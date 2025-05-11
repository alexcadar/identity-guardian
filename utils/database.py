#!/usr/bin/env python3
# -*- coding: utf-8 -*-
print("Importând database.py")
"""
Identity Guardian - Simplified Database Module
Handles database operations using a simplified schema focused on storing reports.
"""

import sqlite3
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import configuration if needed (folosim același config)
try:
    import config
except ImportError:
    class MockConfig: DB_PATH = 'identity_guardian_simple.db' # Nume nou DB
    config = MockConfig()
    logging.warning("config.py not found, using default simple database path.")

# Set up logging
logger = logging.getLogger(__name__)

# Nume nou pentru a nu suprascrie DB-ul existent în teste
DB_PATH = getattr(config, 'DB_PATH', 'identity_guardian_simple.db')

def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database."""
    try:
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir): os.makedirs(db_dir)
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def init_database() -> bool:
    """Initializes the simplified database schema with migration support."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the Reports table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Reports'")
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            # Create the table with the new schema (timestamp as TEXT)
            cursor.execute('''
            CREATE TABLE Reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                module_type TEXT NOT NULL, 
                summary_data_json TEXT NOT NULL, 
                full_report_json TEXT NOT NULL 
            )
            ''')
            # Create indices
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_type_timestamp ON Reports(module_type, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_timestamp ON Reports(timestamp)')
            conn.commit()
            logger.info(f"Database path: {os.path.abspath(DB_PATH)}")
            logger.info("Simplified database initialized successfully with new schema")
            conn.close()
            return True

        # Table exists, check the schema (specifically the timestamp column type)
        cursor.execute("PRAGMA table_info(Reports)")
        columns = cursor.fetchall()
        timestamp_type = None
        for col in columns:
            if col['name'] == 'timestamp':
                timestamp_type = col['type'].upper()
                break

        if timestamp_type == 'TIMESTAMP':
            logger.info("Detected old schema with timestamp as TIMESTAMP, migrating to TEXT...")
            # Step 1: Create a new table with the updated schema
            cursor.execute('''
            CREATE TABLE Reports_new (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                module_type TEXT NOT NULL, 
                summary_data_json TEXT NOT NULL, 
                full_report_json TEXT NOT NULL 
            )
            ''')

            # Step 2: Migrate data, converting timestamp format
            cursor.execute('''
            INSERT INTO Reports_new (report_id, timestamp, module_type, summary_data_json, full_report_json)
            SELECT 
                report_id, 
                REPLACE(timestamp, 'T', ' ') AS timestamp, 
                module_type, 
                summary_data_json, 
                full_report_json
            FROM Reports
            ''')

            # Step 3: Drop the old table and rename the new one
            cursor.execute('DROP TABLE Reports')
            cursor.execute('ALTER TABLE Reports_new RENAME TO Reports')

            # Step 4: Recreate indices
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_type_timestamp ON Reports(module_type, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_timestamp ON Reports(timestamp)')

            conn.commit()
            logger.info("Database schema migration completed: timestamp changed from TIMESTAMP to TEXT")
        else:
            logger.info("Database schema is up to date (timestamp as TEXT)")

        conn.close()
        return True
    except Exception as e:
        logger.error(f"Simplified database initialization/migration failed: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return False

def save_report(module_type: str, summary_data: Dict[str, Any], full_report: Dict[str, Any]) -> Optional[int]:
    """Saves a generic report to the database."""
    if not module_type or not summary_data or not full_report:
        logger.error("Missing required data for save_report")
        return None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        logger.debug(f"Summary data: {summary_data}")
        logger.debug(f"Full report: {full_report}")

        summary_json = json.dumps(summary_data, ensure_ascii=False)
        full_json = json.dumps(full_report, ensure_ascii=False)

        # Use a consistent timestamp format
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute(
            """
            INSERT INTO Reports (timestamp, module_type, summary_data_json, full_report_json)
            VALUES (?, ?, ?, ?)
            """,
            (timestamp, module_type, summary_json, full_json)
        )
        report_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Saved {module_type} report with ID {report_id}")
        return report_id
    except sqlite3.Error as e:
        logger.error(f"Error saving {module_type} report: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON serialization error: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return None

def get_reports_by_type(module_type: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves a list of reports for a specific module type."""
    reports = []
    if not module_type: return reports
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT report_id, timestamp, summary_data_json
            FROM Reports
            WHERE module_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (module_type, limit)
        )
        rows = cursor.fetchall()
        for row in rows:
            report_summary = dict(row)
            try:
                report_summary['summary_data'] = json.loads(report_summary['summary_data_json'])
                del report_summary['summary_data_json'] # Eliminăm stringul raw
                reports.append(report_summary)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse summary_data_json for report_id {row['report_id']}")
                reports.append({'report_id': row['report_id'], 'timestamp': row['timestamp'], 'summary_data': {'error': 'invalid JSON'}})
        conn.close()
        return reports
    except sqlite3.Error as e:
        logger.error(f"Error retrieving {module_type} reports: {e}")
        if 'conn' in locals() and conn: conn.close()
        return []

def get_report_detail(report_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves the full details of a specific report by its ID."""
    if not report_id: return None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT report_id, timestamp, module_type, full_report_json
            FROM Reports
            WHERE report_id = ?
            """,
            (report_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        report_detail = dict(row)
        try:
            report_detail['full_report'] = json.loads(report_detail['full_report_json'])
            del report_detail['full_report_json']
            conn.close()
            return report_detail
        except json.JSONDecodeError:
            logger.warning(f"Could not parse full_report_json for report_id {report_id}")
            conn.close()
            report_detail['full_report'] = {'error': 'invalid JSON'}
            del report_detail['full_report_json']
            return report_detail

    except sqlite3.Error as e:
        logger.error(f"Error retrieving report detail for report_id {report_id}: {e}")
        if 'conn' in locals() and conn: conn.close()
        return None

# Initialize on import
if __name__ != '__main__':
    init_database() # Asigurăm că DB-ul e inițializat la import

# For testing directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Running simplified database tests...")
    init_success = init_database()
    print(f"Simplified DB initialization: {'Success' if init_success else 'Failed'}")
   
    if init_success:
        # Salvează un raport de test
        summary = {"score": 75, "risk": "medium"}
        full = {"score": 75, "risk": "medium", "recommendations": ["rec1", "rec2"]}
        report_id = save_report("hygiene", summary, full)
        print(f"Saved test hygiene report ID: {report_id}")

        # Recuperează raportul
        reports = get_reports_by_type("hygiene")
        print(f"Retrieved hygiene reports ({len(reports)}): {reports}")

        if report_id:
            detail = get_report_detail(report_id)
            print(f"Detail for report ID {report_id}: {detail}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    init_database()
    summary = {"test": "data"}
    full = {"full": "report"}
    report_id = save_report("test", summary, full)
    print(f"Report ID: {report_id}")
    reports = get_reports_by_type("test")
    print(f"Retrieved reports: {reports}")