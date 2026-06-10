import os
import dotenv
dotenv.load_dotenv()
from app.services import db

def run_migration():
    temp_file = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "storage", "last_user_id.txt")
    if not os.path.exists(temp_file):
        print("Error: storage/last_user_id.txt not found. Please restart the backend and refresh the browser.")
        return
        
    with open(temp_file, "r") as f:
        new_user_id = f.read().strip()
        
    if not new_user_id or new_user_id == "global":
        print(f"Error: Invalid new user ID parsed: '{new_user_id}'")
        return
        
    old_user_id = "user_3EZD5UTvgVDMoAScLGKsxmX3x3h"
    print(f"Migrating records from old user ID '{old_user_id}' to new user ID '{new_user_id}'...")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Migrate tasks table
        cursor.execute("UPDATE tasks SET user_id = %s WHERE user_id = %s" if db.IS_POSTGRES else "UPDATE tasks SET user_id = ? WHERE user_id = ?", (new_user_id, old_user_id))
        tasks_migrated = cursor.rowcount
        conn.commit()
        print(f"Successfully migrated {tasks_migrated} tasks.")
        
        # Migrate settings table
        cursor.execute("UPDATE settings SET user_id = %s WHERE user_id = %s" if db.IS_POSTGRES else "UPDATE settings SET user_id = ? WHERE user_id = ?", (new_user_id, old_user_id))
        settings_migrated = cursor.rowcount
        conn.commit()
        print(f"Successfully migrated {settings_migrated} settings.")
        
        # Migrate youtube_oauth table
        cursor.execute("UPDATE youtube_oauth SET user_id = %s WHERE user_id = %s" if db.IS_POSTGRES else "UPDATE youtube_oauth SET user_id = ? WHERE user_id = ?", (new_user_id, old_user_id))
        oauth_migrated = cursor.rowcount
        conn.commit()
        print(f"Successfully migrated {oauth_migrated} youtube_oauth records.")
        
        print("Migration complete!")
    except Exception as e:
        print("Error during migration:", e)
        conn.rollback()
        
    conn.close()

if __name__ == "__main__":
    run_migration()
