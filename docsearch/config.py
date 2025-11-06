"""
DocSearch - Configuration
"""

import os
from pathlib import Path

class Config:
    """Base configuration"""

    # Base directory
    BASE_DIR = Path(__file__).parent

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))

    # OpenSearch
    OPENSEARCH_HOST = os.getenv('OPENSEARCH_HOST', 'localhost')
    OPENSEARCH_PORT = int(os.getenv('OPENSEARCH_PORT', 9200))
    OPENSEARCH_USER = os.getenv('OPENSEARCH_USER', 'admin')
    OPENSEARCH_PASSWORD = os.getenv('OPENSEARCH_PASSWORD', 'admin')
    OPENSEARCH_USE_SSL = os.getenv('OPENSEARCH_USE_SSL', 'false').lower() == 'true'
    OPENSEARCH_VERIFY_CERTS = os.getenv('OPENSEARCH_VERIFY_CERTS', 'false').lower() == 'true'

    # OpenAI
    USE_OPENAI = os.getenv('USE_OPENAI', 'false').lower() == 'true'
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # Upload
    UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_UPLOAD_SIZE_MB', 50)) * 1024 * 1024

    # Supported file extensions
    ALLOWED_EXTENSIONS = {
        '.pdf', '.doc', '.docx',
        '.xls', '.xlsx', '.csv',
        '.html', '.htm',
        '.md', '.txt'
    }


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


# Config dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
