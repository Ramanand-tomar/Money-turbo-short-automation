import os
import dotenv
dotenv.load_dotenv()
from app.services import db

def check_users():
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT DISTINCT user_id FROM tasks")
        print("Tasks user_ids:", [row[0] for row in cursor.fetchall()])
    except Exception as e:
        print("Error reading tasks user_ids:", e)
        
    try:
        cursor.execute("SELECT DISTINCT user_id FROM settings")
        print("Settings user_ids:", [row[0] for row in cursor.fetchall()])
    except Exception as e:
        print("Error reading settings user_ids:", e)
        
    conn.close()

if __name__ == "__main__":
    check_users()
