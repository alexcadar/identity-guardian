Identity Guardian
Identity Guardian is a comprehensive, locally-run web application designed to protect users' online identities. It enables users to monitor personal data exposure, assess digital hygiene, and generate GDPR-compliant data removal requests. Built with privacy in mind, all data processing occurs on the user's device, ensuring sensitive information remains secure.
Features

Exposure Monitor: Checks if email addresses or usernames have been compromised in data breaches or exposed on platforms like Pastebin, leveraging APIs such as HaveIBeenPwned, Google Custom Search, Intelligence X, DeHashed, and LeakCheck. Provides risk assessments and historical tracking of results.
Digital Hygiene Report: Interactive questionnaire to evaluate users' security practices (e.g., password strength, 2FA usage, software updates). Generates personalized risk scores and recommendations using the Google Gemini API.
Anti-Dox Toolkit: Creates customizable GDPR-compliant data removal requests for platforms like Google, Facebook, Twitter/X, and LinkedIn, with templates inspired by ANAF standards. Includes a privacy checklist and emergency doxxing response plan.
Centralized Dashboard: Displays historical reports, exposure check results, and data removal request statuses in a user-friendly interface.

Requirements

Python: Version 3.8 or higher
Operating System: Windows, macOS, or Linux
API Keys (optional but recommended for full functionality):
HaveIBeenPwned (subscription required)
Google Custom Search (free via Google Cloud Console)
Google Gemini (free via Google Cloud Console)
Intelligence X (limited free version available)
DeHashed (subscription required)
LeakCheck (subscription required)



Installation

Clone the Repository:
git clone https://github.com/alexcadar/identity-guardian.git
cd identity-guardian


Create a Virtual Environment:
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install Dependencies:
pip install -r requirements.txt


Configure Environment Variables:Create a .env file in the project directory and add the required API keys:
HIBP_API_KEY=""  # Requires subscription
GOOGLE_API_KEY=""  # Free via Google Cloud Console: https://console.cloud.google.com/apis
GOOGLE_CSE_ID=""  # Free via Google Cloud Console: https://support.google.com/programmable-search/answer/12499034?hl=en
GEMINI_API_KEY=""  # Free via Google Cloud Console: https://console.cloud.google.com/apis
LEAK_CHECK=""  # Requires subscription
DEHASHED=""  # Requires subscription
INTELLX=""  # Limited free version available


Initialize the Database:The SQLite database (identity_guardian.db) is automatically created on first run.

Run the Application:
python app.py

Access the application at http://localhost:5000 in your browser.


Usage

Exposure Monitor: Enter an email or username to check for data breaches or online exposure. View detailed results and risk assessments.
Digital Hygiene Report: Complete the interactive questionnaire to receive a personalized security report with actionable recommendations.
Anti-Dox Toolkit: Select data types and platforms to generate tailored GDPR data removal requests. Track request statuses and access privacy resources.
Dashboard: Review previous reports, exposure check histories, and data removal progress in a centralized interface.

Technical Details

Backend: Python (Flask, requests), SQLite for local data storage, modular API clients for external services.
Frontend: Responsive web interface built with HTML, CSS, and Jinja2 templates.
Privacy: Runs locally with no external data transmission (except API queries). Uses anonymized Flask sessions for persistence.
Logging and Debugging: Extensive logging and diagnostic tools ensure reliability and ease of maintenance.

Contributing
Contributions are welcome! Please submit a pull request or open an issue on the GitHub repository for bugs, feature requests, or improvements.
License
This project is licensed under the MIT License. See the LICENSE file for details.
