import sqlite3
import os

db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "storage")
db_path = os.path.join(db_dir, "metadata.db")

print("Checking SQLite database at:", db_path)
if not os.path.exists(db_path):
    print("Database file does not exist!")
else:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # List tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row["name"] for row in cursor.fetchall()]
    print("Tables:", tables)
    
    if "tasks" in tables:
        cursor.execute("SELECT task_id, user_id, state, progress, status_message, created_at FROM tasks ORDER BY created_at DESC")
        rows = cursor.fetchall()
        print(f"\nFound {len(rows)} tasks:")
        for row in rows:
            print(dict(row))
    else:
        print("tasks table not found!")
    conn.close()
