import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class PrecedentManager:
    """
    Handles live ingestion and tagging of judicial precedents to keep the
    knowledge base synchronized with evolving case law.
    """
    def __init__(self):
        self.kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
        self.log_path = os.path.join(os.path.dirname(__file__), "precedent_log.json")
        self._ensure_log_exists()

    def _ensure_log_exists(self):
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w") as f:
                json.dump({"updates": [], "last_sync": None}, f)

    def ingest_judgment(self, title: str, citation: str, impact_area: str, summary: str):
        """
        Simulates ingestion of a new judgment. 
        In production, this would be an automated scraper hook.
        """
        update_record = {
            "title": title,
            "citation": citation,
            "impact_area": impact_area,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            with open(self.log_path, "r") as f:
                log = json.load(f)
            
            log["updates"].append(update_record)
            log["last_sync"] = datetime.now().isoformat()
            
            with open(self.log_path, "w") as f:
                json.dump(log, f, indent=2)
            
            logger.info(f"Ingested new precedent: {citation}")
            return True
        except Exception as e:
            logger.error(f"Failed to ingest precedent: {e}")
            return False

    def get_latest_precedents(self, limit: int = 5) -> List[Dict]:
        try:
            with open(self.log_path, "r") as f:
                log = json.load(f)
            return log["updates"][-limit:][::-1]
        except:
            return []

precedent_manager = PrecedentManager()
