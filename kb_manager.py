import json
import os
import logging
logger = logging.getLogger(__name__)
class KnowledgeBaseManager:
    _instance = None
    _data = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KnowledgeBaseManager, cls).__new__(cls)
            cls._instance._load_kb()
        return cls._instance
    def _load_kb(self):
        kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
        try:
            with open(kb_path, "r") as f:
                self._data = json.load(f)
            logger.info("Knowledge Base loaded successfully from JSON.")
        except Exception as e:
            logger.error(f"Failed to load Knowledge Base from {kb_path}: {e}")
            self._data = {}
    def get_semantic_patterns(self):
        return self._data.get("semantic_patterns", {})
    def get_legal_concepts(self):
        return self._data.get("legal_concepts", {})
    def get_knowledge_base(self):
        return self._data.get("knowledge_base", {})
    def get_scoring_catalogue(self):
        return self._data.get("scoring_catalogue", {})
    def get_defence_templates(self):
        return self._data.get("defence_templates", {})
    def get_defence_legal_weights(self):
        return self._data.get("defence_legal_weights", {})
    def get_score_impact(self, concept):
        kb = self.get_knowledge_base()
        return kb.get(concept, {}).get("score_impact", 0)
    def get_risk_level(self, concept):
        kb = self.get_knowledge_base()
        return kb.get(concept, {}).get("risk_level", "LOW")
kb_manager = KnowledgeBaseManager()
