import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class StrategyEngine:
    """
    Advanced Litigation Strategy Engine — generates actionable litigation maps
    for both Prosecution and Defence based on case strength and evidence gaps.
    """

    @staticmethod
    def generate_litigation_map(case_data: Dict, score: float, concepts: List[Dict], detected_defences: List[Dict] = None) -> Dict[str, Any]:
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
            prosecution["statutory_leverage"].append("Section 143A: File interim compensation application on the first date of framing notice, strictly pleading 'Financial Hardship' to avoid discretionary rejection.")
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
            defence["landmark_defence"].append("Sushil Kumar/Basalingappa Rule: Cross-examine Complainant on their source of funds and ITR non-disclosure for large amounts.")

        if "security_cheque" in concept_names:
            defence["landmark_defence"].append("Security Defense: Establish that no debt was due on the date of cheque issuance (Indus Airways).")

        # 3. Dynamic Defense Simulation (New Hardening)
        simulated_defences = []
        if detected_defences:
            for d in detected_defences:
                simulated_defences.append({
                    "defence_name": d.get("name", "Unknown Defense"),
                    "simulation_impact": f"Lowers conviction probability by {int(d.get('confidence', 0.5) * 40)}%. Rebuts S.139 presumption.",
                    "counter_move": d.get("rebuttal", "Provide documentary evidence of the underlying debt.")
                })
        
        if not simulated_defences and "security_cheque" in concept_names:
            simulated_defences.append({
                "defence_name": "Security Cheque Defense",
                "simulation_impact": "HIGH IMPACT. If the accused proves the cheque was given for security and not for an existing debt, the case is liable to be dismissed.",
                "counter_move": "Show that on the date of cheque presentation, a legally enforceable debt equal to the cheque amount had accrued."
            })

        return {
            "prosecution_map": prosecution,
            "defence_map": defence,
            "defense_simulation": simulated_defences or "No active defenses detected for simulation.",
            "overall_strategy": "Aggressive Prosecution" if score > 70 else "Strategic Settlement"
        }
