import os
from datetime import timedelta

class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///leads.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True for SQL query logging
    
    # Pagination
    LEADS_PER_PAGE = 20
    
    # Upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'json'}
    
    # API settings
    API_RATE_LIMIT = int(os.environ.get('API_RATE_LIMIT', 100))
    API_KEY_SECRET = os.environ.get('API_KEY_SECRET') or 'super-secret-api-key-string'
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Visitor Lead Tracking
    VISITOR_LEAD_DUPLICATE_CHECK_HOURS = int(os.environ.get('VISITOR_LEAD_DUPLICATE_CHECK_HOURS', 24))

    # Flask-Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # Salesforce Integration
    SALESFORCE_USERNAME = os.environ.get('SALESFORCE_USERNAME')
    SALESFORCE_PASSWORD = os.environ.get('SALESFORCE_PASSWORD')
    SALESFORCE_TOKEN = os.environ.get('SALESFORCE_TOKEN')

    # HubSpot Integration
    HUBSPOT_API_KEY = os.environ.get('HUBSPOT_API_KEY')

    # Twitter Integration
    TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY')
    TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET')
    TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
    TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')

    # Instagram Integration
    INSTAGRAM_USERNAME = os.environ.get('INSTAGRAM_USERNAME')
    INSTAGRAM_PASSWORD = os.environ.get('INSTAGRAM_PASSWORD')

    # Google Gemini Integration
    GOOGLE_GEMINI_API_KEY = os.environ.get('GOOGLE_GEMINI_API_KEY')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_leads.db'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}