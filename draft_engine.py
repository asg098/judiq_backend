import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DraftEngine:
    @staticmethod
    def generate_opinion(analysis_result: Dict[str, Any]) -> str:
        score = analysis_result.get("score", 0)
        verdict = analysis_result.get("verdict", "Unknown")
        template = f"""
LEGAL OPINION PREVIEW
--------------------
SUBJECT: Section 138 NI Act Analysis
CURRENT STRENGTH: {score}/100 ({verdict})

ANALYSIS:
Based on the provided instrument details and semantic concept detection, the case exhibits {verdict.lower()} characteristics.
"""
        if score < 40:
            template += "\nWARNING: Significant fatal defects (Notice/Signature/Security) detected. Litigation is high-risk."
        else:
            template += "\nProceed with standard litigation protocols. Ensure all physical documents are notarized."
        return template
