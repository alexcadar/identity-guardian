# Identity Guardian

Identity Guardian is a comprehensive privacy protection toolkit designed to help users monitor personal data exposure, assess digital security practices, and generate GDPR-compliant data removal requests. The application runs entirely locally to ensure maximum privacy and security.

## Features

- **Exposure Monitor**: Checks if emails or usernames have been exposed in data breaches or on sites like Pastebin, using APIs from HaveIBeenPwned, Google Custom Search, Intelligence X, DeHashed, and LeakCheck.
- **Digital Hygiene Assessment**: Interactive questionnaire to evaluate security practices, with personalized scores and recommendations powered by Google Gemini API.
- **Anti-Dox Toolkit**: Generates GDPR-compliant data removal requests for various platforms using professionally crafted templates.
- **Centralized Dashboard**: Consolidates reports and verification history for easy access and tracking.

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
   HIBP_API_KEY=""          # Requires subscription
   GOOGLE_API_KEY=""        # Free in Google Cloud Console - https://console.cloud.google.com/apis
   GOOGLE_CSE_ID=""         # Free in Google Cloud Console - follow documentation: https://support.google.com/programmable-search/answer/12499034?hl=en
   GEMINI_API_KEY=""        # Free in Google Cloud Console - https://console.cloud.google.com/apis
   LEAK_CHECK=""            # Requires subscription
   DEHASHED=""              # Requires subscription
   INTELLX=""               # Limited free version available
   ```

5. **Initialize the database**:
   The SQLite database (`identity_guardian.db`) is created automatically on first run.

6. **Run the application**:
   ```bash
   python app.py
   ```
   Access the application at `http://localhost:5000` in your browser.

## Usage

- **Exposure Monitor**: Enter an email or username to check for data exposure across multiple sources.
- **Digital Hygiene Assessment**: Complete the interactive questionnaire to receive a personalized security report with actionable recommendations.
- **Anti-Dox Toolkit**: Select data types and reasons to generate customized GDPR removal requests.
- **Dashboard**: View and manage previous reports and verification history.

## Privacy & Security

- **Local Processing**: All data processing occurs locally on your device
- **No External Data Storage**: Personal information is never transmitted to external servers (except for API queries)
- **Secure Database**: Local SQLite database with proper session management
- **Anonymized Sessions**: Flask sessions maintain privacy while providing persistent functionality

## Technology Stack

- **Backend**: Python, Flask, SQLite
- **Frontend**: HTML, CSS, Jinja2 templates
- **APIs**: HaveIBeenPwned, Google Custom Search, Google Gemini, Intelligence X, DeHashed, LeakCheck
- **Database**: SQLite for local data storage

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is designed for legitimate privacy protection purposes. Users are responsible for complying with applicable laws and platform terms of service when using data removal features.
