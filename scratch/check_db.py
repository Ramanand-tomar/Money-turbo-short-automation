import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from app.services import db
from loguru import logger

def main():
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        if db.IS_POSTGRES:
            # Query column names and types in postgres
            cursor.execute("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'tasks';
            """)
            rows = cursor.fetchall()
            logger.info("PostgreSQL 'tasks' columns:")
            for r in rows:
                logger.info(f"Column: {r[0]} | Type: {r[1]} | MaxLen: {r[2]}")
                
            # Query some task rows
            cursor.execute("SELECT task_id, user_id, state, cloudinary_url FROM tasks LIMIT 10")
            tasks = cursor.fetchall()
            logger.info("PostgreSQL 'tasks' data:")
            for t in tasks:
                logger.info(f"ID: {t[0]} | User: {t[1]} | State: {t[2]} | Cloudinary: {t[3]}")
        else:
            # SQLite
            cursor.execute("PRAGMA table_info(tasks)")
            rows = cursor.fetchall()
            logger.info("SQLite 'tasks' columns:")
            for r in rows:
                logger.info(f"Column: {dict(r)}")
            
            cursor.execute("SELECT task_id, user_id, state, cloudinary_url FROM tasks LIMIT 10")
            tasks = cursor.fetchall()
            logger.info("SQLite 'tasks' data:")
            for t in tasks:
                logger.info(f"ID: {t['task_id']} | User: {t['user_id']} | State: {t['state']} | Cloudinary: {t['cloudinary_url']}")
    except Exception as e:
        logger.error(f"Error checking database: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
