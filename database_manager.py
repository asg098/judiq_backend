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
            cursor.execute('''
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
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_cases ON saved_cases(user_id)')
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Database init failed: {e}")

    @staticmethod
    def save_case(user_id, case_id, case_data, analysis_result):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO saved_cases 
                (case_id, user_id, case_data, analysis_result, score, verdict, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    case_data=excluded.case_data,
                    analysis_result=excluded.analysis_result,
                    score=excluded.score,
                    verdict=excluded.verdict,
                    updated_at=excluded.updated_at
            ''', (
                case_id, 
                user_id, 
                json.dumps(case_data), 
                json.dumps(analysis_result),
                analysis_result.get('score', 0),
                analysis_result.get('verdict', 'Unknown'),
                now, now
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save case: {e}")
            return False

    @staticmethod
    def get_user_cases(user_id):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM saved_cases WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
            rows = cursor.fetchall()
            conn.close()
            
            result_cases = []
            for r in rows:
                case_dict = dict(r)
                try:
                    case_dict['case_data'] = json.loads(case_dict['case_data']) if case_dict.get('case_data') else {}
                    case_dict['analysis_result'] = json.loads(case_dict['analysis_result']) if case_dict.get('analysis_result') else {}
                except Exception:
                    pass
                result_cases.append(case_dict)
                
            return result_cases
        except Exception as e:
            logger.error(f"Failed to fetch cases: {e}")
            return []
