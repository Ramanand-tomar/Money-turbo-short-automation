import sys
import os
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from app.services import db
from loguru import logger

def main():
    from dotenv import load_dotenv
    load_dotenv()
    user_id = "user_3EZD5UTvgVDMoAScLGKsxmX3x3h"
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        if db.IS_POSTGRES:
            cursor.execute("SELECT * FROM youtube_oauth")
            rows = cursor.fetchall()
            logger.info(f"youtube_oauth rows in PostgreSQL:")
            for r in rows:
                logger.info(f"User: {r[0]} | Channel Name: {r[2]} | Channel ID: {r[1]} | Token Expiry: {r[5]}")
        else:
            cursor.execute("SELECT * FROM youtube_oauth")
            rows = cursor.fetchall()
            logger.info(f"youtube_oauth rows in SQLite:")
            for r in rows:
                logger.info(f"User: {r['user_id']} | Channel Name: {r['channel_name']} | Channel ID: {r['channel_id']} | Token Expiry: {r['token_expiry']}")
    except Exception as e:
        logger.error(f"Error checking youtube oauth table: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
