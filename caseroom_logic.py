


import logging
import uuid
import sqlite3
from datetime import datetime
from database_manager import DatabaseManager, DB_PATH
logger = logging.getLogger(__name__)
class CaseroomManager:
    @staticmethod
    def initialize_caseroom_for_case(case_id, owner_id):
        """Creates a new caseroom for a newly registered case."""
        caseroom_id = f"CR_{uuid.uuid4().hex[:8].upper()}"
        success = DatabaseManager.create_caseroom(caseroom_id, case_id, owner_id)
        if success:
            logger.info(f"✅ Caseroom {caseroom_id} initialized for case {case_id}")
            # Add initial welcome message
            DatabaseManager.send_message(caseroom_id, "SYSTEM", f"Welcome to the Caseroom for Case {case_id}. Strategy discussions and evidence management starts here.")
            return caseroom_id
        return None
    @staticmethod
    def invite_collaborator(caseroom_id, user_id, role):
        """Invites a new lawyer/collaborator to the caseroom."""
        return DatabaseManager.add_participant(caseroom_id, user_id, role)

    @staticmethod
    def get_full_caseroom_state(caseroom_id):
        """Fetches the entire state of the caseroom for real-time sync."""
        return DatabaseManager.get_caseroom_data(caseroom_id)

    @staticmethod
    def post_comment(caseroom_id, user_id, text):
        """Posts a message/strategy comment in the caseroom."""
        return DatabaseManager.send_message(caseroom_id, user_id, text)

    @staticmethod
    def add_milestone(caseroom_id, title, due_date, description=""):
        """Adds a task or milestone to the caseroom timeline."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO caseroom_tasks (caseroom_id, title, description, due_date, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (caseroom_id, title, description, due_date, now))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to add task: {e}")
            return False
