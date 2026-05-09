from typing import Dict, List, Any
class AdversarialEngine:
    """
    Elite Adversarial Engine — Simulates courtroom dynamics, tactical rebuttal chains,
    and stage-wise procedural survivability mapping.
    """

    # Stage-wise Survivability Baseline (Procedural roadmap)
    PROCEDURAL_STAGES = [
        {"id": "summoning", "name": "Summoning Stage", "baseline_prob": 0.95},
        {"id": "framing", "name": "Notice/Framing of Charge", "baseline_prob": 0.85},
        {"id": "evidence", "name": "Complainant Evidence", "baseline_prob": 0.70},
        {"id": "cross_exam", "name": "Cross-Examination", "baseline_prob": 0.60},
        {"id": "final", "name": "Final Arguments", "baseline_prob": 0.55},
        {"id": "appeal", "name": "Appeal Sustainability", "baseline_prob": 0.45}
    ]

    ATTACK_TREES = {
        "security_cheque": {
            "name": "The Security Cheque Rebuttal",
            "trigger": "agreement_type == 'verbal' or not debt_proven",
            "chain": [
                "1. Defence admits signature but denies 'existing liability'.",
                "2. Argues cheque was given as 'blank security' for a future transaction.",
                "3. Cites 'Sampelly Satyanarayana Rao' to rebut S.139.",
                "4. Shifting burden: Complainant must now prove crystallization of debt."
            ],
            "probability_collapse": 0.55,
            "rebuttal_tree": {
                "defence_evidence": "Lack of invoices / Post-dated nature of instrument.",
                "complainant_counter": "Produce ledger entries showing 'crystallized debt' on cheque date.",
                "burden_shift_effect": "Immediate shift if no documentary proof of debt exists.",
                "magistrate_view": "Likely to stay proceedings for further evidence.",
                "conviction_impact": -25
            }
        },
        "financial_capacity": {
            "name": "Basalingappa Capacity Challenge",
            "trigger": "amount > 200000 and not complainant_itr_available",
            "chain": [
                "1. Defence challenges Complainant's 'source of funds'.",
                "2. Questions how such a large amount was available in cash.",
                "3. Argues violation of Income Tax laws (S.269SS/ST).",
                "4. Adverse inference drawn due to non-production of ITR."
            ],
            "probability_collapse": 0.68,
            "rebuttal_tree": {
                "defence_evidence": "ITR history / Bank balance of Complainant.",
                "complainant_counter": "Argue 'friendly loan' from savings; cite 'Rangappa v. Mohan'.",
                "burden_shift_effect": "Shifts to Complainant to prove financial standing.",
                "magistrate_view": "Highly skeptical of high-value cash transactions without ITR.",
                "conviction_impact": -35
            }
        },
        "material_alteration": {
            "name": "S.87 Material Alteration Trap",
            "trigger": "handwriting_different or ink_different",
            "chain": [
                "1. Defence alleges cheque was 'completed' by Complainant without consent.",
                "2. Points to different ink/handwriting in date/amount fields.",
                "3. Argues 'material alteration' voids the instrument under Section 87.",
                "4. Requests Forensic (FSL) examination of handwriting."
            ],
            "probability_collapse": 0.82,
            "rebuttal_tree": {
                "defence_evidence": "Visual inspection of ink/handwriting variation.",
                "complainant_counter": "Cite 'Bir Singh v. Mukesh Kumar' - authority to fill blank cheque.",
                "burden_shift_effect": "High risk of trial stay for FSL report.",
                "magistrate_view": "Extreme caution if alteration is visible to naked eye.",
                "conviction_impact": -45
            }
        },
        "vicarious_liability": {
            "name": "Section 141 Misjoinder",
            "trigger": "is_company and not directors_named",
            "chain": [
                "1. Defence argues Company was not impleaded or directors had no role.",
                "2. Cites 'Aneeta Hada v. Godfather Travels'.",
                "3. Argues 'Director' is not 'in charge of and responsible to' the company.",
                "4. Seeks quashing under S.482 CrPC."
            ],
            "probability_collapse": 0.90,
            "rebuttal_tree": {
                "defence_evidence": "Resignation letters / MCA records.",
                "complainant_counter": "Show 'Director' signature on the cheque or active role in debt.",
                "burden_shift_effect": "Fatal defect if Company is not a party.",
                "magistrate_view": "Strict adherence to statutory mandatory impleadment.",
                "conviction_impact": -50
            }
        }
    }

    @classmethod
    def calculate_stage_survivability(cls, score: int, adversarial_risk: float) -> List[Dict]:
        """Calculates quantified probability of surviving each stage of litigation."""
        roadmap = []
        current_risk_multiplier = 1.0 - (adversarial_risk * 0.7) # Aggressive risk weighting
        
        for stage in cls.PROCEDURAL_STAGES:
            prob = stage["baseline_prob"] * (score / 100.0) * current_risk_multiplier
            
            if stage["id"] == "cross_exam":
                prob *= 0.75 # Heaviest collapse point
                
            roadmap.append({
                "stage": stage["name"],
                "probability": f"{int(max(2, min(98, prob * 100)))}%",
                "status": "Vulnerable" if prob < 0.45 else ("Stable" if prob > 0.7 else "Caution"),
                "risk_factor": "Cross-exam fumble" if stage["id"] == "cross_exam" else "Procedural bar"
            })
            current_risk_multiplier *= 0.92
            
        return roadmap

    @classmethod
    def simulate_courtroom_battle(cls, case_data: Dict, concepts: List[Dict]) -> List[Dict]:
        """Deep modeling of tactical exchanges and rebuttal trees."""
        battle_nodes = []
        concept_names = {c["concept"] for c in concepts}
        amount = float(case_data.get("amount") or 0)
        accused_name = str(case_data.get("accused_name", "")).lower()
        is_company = any(x in accused_name for x in ["pvt", "ltd", "corp", "inc", "co.", "company"])

        # 1. Security Cheque Logic
        if not case_data.get("debt_proven") or "security_cheque" in concept_names:
            battle_nodes.append(cls._build_node(cls.ATTACK_TREES["security_cheque"], "Security Cheque Defense"))

        # 2. Financial Capacity Logic
        if amount > 150000 and not case_data.get("complainant_itr_available"):
            battle_nodes.append(cls._build_node(cls.ATTACK_TREES["financial_capacity"], "Capacity Challenge"))

        # 3. Material Alteration Logic
        if case_data.get("handwriting_different") or "material_alteration" in concept_names:
            battle_nodes.append(cls._build_node(cls.ATTACK_TREES["material_alteration"], "S.87 Material Alteration"))

        # 4. Vicarious Liability Logic
        if is_company and not case_data.get("directors_named"):
            battle_nodes.append(cls._build_node(cls.ATTACK_TREES["vicarious_liability"], "S.141 Company Defect"))

        return battle_nodes

    @classmethod
    def _build_node(cls, tree: Dict, vector_name: str) -> Dict:
        return {
            "attack_vector": vector_name,
            "tactical_chain": tree["chain"],
            "rebuttal_tree": tree["rebuttal_tree"],
            "survival_probability": f"{int((1.0 - tree['probability_collapse']) * 100)}%",
            "destruction_probability": f"{int(tree['probability_collapse'] * 100)}%",
            "courtroom_dynamics": {
                "hostile_question": f"Is it not true that the {vector_name.lower()} logic invalidates your claim?",
                "witness_fatigue_risk": "HIGH" if tree["probability_collapse"] > 0.6 else "MEDIUM",
                "contradiction_escalation": "Defence will contrast the notice demand with cross-exam admissions."
            }
        }

    @classmethod
    def audit_case(cls, case_data: Dict, concepts: List[Dict]) -> Dict:
        """Central audit method for the orchestrator."""
        battle_nodes = cls.simulate_courtroom_battle(case_data, concepts)
        
        # Dynamic risk calculation based on active nodes
        base_risk = 0.15
        for node in battle_nodes:
            # Extract probability from string "82%"
            try:
                dest_prob = float(node["destruction_probability"].strip('%')) / 100.0
                base_risk += (dest_prob * 0.3)
            except: base_risk += 0.1
            
        return {
            "risks_and_rebuttals": battle_nodes,
            "contradictions": [], 
            "adversarial_risk": min(0.95, base_risk)
        }

    @classmethod
    def calculate_adversarial_risk(cls, battle_nodes: List[Dict]) -> float:
        if not battle_nodes: return 0.1
        risk = 0.2
        for node in battle_nodes:
            risk += 0.15
        return min(0.9, risk)
