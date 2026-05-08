import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class AdversarialEngine:
    """
    Dynamic Adversarial Engine — Simulates courtroom attack chains, 
    calculates probability collapse, and maps litigation outcome branching.
    """

    # Attack Trees based on procedural and evidentiary vulnerabilities
    ATTACK_TREES = {
        "resignation_trap": {
            "name": "The Resignation Attack",
            "trigger": "director_resignation_date < cheque_date",
            "chain": [
                "1. Accused Director files for Quashing (S.482 CrPC).",
                "2. Demonstrates resignation via Form DIR-11/DIR-12 filed with ROC.",
                "3. Complaint is quashed against that specific director.",
                "4. Complainant faces 'Malicious Prosecution' counter-suit."
            ],
            "probability_collapse": 0.85,
            "rebuttal_strategy": "Verify ROC records BEFORE filing. Only implead directors active on the date of cheque issuance AND date of default.",
            "burden_shift": "Shifts to Complainant to prove the director was 'in charge of and responsible for' the conduct of business DESPITE resignation."
        },
        "basalingappa_rebuttal": {
            "name": "The Financial Capacity Attack",
            "trigger": "amount > 500000 and not complainant_itr_available",
            "chain": [
                "1. Defence cross-examines on source of funds.",
                "2. Demands ITR records during cross-examination (S.91 CrPC).",
                "3. Failure to produce documents leads to adverse inference (S.114 IEA).",
                "4. S.139 Presumption is successfully rebutted.",
                "5. Prosecution fails as 'Legally Enforceable Debt' is not proven."
            ],
            "probability_collapse": 0.65,
            "rebuttal_strategy": "Produce bank passbooks showing historical savings. Argue that S.139 presumption remains until 'probable' doubt is created.",
            "burden_shift": "Once Accused raises a 'probable' doubt regarding capacity, the burden shifts back to Complainant to prove the source of funds."
        },
        "material_alteration_strike": {
            "name": "The Material Alteration Strike",
            "trigger": "handwriting_different",
            "chain": [
                "1. Defence alleges 'Material Alteration' u/s 87 NI Act.",
                "2. Moves application for Handwriting Expert (S.45 IEA).",
                "3. Expert confirms different inks/handwriting for signature vs body.",
                "4. If alteration is without drawer's consent, instrument is VOID.",
                "5. Immediate Acquittal."
            ],
            "probability_collapse": 0.90,
            "rebuttal_strategy": "Invoke S.20 NI Act — 'Inchoate Stamped Instruments'. Argue that the drawer gave implied authority to the holder to fill the details.",
            "burden_shift": "Heavy burden on Complainant to prove the details were filled with the drawer's consent or at their direction."
        }
    }

    @classmethod
    def simulate_attack_chains(cls, case_data: Dict, concepts: List[Dict]) -> List[Dict]:
        chains = []
        concept_names = {c["concept"] for c in concepts}
        amount = float(case_data.get("amount") or 0)
        
        if case_data.get("director_resignation_date") and case_data.get("cheque_date"):
            if case_data.get("director_resignation_date") < case_data.get("cheque_date"):
                chains.append(cls.ATTACK_TREES["resignation_trap"])

        if amount > 500000 and not case_data.get("complainant_itr_available"):
            chains.append(cls.ATTACK_TREES["basalingappa_rebuttal"])

        if case_data.get("handwriting_different"):
            chains.append(cls.ATTACK_TREES["material_alteration_strike"])

        return chains

    @classmethod
    def calculate_adversarial_risk(cls, chains: List[Dict]) -> float:
        if not chains: return 0.0
        cumulative_risk = 0.0
        for chain in chains:
            risk = chain.get("probability_collapse", 0.0)
            cumulative_risk = cumulative_risk + (risk * (1.0 - cumulative_risk))
        return round(cumulative_risk, 2)

    @classmethod
    def simulate_courtroom_battle(cls, case_data: Dict, concepts: List[Dict]) -> List[Dict]:
        """Simulates sequential courtroom attack/rebuttal nodes."""
        battle_nodes = []
        chains = cls.simulate_attack_chains(case_data, concepts)
        
        for chain in chains:
            battle_nodes.append({
                "stage": "Cross-Examination",
                "defence_move": chain["chain"][0],
                "complainant_rebuttal": chain.get("rebuttal_strategy", "Rely on S.139 presumption."),
                "witness_risk": chain.get("burden_shift", "Standard procedural risk."),
                "survivability_impact": f"-{int(chain['probability_collapse'] * 100)}%"
            })
            if len(chain["chain"]) > 1:
                battle_nodes.append({
                    "stage": "Evidentiary Challenge",
                    "defence_move": chain["chain"][1],
                    "complainant_rebuttal": "Produce secondary evidence or witness testimony.",
                    "witness_risk": "Risk of being caught in a contradiction during cross-verification.",
                    "survivability_impact": "High"
                })
        
        return battle_nodes

    @classmethod
    def generate_survivability_graph(cls, base_score: int, adversarial_risk: float) -> List[Dict]:
        """Generates data points for a survivability graph over the trial timeline."""
        # Timeline: [Filing, Notice, Framing of Charge, Evidence, Final Argument]
        current_strength = base_score
        graph = [
            {"stage": "Filing", "strength": current_strength},
            {"stage": "Notice", "strength": current_strength * 0.95}
        ]
        
        # Framing of Charge (Risk materializes)
        current_strength *= (1.0 - (adversarial_risk * 0.3))
        graph.append({"stage": "Framing of Charge", "strength": int(current_strength)})
        
        # Evidence (Heaviest hit)
        current_strength *= (1.0 - (adversarial_risk * 0.6))
        graph.append({"stage": "Evidence Phase", "strength": int(current_strength)})
        
        # Final Argument
        graph.append({"stage": "Final Argument", "strength": int(current_strength * 1.1)}) # Slight recovery if survived
        
        return graph

adversarial_engine = AdversarialEngine()
