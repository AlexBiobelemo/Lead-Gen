# Lead Gen


## Introduction
Lead Gen is a comprehensive application designed to streamline lead generation, management, and engagement. It provides tools for scraping leads, generating AI-powered leads, managing user profiles, and integrating with external platforms like Salesforce and HubSpot.

## Key Features
*   **Lead Scraping:** Efficiently scrape leads from various sources.
*   **AI Lead Generation:** Generate new leads using artificial intelligence.
*   **Lead Management:** Add, view, edit, and manage leads with detailed information.
*   **User Authentication & Profiles:** Secure user registration, login, and profile management.
*   **Dashboard & Analytics:** Overview of lead data and engagement metrics.
*   **API Integration:** Support for Salesforce and HubSpot integration.
*   **Theming:** Dark theme support for user interface.

## Technical Stack
*   **Backend:** Python, Flask
*   **Database:** SQLite (managed with SQLAlchemy and Alembic migrations)
*   **Frontend:** HTML, CSS, JavaScript
*   **AI/ML:** (Implied by AI Lead Generation, specific libraries not provided)

## Getting Started

### Prerequisites
*   Python 3.x
*   pip (Python package installer)
*   Virtual environment (recommended)

### Installation
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/AlexBiobelemo/Lead-Gen/
    cd Lead-Gen
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up environment variables:**
    Create a `.env` file in the root directory and add necessary variables (e.g., `SECRET_KEY`, database URI, API keys for integrations). Refer to `.env` for examples.
    ```
    SECRET_KEY="your_secret_key_here"
    DATABASE_URL="sqlite:///instance/leads.db"
    # Add other API keys or configuration as needed
    ```
5.  **Initialize the database:**
    ```bash
    flask db upgrade
    ```

## Usage Instructions
1.  **Run the application:**
    ```bash
    flask run
    ```
2.  **Access the application:**
    Open your web browser and navigate to `http://127.0.0.1:5000` (or the port specified in your configuration).
3.  **Register an account:**
    Create a new user account to access the dashboard and features.
4.  **Start generating/managing leads:**
    Explore the dashboard to scrape leads, generate AI leads, and manage your lead database.

## Configuration
Configuration details are managed through environment variables in the `.env` file and `config.py`. Key configurable aspects include:
*   `SECRET_KEY`: For session management and security.
*   `SQLALCHEMY_DATABASE_URI`: Database connection string.
*   API keys for external services (e.g., Salesforce, HubSpot, AI services).

## Contributing Guidelines
Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes and ensure tests pass.
4.  Submit a pull request with a clear description of your changes.

## License
None

## Contact Information
For questions or feedback, please connect with Alex Alagoa Biobelemo on [LinkedIn](https://www.linkedin.com/in/alex-alagoa-biobelemo/).
