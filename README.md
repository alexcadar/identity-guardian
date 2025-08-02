# Identity Guardian

**Identity Guardian** is a defensive toolkit designed to protect your online identity. It helps users monitor personal data exposure, assess digital hygiene, and generate GDPR data deletion requests.

## Features

- **Exposure Monitor**: Checks if emails or usernames have been exposed in data breaches or leaked on platforms like Pastebin, using APIs such as HaveIBeenPwned, Google Custom Search, Intelligence X, DeHashed, and LeakCheck.
- **Digital Hygiene Assessment**: An interactive questionnaire that evaluates security practices and provides personalized scores and recommendations using the Google Gemini API.
- **Anti-Dox Toolkit**: Generates GDPR-compliant data deletion requests for various platforms, using templates inspired by ANAF (Romanian National Agency for Fiscal Administration) models.
- **Dashboard**: Centralized interface to view reports and scan history.

## Requirements

- Python 3.8+
- Operating System: Windows, macOS, or Linux
- API Keys for: HaveIBeenPwned, Google Custom Search, Google Gemini, Intelligence X, DeHashed, LeakCheck (optional but recommended)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/alexcadar/identity-guardian.git
   cd identity-guardian
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:  
   Create a `.env` file in the project directory and add your API keys:
   ```plaintext
   HIBP_API_KEY=""         # Requires a subscription
   GOOGLE_API_KEY=""       # Free in Google Cloud Console - https://console.cloud.google.com/apis
   GOOGLE_CSE_ID=""        # Free - follow documentation: https://support.google.com/programmable-search/answer/12499034
   GEMINI_API_KEY=""       # Free - Google Cloud Console
   LEAK_CHECK=""           # Subscription required
   DEHASHED=""             # Subscription required
   INTELLX=""              # Free limited version available
   ```

5. **Initialize the database**:  
   The SQLite database (`identity_guardian.db`) is automatically created on first run.

6. **Run the application**:
   ```bash
   python app.py
   ```
   Then access the app in your browser at `http://localhost:5000`.

## Usage

- **Exposure Monitor**: Enter an email or username to check for data leaks.
- **Digital Hygiene**: Complete the questionnaire to receive a personalized security report.
- **Anti-Dox Toolkit**: Select the data types and reasons to generate GDPR removal requests.
- **Dashboard**: View past reports and scan history.
