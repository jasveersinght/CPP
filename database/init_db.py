import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from config import get_config
from database.db import get_db_connection
from database.seed_data import seed_host, seed_teams, seed_questions, reset_test_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def init_database():
    """Execute schema.sql to recreate database tables."""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            statements = [s.strip() for s in sql_script.split(';') if s.strip()]
            for stmt in statements:
                cursor.execute(stmt)
        conn.commit()
        logger.info("Successfully executed database/schema.sql")
    finally:
        conn.close()

def seed_database():
    """Seed initial host, 80 competition teams, and 90 mathematical questions."""
    seed_host()
    seed_teams(count=80)
    seed_questions()
    logger.info("Database seeding completed successfully.")

if __name__ == '__main__':
    logger.info("Initializing schema...")
    init_database()
    logger.info("Seeding data...")
    seed_database()
