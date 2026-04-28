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

    @staticmethod
    def upload_document(caseroom_id, user_id, file_name, file_path, doc_type, validation_status="PENDING", extracted_data=None):
        """Records a new document upload in the caseroom."""
        return DatabaseManager.save_document(caseroom_id, user_id, file_name, file_path, doc_type, validation_status, extracted_data)

    @staticmethod
    def reanalyze_case_from_documents(caseroom_id, user_id="SYSTEM"):
        """Aggregates OCR extracted data, overrides case_data, and re-analyzes for Reality Score."""
        import json
        from engine_core import JudiQEngine
        
        caseroom_data = DatabaseManager.get_caseroom_data(caseroom_id)
        if not caseroom_data or not caseroom_data.get("room_info"):
            return False, "Caseroom not found"
            
        case_id = caseroom_data["room_info"][1]  # caseroom_info = (caseroom_id, case_id, owner_id, created_at)
        
        original_case = DatabaseManager.get_case(case_id)
        if not original_case:
            return False, "Original case not found"
            
        try:
            case_data = json.loads(original_case[2])  # case_data is index 2
        except:
            return False, "Invalid case data format"
            
        documents = caseroom_data.get("documents", [])
        updates = []
        
        for doc in documents:
            dtype = str(doc.get("doc_type")).upper()
            ext = doc.get("extracted_data") or {}
            
            dates = ext.get("extracted_dates", [])
            amounts = ext.get("extracted_amounts", [])
            
            if dtype == "CHEQUE":
                if amounts:
                    case_data["amount"] = amounts[0]
                    updates.append(f"Cheque Amount -> {amounts[0]}")
                if dates:
                    case_data["cheque_date"] = dates[0]
                    updates.append(f"Cheque Date -> {dates[0]}")
                chq_nums = ext.get("extracted_cheque_numbers", [])
                if chq_nums:
                    case_data["cheque_number"] = chq_nums[0]
                    updates.append(f"Cheque Number -> {chq_nums[0]}")
                    
            elif dtype == "MEMO":
                if dates:
                    case_data["dishonour_date"] = dates[0]
                    updates.append(f"Dishonour Date -> {dates[0]}")
                reasons = ext.get("detected_reasons", [])
                if reasons:
                    case_data["dishonour_reason"] = reasons[0]
                    updates.append(f"Dishonour Reason -> {reasons[0]}")
                    
            elif dtype == "NOTICE":
                if dates:
                    case_data["notice_date"] = dates[0]
                    updates.append(f"Notice Date -> {dates[0]}")
                tracking = ext.get("postal_tracking_numbers", [])
                if tracking:
                    case_data["notice_tracking_number"] = tracking[0]
                    updates.append(f"Postal Tracking -> {tracking[0]}")

            elif dtype == "DEBT_PROOF":
                dp_class = ext.get("debt_proof_class")
                if dp_class:
                    case_data["debt_proof_type"] = dp_class
                    updates.append(f"Debt Proof Classification -> {dp_class}")
        
        if not updates:
            return True, "No new data extracted from documents to update."
            
        case_data["analysis_mode"] = "reality_verified"
        
        # Run the engine with the physically verified data
        new_result = JudiQEngine.analyze_case(case_data)
        
        DatabaseManager.save_case(
            case_id=case_id,
            user_id=original_case[1],
            case_data=case_data,
            analysis_result=new_result,
            score=new_result.get("score", 0),
            verdict=new_result.get("verdict", "Unknown")
        )
        
        msg = f"Re-analyzed case using physical documents. Verified Facts:\n" + "\n".join(updates)
        DatabaseManager.send_message(caseroom_id, user_id, msg)
        
        return True, "Case re-analyzed successfully."
