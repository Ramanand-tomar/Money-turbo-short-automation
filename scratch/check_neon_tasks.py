import psycopg2
from urllib.parse import urlparse

DATABASE_URL = 'postgresql://neondb_owner:npg_RseWZ3DM1BlG@ep-royal-flower-aomwat5n-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

print("Connecting to NeonDB...")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = [row[0] for row in cursor.fetchall()]
print("Tables:", tables)

if "tasks" in tables:
    # Query all columns in tasks
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='tasks'")
    columns = [row[0] for row in cursor.fetchall()]
    print("Tasks columns:", columns)
    
    cursor.execute("SELECT task_id, user_id, state, progress, status_message, created_at FROM tasks ORDER BY created_at DESC")
    rows = cursor.fetchall()
    print(f"\nFound {len(rows)} tasks:")
    for row in rows:
        print(dict(zip(["task_id", "user_id", "state", "progress", "status_message", "created_at"], row)))
else:
    print("tasks table not found!")

conn.close()
