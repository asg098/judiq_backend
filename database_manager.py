














import sqlite3
import json
import logging
from datetime import datetime
logger = logging.getLogger(__name__)
DB_PATH = "analytics.db"
class DatabaseManager:
    @staticmethod
    def init_db():
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saved_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    case_data TEXT,
                    analysis_result TEXT,
                    score REAL,
                    verdict TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # --- CASEROOM TABLES ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS caserooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caseroom_id TEXT UNIQUE NOT NULL,
                    case_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    status TEXT DEFAULT 'ACTIVE',
                    created_at TEXT,
                    FOREIGN KEY (case_id) REFERENCES saved_cases(case_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS caseroom_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caseroom_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT DEFAULT 'RESEARCHER', -- LEAD_COUNSEL, ASSOCIATE, RESEARCHER, CLIENT
                    joined_at TEXT,
                    UNIQUE(caseroom_id, user_id),
                    FOREIGN KEY (caseroom_id) REFERENCES caserooms(caseroom_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS caseroom_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caseroom_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT,
                    FOREIGN KEY (caseroom_id) REFERENCES caserooms(caseroom_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS caseroom_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caseroom_id TEXT NOT NULL,
                    uploader_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    doc_type TEXT, -- CHEQUE, MEMO, NOTICE, 65B, etc.
                    validation_status TEXT DEFAULT 'PENDING',
                    version INTEGER DEFAULT 1,
                    created_at TEXT,
                    FOREIGN KEY (caseroom_id) REFERENCES caserooms(caseroom_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS caseroom_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caseroom_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date TEXT,
                    status TEXT DEFAULT 'PENDING', -- PENDING, COMPLETED, OVERDUE
                    created_at TEXT,
                    FOREIGN KEY (caseroom_id) REFERENCES caserooms(caseroom_id)
                )
            """)

            conn.commit()
            conn.close()
            logger.info("Database and Caseroom tables initialized successfully.")
        except Exception as e:
            logger.error(f"Database init failed: {e}")
            raise e

    @staticmethod
    def save_case(case_id, user_id, case_data, analysis_result, score, verdict):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO saved_cases 
                (case_id, user_id, case_data, analysis_result, score, verdict, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case_id, 
                user_id, 
                json.dumps(case_data), 
                json.dumps(analysis_result), 
                score, 
                verdict,
                now,
                now
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save case {case_id}: {e}")
            return False

    @staticmethod
    def get_case(case_id):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM saved_cases WHERE case_id = ?", (case_id,))
            row = cursor.fetchone()
            conn.close()
            return row
        except Exception as e:
            logger.error(f"Failed to fetch case {case_id}: {e}")
            return None

    @staticmethod
    def get_caseroom_by_case_id(case_id):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT caseroom_id FROM caserooms WHERE case_id = ?", (case_id,))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to fetch caseroom by case_id {case_id}: {e}")
            return None

    @staticmethod
    def create_caseroom(caseroom_id, case_id, owner_id):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO caserooms (caseroom_id, case_id, owner_id, created_at)
                VALUES (?, ?, ?, ?)
            """, (caseroom_id, case_id, owner_id, now))
            
            # Add owner as Lead Counsel
            cursor.execute("""
                INSERT INTO caseroom_participants (caseroom_id, user_id, role, joined_at)
                VALUES (?, ?, 'LEAD_COUNSEL', ?)
            """, (caseroom_id, owner_id, now))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to create caseroom {caseroom_id}: {e}")
            return False

    @staticmethod
    def add_participant(caseroom_id, user_id, role="RESEARCHER"):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT OR IGNORE INTO caseroom_participants (caseroom_id, user_id, role, joined_at)
                VALUES (?, ?, ?, ?)
            """, (caseroom_id, user_id, role, now))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to add participant to {caseroom_id}: {e}")
            return False

    @staticmethod
    def get_caseroom_data(caseroom_id):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Fetch basic info
            cursor.execute("SELECT * FROM caserooms WHERE caseroom_id = ?", (caseroom_id,))
            room = cursor.fetchone()
            if not room: return None
            
            # Fetch participants
            cursor.execute("SELECT user_id, role FROM caseroom_participants WHERE caseroom_id = ?", (caseroom_id,))
            participants = [{"user_id": r[0], "role": r[1]} for r in cursor.fetchall()]
            
            # Fetch messages
            cursor.execute("SELECT user_id, content, created_at FROM caseroom_messages WHERE caseroom_id = ? ORDER BY created_at ASC", (caseroom_id,))
            messages = [{"user_id": r[0], "content": r[1], "timestamp": r[2]} for r in cursor.fetchall()]
            
            # Fetch tasks
            cursor.execute("SELECT id, title, status, due_date FROM caseroom_tasks WHERE caseroom_id = ?", (caseroom_id,))
            tasks = [{"id": r[0], "title": r[1], "status": r[2], "due_date": r[3]} for r in cursor.fetchall()]
            
            conn.close()
            return {
                "room_info": room,
                "participants": participants,
                "messages": messages,
                "tasks": tasks
            }
        except Exception as e:
            logger.error(f"Failed to fetch caseroom data for {caseroom_id}: {e}")
            return None

    @staticmethod
    def send_message(caseroom_id, user_id, content):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO caseroom_messages (caseroom_id, user_id, content, created_at)
                VALUES (?, ?, ?, ?)
            """, (caseroom_id, user_id, content, now))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to send message in {caseroom_id}: {e}")
            return False
