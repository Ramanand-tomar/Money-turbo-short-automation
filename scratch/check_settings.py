import sys
import os
os.environ["NEON_DATABASE_URL"] = 'postgresql://neondb_owner:npg_RseWZ3DM1BlG@ep-royal-flower-aomwat5n-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
sys.path.insert(0, r"c:\Users\raman\OneDrive\Desktop\interesting-projects\youtube-automation\MoneyPrinterTurbo")

from app.services import db

conn = db.get_connection()
cursor = conn.cursor()
try:
    cursor.execute("SELECT * FROM settings")
    rows = cursor.fetchall()
    print("Database Settings Rows:")
    for r in rows:
        print(r)
except Exception as e:
    print("Error fetching settings:", e)
finally:
    conn.close()
