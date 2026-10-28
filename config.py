import os
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'default-dev-secret-key-change-in-prod')
    
    # Database configuration
    MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'math_auction')
    
    # Auction System Rules
    AUCTION_DURATION_SECONDS = int(os.getenv('AUCTION_DURATION_SECONDS', 10))
    BID_INCREMENT = float(os.getenv('BID_INCREMENT', 10.0))
    STARTING_WALLET_BALANCE = float(os.getenv('STARTING_WALLET_BALANCE', 10000.0))
    MAX_QUESTIONS_PER_TEAM = int(os.getenv('MAX_QUESTIONS_PER_TEAM', 5))
    MAX_TEAMS = int(os.getenv('MAX_TEAMS', 80))
    TOTAL_QUESTION_TARGET = int(os.getenv('TOTAL_QUESTION_TARGET', 90))

    # Database Pool Configuration
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 50))
    DB_POOL_MAX_OVERFLOW = int(os.getenv('DB_POOL_MAX_OVERFLOW', 30))
    DB_POOL_TIMEOUT = float(os.getenv('DB_POOL_TIMEOUT', 10.0))
    
    # Watchdog configuration
    WATCHDOG_INTERVAL_SECONDS = float(os.getenv('WATCHDOG_INTERVAL_SECONDS', 0.5))
    
    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True in HTTPS production
    
    @classmethod
    def get_db_config(cls):
        return {
            'host': cls.MYSQL_HOST,
            'port': cls.MYSQL_PORT,
            'user': cls.MYSQL_USER,
            'password': cls.MYSQL_PASSWORD,
            'database': cls.MYSQL_DATABASE,
            'charset': 'utf8mb4',
            'autocommit': False,
        }

class DevelopmentConfig(Config):
    DEBUG = True
    ENV = 'development'

class ProductionConfig(Config):
    DEBUG = False
    ENV = 'production'
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    MYSQL_DATABASE = os.getenv('TEST_MYSQL_DATABASE', 'math_auction')

config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    env = os.getenv('FLASK_ENV', 'development').lower()
    return config_map.get(env, DevelopmentConfig)
