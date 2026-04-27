import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class StrategyEngine:
    """
    Advanced Litigation Strategy Engine — generates actionable litigation maps
    for both Prosecution and Defence based on case strength and evidence gaps.
    """

    @staticmethod
    def generate_litigation_map(case_data: Dict, score: float, concepts: List[Dict]) -> Dict[str, Any]:
        concept_names = {c["concept"] for c in concepts}
        
        # 1. Prosecution Strategy (The Offensive)
        prosecution = {
            "primary_objective": "Secure Conviction & Recovery",
            "tactical_moves": [],
            "evidentiary_tasks": [],
            "statutory_leverage": []
        }

        if score >= 70:
            prosecution["tactical_moves"].append("Aggressive Trial: Push for daily hearings and early framing of charge.")
            prosecution["statutory_leverage"].append("Section 143A: File interim compensation application on the first date of framing notice.")
        else:
            prosecution["tactical_moves"].append("Settlement Focus: Use the threat of trial to push for a structured repayment plan.")
            prosecution["evidentiary_tasks"].append("Corroboration: Secure bank statements and income tax records to bolster 'Financial Capacity'.")

        if "signature_dispute" in concept_names:
            prosecution["evidentiary_tasks"].append("Forensic Readiness: Keep original documents ready for S.45 Evidence Act expert comparison.")

        # 2. Defence Strategy (The Defensive)
        defence = {
            "primary_objective": "Rebut Presumption & Acquittal",
            "tactical_moves": [],
            "evidentiary_tasks": [],
            "landmark_defence": []
        }

        if score >= 75:
            defence["tactical_moves"].append("Delay & Negotiate: Explore compounding options as conviction probability is high.")
        else:
            defence["tactical_moves"].append("Rebuttal Mode: Challenge the 'legally enforceable debt' by exposing gaps in consideration.")
            
        if "financial_capacity_risk" in concept_names:
            defence["landmark_defence"].append("Basalingappa Rule: Cross-examine Complainant on their source of funds and ITR non-disclosure.")

        if "security_cheque" in concept_names:
            defence["landmark_defence"].append("Security Defense: Establish that no debt was due on the date of cheque issuance (Indus Airways).")

        return {
            "prosecution_map": prosecution,
            "defence_map": defence,
            "overall_strategy": "Aggressive Prosecution" if score > 70 else "Strategic Settlement"
        }
