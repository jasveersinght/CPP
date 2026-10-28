import os
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

def _parse_database_url():
    """Parse DATABASE_URL or MYSQL_URL if present, otherwise fallback to MYSQL_* env variables."""
    db_url = os.getenv('DATABASE_URL') or os.getenv('MYSQL_URL')
    if db_url:
        parsed = urlparse(db_url)
        q_params = parse_qs(parsed.query)
        ssl_enabled = (
            os.getenv('MYSQL_SSL', '').lower() in ('true', '1', 'yes') or
            'ssl' in q_params or
            'ssl-mode' in q_params or
            'sslmode' in q_params
        )
        return {
            'host': parsed.hostname or '127.0.0.1',
            'port': parsed.port or 3306,
            'user': parsed.username or 'root',
            'password': parsed.password or '',
            'database': parsed.path.lstrip('/') if parsed.path else 'math_auction',
            'ssl': ssl_enabled
        }
    return {
        'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DATABASE', 'math_auction'),
        'ssl': os.getenv('MYSQL_SSL', '').lower() in ('true', '1', 'yes')
    }

_parsed_db = _parse_database_url()

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'default-dev-secret-key-change-in-prod')
    
    # Database configuration
    MYSQL_HOST = _parsed_db['host']
    MYSQL_PORT = _parsed_db['port']
    MYSQL_USER = _parsed_db['user']
    MYSQL_PASSWORD = _parsed_db['password']
    MYSQL_DATABASE = _parsed_db['database']
    MYSQL_SSL = _parsed_db['ssl']
    MYSQL_SSL_CA = os.getenv('MYSQL_SSL_CA', None)
    
    # Auction System Rules
    QUESTION_READING_DURATION_SECONDS = int(os.getenv('QUESTION_READING_DURATION_SECONDS', 10))
    AUCTION_DURATION_SECONDS = int(os.getenv('AUCTION_DURATION_SECONDS', 30))
    BID_INCREMENT = float(os.getenv('BID_INCREMENT', 10.0))
    STARTING_WALLET_BALANCE = float(os.getenv('STARTING_WALLET_BALANCE', 10000.0))
    MAX_QUESTIONS_PER_TEAM = int(os.getenv('MAX_QUESTIONS_PER_TEAM', 5))
    MAX_TEAMS = int(os.getenv('MAX_TEAMS', 80))
    TOTAL_QUESTION_TARGET = int(os.getenv('TOTAL_QUESTION_TARGET', 90))

    # Database Pool Configuration
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 20))
    DB_POOL_MAX_OVERFLOW = int(os.getenv('DB_POOL_MAX_OVERFLOW', 15))
    DB_POOL_TIMEOUT = float(os.getenv('DB_POOL_TIMEOUT', 10.0))
    
    # Watchdog configuration
    WATCHDOG_INTERVAL_SECONDS = float(os.getenv('WATCHDOG_INTERVAL_SECONDS', 0.5))
    
    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True in HTTPS production
    
    @classmethod
    def get_db_config(cls):
        cfg = {
            'host': cls.MYSQL_HOST,
            'port': cls.MYSQL_PORT,
            'user': cls.MYSQL_USER,
            'password': cls.MYSQL_PASSWORD,
            'database': cls.MYSQL_DATABASE,
            'charset': 'utf8mb4',
            'autocommit': False,
        }
        if cls.MYSQL_SSL or cls.MYSQL_SSL_CA:
            ssl_opts = {}
            if cls.MYSQL_SSL_CA and os.path.exists(cls.MYSQL_SSL_CA):
                ssl_opts['ca'] = cls.MYSQL_SSL_CA
            else:
                ssl_opts['check_hostname'] = False
            cfg['ssl'] = ssl_opts
        return cfg

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
    QUESTION_READING_DURATION_SECONDS = int(os.getenv('TEST_QUESTION_READING_DURATION_SECONDS', 0))
    AUCTION_DURATION_SECONDS = int(os.getenv('TEST_AUCTION_DURATION_SECONDS', 30))
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
