import os
import json
import sqlite3
from loguru import logger

# Try to get Neon database URL, fallback to local sqlite database
DATABASE_URL = os.getenv("NEON_DATABASE_URL") or os.getenv("DATABASE_URL")
IS_POSTGRES = False

if DATABASE_URL and (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")):
    IS_POSTGRES = True
    logger.info("Using PostgreSQL/NeonDB database backend.")
else:
    logger.info("Using local SQLite database backend (storage/metadata.db).")

def get_connection():
    if IS_POSTGRES:
        import psycopg2
        # Ensure SSL connection is used for NeonDB
        if "?" not in DATABASE_URL:
            conn_url = f"{DATABASE_URL}?sslmode=require"
        else:
            conn_url = DATABASE_URL
        return psycopg2.connect(conn_url)
    else:
        db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "storage")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "metadata.db")
        conn = sqlite3.connect(db_path)
        # Return rows as dicts for easier handling
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if IS_POSTGRES:
            # Create user-scoped settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    user_id VARCHAR(100) NOT NULL,
                    key VARCHAR(100) NOT NULL,
                    value TEXT,
                    PRIMARY KEY (user_id, key)
                )
            """)
            # Create user-scoped tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id VARCHAR(100) PRIMARY KEY,
                    user_id VARCHAR(100) DEFAULT 'global',
                    state INT DEFAULT 0,
                    progress INT DEFAULT 0,
                    params TEXT,
                    script TEXT,
                    terms TEXT,
                    videos TEXT,
                    combined_videos TEXT,
                    audio_file TEXT,
                    audio_duration INT,
                    subtitle_path TEXT,
                    materials TEXT,
                    cloudinary_url TEXT,
                    error_message TEXT,
                    status_message TEXT,
                    cross_post_results TEXT,
                    youtube_uploaded INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create user-scoped youtube_oauth table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS youtube_oauth (
                    user_id VARCHAR(100) PRIMARY KEY,
                    channel_id VARCHAR(150),
                    channel_name VARCHAR(255),
                    access_token TEXT,
                    refresh_token TEXT,
                    token_expiry VARCHAR(150)
                )
            """)
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(100) PRIMARY KEY,
                    email VARCHAR(255),
                    role VARCHAR(50) DEFAULT 'user',
                    plan VARCHAR(50) DEFAULT 'free',
                    quota_videos_per_day INT DEFAULT 5,
                    quota_videos_per_month INT DEFAULT 50,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create usage_log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_log (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    task_id VARCHAR(100) NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create platform_config table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_config (
                    key VARCHAR(100) PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create viral_scores table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS viral_scores (
                    id SERIAL PRIMARY KEY,
                    task_id VARCHAR(100) DEFAULT NULL,
                    script TEXT NOT NULL,
                    platform VARCHAR(100) DEFAULT 'youtube_shorts',
                    hook_score INT DEFAULT 0,
                    emotion_score INT DEFAULT 0,
                    clarity_score INT DEFAULT 0,
                    pacing_score INT DEFAULT 0,
                    cta_score INT DEFAULT 0,
                    overall_score INT DEFAULT 0,
                    improvement_tip TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create trend_cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trend_cache (
                    id SERIAL PRIMARY KEY,
                    topic VARCHAR(255) NOT NULL,
                    platform VARCHAR(50) NOT NULL,
                    score INT DEFAULT 0,
                    category VARCHAR(50) NOT NULL,
                    suggested_hook TEXT,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create scheduled_posts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    id SERIAL PRIMARY KEY,
                    task_id VARCHAR(100) NOT NULL,
                    user_id VARCHAR(100) NOT NULL,
                    platform VARCHAR(50) NOT NULL,
                    scheduled_at TIMESTAMP NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create platform_oauth table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_oauth (
                    user_id VARCHAR(100) NOT NULL,
                    platform VARCHAR(50) NOT NULL,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    token_expiry VARCHAR(150),
                    channel_id VARCHAR(150),
                    channel_name VARCHAR(255),
                    PRIMARY KEY (user_id, platform)
                )
            """)
        else:
            # SQLite user-scoped table creation
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    user_id TEXT,
                    key TEXT,
                    value TEXT,
                    PRIMARY KEY (user_id, key)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    user_id TEXT DEFAULT 'global',
                    state INTEGER DEFAULT 0,
                    progress INTEGER DEFAULT 0,
                    params TEXT,
                    script TEXT,
                    terms TEXT,
                    videos TEXT,
                    combined_videos TEXT,
                    audio_file TEXT,
                    audio_duration INTEGER,
                    subtitle_path TEXT,
                    materials TEXT,
                    cloudinary_url TEXT,
                    error_message TEXT,
                    status_message TEXT,
                    cross_post_results TEXT,
                    youtube_uploaded INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS youtube_oauth (
                    user_id TEXT PRIMARY KEY,
                    channel_id TEXT,
                    channel_name TEXT,
                    access_token TEXT,
                    refresh_token TEXT,
                    token_expiry TEXT
                )
            """)
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT,
                    role TEXT DEFAULT 'user',
                    plan TEXT DEFAULT 'free',
                    quota_videos_per_day INTEGER DEFAULT 5,
                    quota_videos_per_month INTEGER DEFAULT 50,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create usage_log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create platform_config table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create viral_scores table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS viral_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT DEFAULT NULL,
                    script TEXT NOT NULL,
                    platform TEXT DEFAULT 'youtube_shorts',
                    hook_score INTEGER DEFAULT 0,
                    emotion_score INTEGER DEFAULT 0,
                    clarity_score INTEGER DEFAULT 0,
                    pacing_score INTEGER DEFAULT 0,
                    cta_score INTEGER DEFAULT 0,
                    overall_score INTEGER DEFAULT 0,
                    improvement_tip TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create trend_cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trend_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    score INTEGER DEFAULT 0,
                    category TEXT NOT NULL,
                    suggested_hook TEXT,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create scheduled_posts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    scheduled_at TIMESTAMP NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create platform_oauth table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_oauth (
                    user_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    token_expiry TEXT,
                    channel_id TEXT,
                    channel_name TEXT,
                    PRIMARY KEY (user_id, platform)
                )
            """)
        # Dynamic database migration helper to ensure newer columns exist in older tables
        # Dynamic database migration helper to ensure newer columns exist in older tables
        migration_columns = [
            ("user_id", "TEXT DEFAULT 'global'"),
            ("cloudinary_url", "TEXT"),
            ("status_message", "TEXT"),
            ("error_message", "TEXT"),
            ("cross_post_results", "TEXT"),
            ("youtube_uploaded", "INTEGER DEFAULT 0")
        ]
        for col_name, col_type in migration_columns:
            try:
                cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
                conn.commit()
            except Exception:
                conn.rollback()

        conn.commit()
        logger.info("User-scoped database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize user-scoped database: {e}")
        conn.rollback()
    finally:
        conn.close()

# Initialize tables on startup
init_db()

# --- HELPER FUNCTIONS FOR SETTINGS ---
def get_setting(key, default=None, user_id="global"):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("SELECT value FROM settings WHERE key = %s AND user_id = %s", (key, user_id))
        else:
            cursor.execute("SELECT value FROM settings WHERE key = ? AND user_id = ?", (key, user_id))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0] if IS_POSTGRES else row["value"]
        # Fallback to os.environ or config.toml if not in database
        env_val = os.getenv(key.upper())
        if env_val is not None:
            return env_val
        return default
    except Exception as e:
        logger.warning(f"Error reading setting {key} for user {user_id}: {e}")
        return default

def save_setting(key, value, user_id="global"):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO settings (user_id, key, value) VALUES (%s, %s, %s)
                ON CONFLICT (user_id, key) DO UPDATE SET value = EXCLUDED.value
            """, (user_id, key, value))
        else:
            cursor.execute("INSERT OR REPLACE INTO settings (user_id, key, value) VALUES (?, ?, ?)", (user_id, key, value))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving setting {key} for user {user_id}: {e}")
        return False

# --- HELPER FUNCTIONS FOR YOUTUBE OAUTH ---
def get_youtube_credentials(user_id="global"):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("SELECT channel_id, channel_name, access_token, refresh_token, token_expiry FROM youtube_oauth WHERE user_id = %s LIMIT 1", (user_id,))
        else:
            cursor.execute("SELECT channel_id, channel_name, access_token, refresh_token, token_expiry FROM youtube_oauth WHERE user_id = ? LIMIT 1", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            if IS_POSTGRES:
                return {
                    "channel_id": row[0],
                    "channel_name": row[1],
                    "access_token": row[2],
                    "refresh_token": row[3],
                    "token_expiry": row[4]
                }
            else:
                return {
                    "channel_id": row["channel_id"],
                    "channel_name": row["channel_name"],
                    "access_token": row["access_token"],
                    "refresh_token": row["refresh_token"],
                    "token_expiry": row["token_expiry"]
                }
        return None
    except Exception as e:
        logger.error(f"Error reading youtube credentials for user {user_id}: {e}")
        return None

def save_youtube_credentials(channel_id, channel_name, access_token, refresh_token, token_expiry, user_id="global"):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO youtube_oauth (user_id, channel_id, channel_name, access_token, refresh_token, token_expiry)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    channel_id = EXCLUDED.channel_id,
                    channel_name = EXCLUDED.channel_name,
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    token_expiry = EXCLUDED.token_expiry
            """, (user_id, channel_id, channel_name, access_token, refresh_token, token_expiry))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO youtube_oauth (user_id, channel_id, channel_name, access_token, refresh_token, token_expiry)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, channel_id, channel_name, access_token, refresh_token, token_expiry))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving youtube credentials for user {user_id}: {e}")
        return False

def delete_youtube_credentials(user_id="global"):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("DELETE FROM youtube_oauth WHERE user_id = %s", (user_id,))
        else:
            cursor.execute("DELETE FROM youtube_oauth WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error deleting youtube credentials for user {user_id}: {e}")
        return False

def check_and_create_user(user_id: str, email: str = None) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    INSERT INTO users (user_id, email, role, plan, quota_videos_per_day, quota_videos_per_month, is_active)
                    VALUES (%s, %s, 'user', 'free', 5, 50, TRUE)
                """, (user_id, email))
                conn.commit()
                logger.info(f"Auto-registered new user in PostgreSQL: {user_id} ({email})")
        else:
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    INSERT INTO users (user_id, email, role, plan, quota_videos_per_day, quota_videos_per_month, is_active)
                    VALUES (?, ?, 'user', 'free', 5, 50, 1)
                """, (user_id, email))
                conn.commit()
                logger.info(f"Auto-registered new user in SQLite: {user_id} ({email})")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error checking/creating user {user_id}: {e}")
        return False

def get_user(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("SELECT user_id, email, role, plan, quota_videos_per_day, quota_videos_per_month, is_active, created_at FROM users WHERE user_id = %s", (user_id,))
        else:
            cursor.execute("SELECT user_id, email, role, plan, quota_videos_per_day, quota_videos_per_month, is_active, created_at FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            if IS_POSTGRES:
                return {
                    "user_id": row[0],
                    "email": row[1],
                    "role": row[2],
                    "plan": row[3],
                    "quota_videos_per_day": row[4],
                    "quota_videos_per_month": row[5],
                    "is_active": bool(row[6]),
                    "created_at": row[7]
                }
            else:
                return {
                    "user_id": row["user_id"],
                    "email": row["email"],
                    "role": row["role"],
                    "plan": row["plan"],
                    "quota_videos_per_day": row["quota_videos_per_day"],
                    "quota_videos_per_month": row["quota_videos_per_month"],
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"]
                }
        return None
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        return None

def create_user(user_id, email, role='user', plan='free', quota_videos_per_day=5, quota_videos_per_month=50, is_active=True):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        active_val = 1 if is_active else 0
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO users (user_id, email, role, plan, quota_videos_per_day, quota_videos_per_month, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, email, role, plan, quota_videos_per_day, quota_videos_per_month, is_active))
        else:
            cursor.execute("""
                INSERT INTO users (user_id, email, role, plan, quota_videos_per_day, quota_videos_per_month, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, email, role, plan, quota_videos_per_day, quota_videos_per_month, active_val))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error creating user {user_id}: {e}")
        return False

def update_user(user_id, **kwargs):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        set_clauses = []
        values = []
        for key, val in kwargs.items():
            if key in ["role", "plan", "quota_videos_per_day", "quota_videos_per_month", "is_active", "email"]:
                if key == "is_active":
                    db_val = bool(val) if IS_POSTGRES else (1 if val else 0)
                else:
                    db_val = val
                
                if IS_POSTGRES:
                    set_clauses.append(f"{key} = %s")
                else:
                    set_clauses.append(f"{key} = ?")
                values.append(db_val)
        if set_clauses:
            values.append(user_id)
            set_str = ", ".join(set_clauses)
            if IS_POSTGRES:
                cursor.execute(f"UPDATE users SET {set_str} WHERE user_id = %s", tuple(values))
            else:
                cursor.execute(f"UPDATE users SET {set_str} WHERE user_id = ?", tuple(values))
            conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return False

def get_usage_today(user_id):
    try:
        from datetime import datetime, timezone
        start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_str = start_of_day.strftime("%Y-%m-%d %H:%M:%S")
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("SELECT COUNT(*) FROM usage_log WHERE user_id = %s AND created_at >= %s", (user_id, start_of_day))
        else:
            cursor.execute("SELECT COUNT(*) FROM usage_log WHERE user_id = ? AND datetime(created_at) >= datetime(?)", (user_id, start_str))
        row = cursor.fetchone()
        count = row[0] if row else 0
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Error counting daily usage for user {user_id}: {e}")
        return 0

def log_usage(user_id, task_id, action):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("INSERT INTO usage_log (user_id, task_id, action) VALUES (%s, %s, %s)", (user_id, task_id, action))
        else:
            cursor.execute("INSERT INTO usage_log (user_id, task_id, action) VALUES (?, ?, ?)", (user_id, task_id, action))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error logging usage for user {user_id}: {e}")
        return False

def get_platform_config(key, default=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("SELECT value FROM platform_config WHERE key = %s", (key,))
        else:
            cursor.execute("SELECT value FROM platform_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0] if IS_POSTGRES else row["value"]
        return default
    except Exception as e:
        logger.warning(f"Error reading platform config {key}: {e}")
        return default

def save_platform_config(key, value):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO platform_config (key, value, updated_at) VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
            """, (key, value))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO platform_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving platform config {key}: {e}")
        return False

def get_admin_stats():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks")
        total_tasks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE state IN (0, 4)")
        active_tasks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE cloudinary_url IS NOT NULL AND cloudinary_url != ''")
        cdn_uploads = cursor.fetchone()[0]
        
        conn.close()
        return {
            "total_users": total_users,
            "total_tasks": total_tasks,
            "active_tasks": active_tasks,
            "cdn_uploads": cdn_uploads
        }
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}")
        return {
            "total_users": 0,
            "total_tasks": 0,
            "active_tasks": 0,
            "cdn_uploads": 0
        }

def get_user_total_tasks(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s", (user_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

def get_users_list(page=1, page_size=20, search=""):
    try:
        offset = (page - 1) * page_size
        conn = get_connection()
        cursor = conn.cursor()
        
        where_clause = ""
        params = []
        if search:
            if IS_POSTGRES:
                where_clause = "WHERE user_id ILIKE %s OR email ILIKE %s"
                params = [f"%{search}%", f"%{search}%"]
            else:
                where_clause = "WHERE user_id LIKE ? OR email LIKE ?"
                params = [f"%{search}%", f"%{search}%"]
                
        count_query = f"SELECT COUNT(*) FROM users {where_clause}"
        cursor.execute(count_query, tuple(params))
        total = cursor.fetchone()[0]
        
        if IS_POSTGRES:
            users_query = f"SELECT user_id, email, role, plan, quota_videos_per_day, quota_videos_per_month, is_active, created_at FROM users {where_clause} ORDER BY created_at DESC LIMIT %s OFFSET %s"
            cursor.execute(users_query, tuple(params + [page_size, offset]))
        else:
            users_query = f"SELECT user_id, email, role, plan, quota_videos_per_day, quota_videos_per_month, is_active, created_at FROM users {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?"
            cursor.execute(users_query, tuple(params + [page_size, offset]))
            
        rows = cursor.fetchall()
        users = []
        for row in rows:
            if IS_POSTGRES:
                u_id = row[0]
                user_dict = {
                    "user_id": u_id,
                    "email": row[1],
                    "role": row[2],
                    "plan": row[3],
                    "quota_videos_per_day": row[4],
                    "quota_videos_per_month": row[5],
                    "is_active": bool(row[6]),
                    "created_at": row[7]
                }
            else:
                u_id = row["user_id"]
                user_dict = {
                    "user_id": u_id,
                    "email": row["email"],
                    "role": row["role"],
                    "plan": row["plan"],
                    "quota_videos_per_day": row["quota_videos_per_day"],
                    "quota_videos_per_month": row["quota_videos_per_month"],
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"]
                }
            users.append(user_dict)
        conn.close()
        
        for u in users:
            u["usage_today"] = get_usage_today(u["user_id"])
            u["total_tasks"] = get_user_total_tasks(u["user_id"])
            
        return users, total
    except Exception as e:
        logger.error(f"Error fetching users list: {e}")
        return [], 0

def get_all_tasks_admin(page=1, page_size=50):
    try:
        offset = (page - 1) * page_size
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM tasks")
        total = cursor.fetchone()[0]
        
        if IS_POSTGRES:
            cursor.execute("""
                SELECT tasks.*, users.email AS user_email 
                FROM tasks 
                LEFT JOIN users ON tasks.user_id = users.user_id 
                ORDER BY tasks.created_at DESC LIMIT %s OFFSET %s
            """, (page_size, offset))
        else:
            cursor.execute("""
                SELECT tasks.*, users.email AS user_email 
                FROM tasks 
                LEFT JOIN users ON tasks.user_id = users.user_id 
                ORDER BY tasks.created_at DESC LIMIT ? OFFSET ?
            """, (page_size, offset))
            
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        
        tasks = []
        for row in rows:
            if hasattr(row, 'keys'):
                data = dict(row)
            else:
                data = dict(zip(columns, row))
                
            for field in ["params", "videos", "combined_videos", "materials"]:
                if field in data and data[field]:
                    try:
                        if isinstance(data[field], str):
                            data[field] = json.loads(data[field])
                    except Exception:
                        pass
            tasks.append(data)
        return tasks, total
    except Exception as e:
        logger.error(f"Error fetching all tasks for admin: {e}")
        return [], 0


# --- HELPER FUNCTIONS FOR VIRAL SCORING ---
def save_viral_score(script: str, platform: str, scores: dict, task_id: str = None) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO viral_scores (task_id, script, platform, hook_score, emotion_score, clarity_score, pacing_score, cta_score, overall_score, improvement_tip)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                task_id,
                script,
                platform,
                scores.get("hook_score", 5),
                scores.get("emotion_score", 5),
                scores.get("clarity_score", 5),
                scores.get("pacing_score", 5),
                scores.get("cta_score", 5),
                scores.get("overall_score", 50),
                scores.get("improvement_tip", "")
            ))
        else:
            cursor.execute("""
                INSERT INTO viral_scores (task_id, script, platform, hook_score, emotion_score, clarity_score, pacing_score, cta_score, overall_score, improvement_tip)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                script,
                platform,
                scores.get("hook_score", 5),
                scores.get("emotion_score", 5),
                scores.get("clarity_score", 5),
                scores.get("pacing_score", 5),
                scores.get("cta_score", 5),
                scores.get("overall_score", 50),
                scores.get("improvement_tip", "")
            ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving viral score: {e}")
        return False

def get_viral_score(task_id: str) -> dict:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("""
                SELECT hook_score, emotion_score, clarity_score, pacing_score, cta_score, overall_score, improvement_tip, platform, created_at 
                FROM viral_scores 
                WHERE task_id = %s 
                LIMIT 1
            """, (task_id,))
        else:
            cursor.execute("""
                SELECT hook_score, emotion_score, clarity_score, pacing_score, cta_score, overall_score, improvement_tip, platform, created_at 
                FROM viral_scores 
                WHERE task_id = ? 
                LIMIT 1
            """, (task_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            if IS_POSTGRES:
                return {
                    "hook_score": row[0],
                    "emotion_score": row[1],
                    "clarity_score": row[2],
                    "pacing_score": row[3],
                    "cta_score": row[4],
                    "overall_score": row[5],
                    "improvement_tip": row[6],
                    "platform": row[7],
                    "created_at": row[8]
                }
            else:
                return {
                    "hook_score": row["hook_score"],
                    "emotion_score": row["emotion_score"],
                    "clarity_score": row["clarity_score"],
                    "pacing_score": row["pacing_score"],
                    "cta_score": row["cta_score"],
                    "overall_score": row["overall_score"],
                    "improvement_tip": row["improvement_tip"],
                    "platform": row["platform"],
                    "created_at": row["created_at"]
                }
        return None
    except Exception as e:
        logger.error(f"Error fetching viral score for task {task_id}: {e}")
        return None

# --- HELPER FUNCTIONS FOR TREND CACHE ---
def get_cached_trends(platform: str, category: str, max_age_minutes: int = 60) -> list:
    try:
        from datetime import datetime, timedelta, timezone
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            # Compute the threshold timestamp on the Python side (same approach as SQLite).
            # Embedding %s inside a SQL string literal (e.g. INTERVAL '%s minutes') is NOT
            # treated as a psycopg2 placeholder — the substitution never happens, producing
            # an invalid interval and a psycopg2 error.
            threshold = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
            cursor.execute("""
                SELECT topic, platform, score, category, suggested_hook, fetched_at 
                FROM trend_cache 
                WHERE platform = %s AND category = %s AND fetched_at >= %s
                ORDER BY score DESC
            """, (platform, category, threshold))
        else:
            time_threshold = (datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                SELECT topic, platform, score, category, suggested_hook, fetched_at 
                FROM trend_cache 
                WHERE platform = ? AND category = ? AND datetime(fetched_at) >= datetime(?)
                ORDER BY score DESC
            """, (platform, category, time_threshold))
        rows = cursor.fetchall()
        conn.close()
        
        trends = []
        for row in rows:
            if IS_POSTGRES:
                trends.append({
                    "topic": row[0],
                    "platform": row[1],
                    "score": row[2],
                    "category": row[3],
                    "suggested_hook": row[4],
                    "fetched_at": row[5]
                })
            else:
                trends.append({
                    "topic": row["topic"],
                    "platform": row["platform"],
                    "score": row["score"],
                    "category": row["category"],
                    "suggested_hook": row["suggested_hook"],
                    "fetched_at": row["fetched_at"]
                })
        return trends
    except Exception as e:
        logger.error(f"Error reading cached trends: {e}")
        return []

def save_trends(trends_list: list) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if trends_list:
            platform = trends_list[0].get("platform")
            category = trends_list[0].get("category")
            if platform and category:
                if IS_POSTGRES:
                    cursor.execute("DELETE FROM trend_cache WHERE platform = %s AND category = %s", (platform, category))
                else:
                    cursor.execute("DELETE FROM trend_cache WHERE platform = ? AND category = ?", (platform, category))
        
        for t in trends_list:
            if IS_POSTGRES:
                cursor.execute("""
                    INSERT INTO trend_cache (topic, platform, score, category, suggested_hook, fetched_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    t.get("topic"),
                    t.get("platform"),
                    t.get("score", 0),
                    t.get("category"),
                    t.get("suggested_hook", ""),
                ))
            else:
                cursor.execute("""
                    INSERT INTO trend_cache (topic, platform, score, category, suggested_hook, fetched_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    t.get("topic"),
                    t.get("platform"),
                    t.get("score", 0),
                    t.get("category"),
                    t.get("suggested_hook", ""),
                ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving trends: {e}")
        return False


# --- HELPER FUNCTIONS FOR MULTI-PLATFORM OAUTH ---
def save_platform_oauth(user_id, platform, access_token, refresh_token, token_expiry, channel_id, channel_name):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO platform_oauth (user_id, platform, access_token, refresh_token, token_expiry, channel_id, channel_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, platform) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    token_expiry = EXCLUDED.token_expiry,
                    channel_id = EXCLUDED.channel_id,
                    channel_name = EXCLUDED.channel_name
            """, (user_id, platform, access_token, refresh_token, token_expiry, channel_id, channel_name))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO platform_oauth (user_id, platform, access_token, refresh_token, token_expiry, channel_id, channel_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, platform, access_token, refresh_token, token_expiry, channel_id, channel_name))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving platform oauth settings for {user_id}/{platform}: {e}")
        return False

def get_platform_oauth(user_id, platform):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("SELECT access_token, refresh_token, token_expiry, channel_id, channel_name FROM platform_oauth WHERE user_id = %s AND platform = %s LIMIT 1", (user_id, platform))
        else:
            cursor.execute("SELECT access_token, refresh_token, token_expiry, channel_id, channel_name FROM platform_oauth WHERE user_id = ? AND platform = ? LIMIT 1", (user_id, platform))
        row = cursor.fetchone()
        conn.close()
        if row:
            if IS_POSTGRES:
                return {
                    "access_token": row[0],
                    "refresh_token": row[1],
                    "token_expiry": row[2],
                    "channel_id": row[3],
                    "channel_name": row[4]
                }
            else:
                return {
                    "access_token": row["access_token"],
                    "refresh_token": row["refresh_token"],
                    "token_expiry": row["token_expiry"],
                    "channel_id": row["channel_id"],
                    "channel_name": row["channel_name"]
                }
        return None
    except Exception as e:
        logger.error(f"Error getting platform oauth settings for {user_id}/{platform}: {e}")
        return None

def delete_platform_oauth(user_id, platform):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("DELETE FROM platform_oauth WHERE user_id = %s AND platform = %s", (user_id, platform))
        else:
            cursor.execute("DELETE FROM platform_oauth WHERE user_id = ? AND platform = ?", (user_id, platform))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error deleting platform oauth settings for {user_id}/{platform}: {e}")
        return False

# --- HELPER FUNCTIONS FOR SMART SCHEDULING ---
def create_scheduled_post(task_id, user_id, platform, scheduled_at, status="pending"):
    try:
        from datetime import datetime
        if isinstance(scheduled_at, datetime):
            scheduled_at_str = scheduled_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            scheduled_at_str = str(scheduled_at).replace('T', ' ').split('.')[0].split('+')[0]
            
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO scheduled_posts (task_id, user_id, platform, scheduled_at, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (task_id, user_id, platform, scheduled_at, status))
            post_id = cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO scheduled_posts (task_id, user_id, platform, scheduled_at, status)
                VALUES (?, ?, ?, ?, ?)
            """, (task_id, user_id, platform, scheduled_at_str, status))
            post_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return post_id
    except Exception as e:
        logger.error(f"Error creating scheduled post for task {task_id}: {e}")
        return None

def get_scheduled_posts(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("SELECT id, task_id, user_id, platform, scheduled_at, status, result, created_at FROM scheduled_posts WHERE user_id = %s ORDER BY scheduled_at DESC", (user_id,))
        else:
            cursor.execute("SELECT id, task_id, user_id, platform, scheduled_at, status, result, created_at FROM scheduled_posts WHERE user_id = ? ORDER BY scheduled_at DESC", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        posts = []
        for row in rows:
            if IS_POSTGRES:
                posts.append({
                    "id": row[0],
                    "task_id": row[1],
                    "user_id": row[2],
                    "platform": row[3],
                    "scheduled_at": row[4],
                    "status": row[5],
                    "result": row[6],
                    "created_at": row[7]
                })
            else:
                posts.append({
                    "id": row["id"],
                    "task_id": row["task_id"],
                    "user_id": row["user_id"],
                    "platform": row["platform"],
                    "scheduled_at": row["scheduled_at"],
                    "status": row["status"],
                    "result": row["result"],
                    "created_at": row["created_at"]
                })
        return posts
    except Exception as e:
        logger.error(f"Error getting scheduled posts for user {user_id}: {e}")
        return []

def get_due_scheduled_posts():
    try:
        from datetime import datetime, timezone
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("""
                SELECT id, task_id, user_id, platform, scheduled_at, status, result, created_at 
                FROM scheduled_posts 
                WHERE status = 'pending' AND scheduled_at <= NOW()
            """)
        else:
            cursor.execute("""
                SELECT id, task_id, user_id, platform, scheduled_at, status, result, created_at 
                FROM scheduled_posts 
                WHERE status = 'pending' AND datetime(scheduled_at) <= datetime(?)
            """, (now_str,))
        rows = cursor.fetchall()
        conn.close()
        
        posts = []
        for row in rows:
            if IS_POSTGRES:
                posts.append({
                    "id": row[0],
                    "task_id": row[1],
                    "user_id": row[2],
                    "platform": row[3],
                    "scheduled_at": row[4],
                    "status": row[5],
                    "result": row[6],
                    "created_at": row[7]
                })
            else:
                posts.append({
                    "id": row["id"],
                    "task_id": row["task_id"],
                    "user_id": row["user_id"],
                    "platform": row["platform"],
                    "scheduled_at": row["scheduled_at"],
                    "status": row["status"],
                    "result": row["result"],
                    "created_at": row["created_at"]
                })
        return posts
    except Exception as e:
        logger.error(f"Error getting due scheduled posts: {e}")
        return []

def update_scheduled_post(post_id, status, result):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("UPDATE scheduled_posts SET status = %s, result = %s WHERE id = %s", (status, result, post_id))
        else:
            cursor.execute("UPDATE scheduled_posts SET status = ?, result = ? WHERE id = ?", (status, result, post_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating scheduled post {post_id}: {e}")
        return False

def cancel_scheduled_post(post_id, user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("DELETE FROM scheduled_posts WHERE id = %s AND user_id = %s", (post_id, user_id))
        else:
            cursor.execute("DELETE FROM scheduled_posts WHERE id = ? AND user_id = ?", (post_id, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error deleting/canceling scheduled post {post_id} for user {user_id}: {e}")
        return False

