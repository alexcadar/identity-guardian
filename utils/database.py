#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

# Import configuration if needed
try:
    import config
except ImportError:
    class MockConfig:
        DB_PATH = 'identity_guardian.db'  # Align with app.py
    config = MockConfig()
    logging.warning("config.py not found, using default database path.")

# Set up logging
logger = logging.getLogger(__name__)

# Use consistent database path
DB_PATH = getattr(config, 'DB_PATH', 'identity_guardian.db')

def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database."""
    try:
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        logger.debug(f"Connected to database at {os.path.abspath(DB_PATH)}")
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
            logger.info(f"Database initialized at {os.path.abspath(DB_PATH)}")
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
        logger.error(f"Database initialization/migration failed: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return False
# Adăugați aceste funcții în database.py după funcția init_database():

def optimize_database() -> bool:
    """
    Add indexes and optimize database for better performance.
    This should be called after init_database().
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create additional indexes for faster queries
        optimization_queries = [
            # Index for faster module_type queries
            "CREATE INDEX IF NOT EXISTS idx_module_type ON Reports(module_type)",
            
            # Index for timestamp queries
            "CREATE INDEX IF NOT EXISTS idx_timestamp_desc ON Reports(timestamp DESC)",
            
            # Compound index for the most common query pattern
            "CREATE INDEX IF NOT EXISTS idx_module_timestamp ON Reports(module_type, timestamp DESC)",
            
            # Enable query optimization
            "PRAGMA optimize",
            
            # Set journal mode for better concurrent access
            "PRAGMA journal_mode=WAL",
            
            # Increase cache size (in pages, -2000 = 2MB)
            "PRAGMA cache_size=-2000",
            
            # Enable foreign keys
            "PRAGMA foreign_keys=ON"
        ]
        
        for query in optimization_queries:
            cursor.execute(query)
            logger.debug(f"Executed optimization: {query}")
        
        conn.commit()
        
        # Analyze the database for query planner
        cursor.execute("ANALYZE")
        
        conn.close()
        logger.info("Database optimization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return False

def get_reports_by_type_paginated(module_type: str, page: int = 1, per_page: int = 10) -> tuple[List[Dict[str, Any]], int]:
    """
    Retrieve paginated reports of a specific type with total count.
    
    Args:
        module_type (str): The type of reports to retrieve
        page (int): Page number (1-based)
        per_page (int): Number of items per page
        
    Returns:
        Tuple[List[Dict], int]: (reports, total_count)
    """
    reports = []
    total_count = 0
    
    if not module_type or page < 1 or per_page < 1:
        return reports, total_count
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute(
            "SELECT COUNT(*) FROM Reports WHERE module_type = ?",
            (module_type,)
        )
        total_count = cursor.fetchone()[0]
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get paginated results
        cursor.execute(
            """
            SELECT report_id, timestamp, summary_data_json
            FROM Reports
            WHERE module_type = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (module_type, per_page, offset)
        )
        
        rows = cursor.fetchall()
        
        for row in rows:
            report_summary = dict(row)
            try:
                report_summary['summary_data'] = json.loads(report_summary['summary_data_json'])
                del report_summary['summary_data_json']
                reports.append(report_summary)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse summary_data_json for report_id {row['report_id']}")
                reports.append({
                    'report_id': row['report_id'], 
                    'timestamp': row['timestamp'], 
                    'summary_data': {'error': 'invalid JSON'}
                })
        
        conn.close()
        logger.debug(f"Retrieved page {page} of {module_type} reports: {len(reports)} items, total: {total_count}")
        return reports, total_count
        
    except sqlite3.Error as e:
        logger.error(f"Error retrieving paginated {module_type} reports: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return [], 0

def vacuum_database() -> bool:
    """
    Vacuum the database to reclaim space and optimize performance.
    Should be called periodically (e.g., weekly).
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)  # Longer timeout for vacuum
        conn.execute("VACUUM")
        conn.close()
        logger.info("Database vacuum completed successfully")
        return True
    except Exception as e:
        logger.error(f"Database vacuum failed: {e}")
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
    """
    Retrieves a list of reports for a specific module type.
    
    Args:
        module_type (str): The type of reports to retrieve ('exposure', 'hygiene', etc.)
        limit (int): Maximum number of reports to return. Use a large number (e.g., 9999) for all reports.
    
    Returns:
        List[Dict[str, Any]]: List of reports with summary data
    """
    reports = []
    if not module_type:
        logger.warning("No module_type provided for get_reports_by_type")
        return reports
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
        
        logger.debug(f"Retrieved {len(rows)} rows for module_type {module_type}")
        
        for row in rows:
            report_summary = dict(row)
            try:
                report_summary['summary_data'] = json.loads(report_summary['summary_data_json'])
                del report_summary['summary_data_json']
                reports.append(report_summary)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse summary_data_json for report_id {row['report_id']}")
                reports.append({
                    'report_id': row['report_id'], 
                    'timestamp': row['timestamp'], 
                    'summary_data': {'error': 'invalid JSON'}
                })
        
        conn.close()
        return reports
    except sqlite3.Error as e:
        logger.error(f"Error retrieving {module_type} reports: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return []

def get_report_detail(report_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves the full details of a specific report by its ID."""
    if not report_id:
        logger.warning("No report_id provided for get_report_detail")
        return None
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
            logger.warning(f"No report found for report_id {report_id}")
            conn.close()
            return None

        report_detail = dict(row)
        try:
            report_detail['full_report'] = json.loads(report_detail['full_report_json'])
            del report_detail['full_report_json']
            logger.debug(f"Successfully retrieved report_id {report_id}: {report_detail}")
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
        if 'conn' in locals() and conn:
            conn.close()
        return None

# Initialize on import
if __name__ != '__main__':
    init_database()

# For testing directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Running simplified database tests...")
    init_success = init_database()
    print(f"Simplified DB initialization: {'Success' if init_success else 'Failed'}")
   
    if init_success:
        # Save a test report
        summary = {"score": 75, "risk": "medium"}
        full = {"score": 75, "risk": "medium", "recommendations": ["rec1", "rec2"]}
        report_id = save_report("hygiene", summary, full)
        print(f"Saved test hygiene report ID: {report_id}")

        # Retrieve the report
        reports = get_reports_by_type("hygiene")
        print(f"Retrieved hygiene reports ({len(reports)}): {reports}")

        if report_id:
            detail = get_report_detail(report_id)
            print(f"Detail for report ID {report_id}: {detail}")

