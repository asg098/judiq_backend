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
    def detect_contradictions(cls, case_data: Dict, concepts: List[Dict]) -> List[Dict]:
        """
        Contradiction Engine v2: Detects mutually exclusive facts with severity propagation.
        Severities: 
        - Minor inconsistency: Subtle variations in narrative.
        - Strategic contradiction: Tactical opening for the defence.
        - Fatal credibility collapse: Destroys the entire cause of action.
        """
        contradictions = []
        concept_names = [c["concept"] for c in concepts]
        
        # 1. Notice/Service Contradiction
        if "notice_not_served" in concept_names and case_data.get("reply_received"):
            contradictions.append({
                "severity": "Fatal credibility collapse",
                "issue": "Notice Service Paradox",
                "detail": "Claiming 'Notice not served' while admitting 'Reply received' is an impossible legal state. Magistrate will likely dismiss at summoning stage.",
                "remediation": "Immediately amend complaint to acknowledge service/reply.",
                "penalty": -45
            })
            
        # 2. Debt/Payment Contradiction
        if "no_debt_proof" in concept_names and case_data.get("partial_payment_admitted"):
            contradictions.append({
                "severity": "Strategic contradiction",
                "issue": "Debt Existence Conflict",
                "detail": "Denying debt proof while admitting partial payment creates a tactical opening for 'Basalingappa' attack.",
                "remediation": "Procure ledger showing 'Part Payment' against 'Running Account'.",
                "penalty": -20
            })

        # 3. Director/Role Contradiction
        if "s141_defect" in concept_names and case_data.get("director_signed_cheque"):
            contradictions.append({
                "severity": "Fatal credibility collapse",
                "issue": "Vicarious Liability Conflict",
                "detail": "Claiming no role for director who signed the cheque. Signature is conclusive proof of responsibility u/s 141.",
                "remediation": "Re-draft S.141 averments to focus on the signing director.",
                "penalty": -50
            })

        # 4. Handwriting/Blank Cheque Contradiction
        if case_data.get("handwriting_different") and case_data.get("cheque_issued_at_office"):
             contradictions.append({
                "severity": "Minor inconsistency",
                "issue": "Execution Context Variation",
                "detail": "Different handwriting on a cheque allegedly issued at the office suggests it was a blank security cheque, not a completed instrument.",
                "remediation": "Clarify if the cheque was filled by a clerk under instructions.",
                "penalty": -10
            })

        # --- V3 ENHANCEMENT: CREDIBILITY COLLAPSE SIMULATION ---
        for c in contradictions:
            c["collapse_simulation"] = cls.simulate_credibility_collapse(c)

        return contradictions

    @classmethod
    def simulate_credibility_collapse(cls, contradiction: Dict) -> Dict:
        """
        Simulates how the defense exploits a specific contradiction in court.
        Addresses USER REQUEST 1 (Contradiction Engine v3).
        """
        severity = contradiction["severity"]
        issue = contradiction["issue"]
        
        attack_patterns = {
            "Fatal credibility collapse": {
                "defense_exploit": "Argue 'Absolute Falsity' of the Complainant's case. Seek immediate acquittal.",
                "cross_exam_impact": "Complainant unable to explain the paradox under pressure. High risk of witness breakdown.",
                "survivability_impact": -0.45
            },
            "Strategic contradiction": {
                "defense_exploit": "Create 'Reasonable Doubt' by showing narrative inconsistency. Target S.139 presumption.",
                "cross_exam_impact": "Forcing admissions that contradict the statutory notice. Credibility erosion risk: HIGH.",
                "survivability_impact": -0.18
            },
            "Minor inconsistency": {
                "defense_exploit": "Show lack of 'Careful Record Keeping'. Marginalize Complainant's reliability.",
                "cross_exam_impact": "Expose memory gaps or lack of professional process.",
                "survivability_impact": -0.05
            }
        }
        
        pattern = attack_patterns.get(severity, attack_patterns["Minor inconsistency"])
        return {
            "attack_vector": f"Exploiting {issue}",
            "defense_strategy": pattern["defense_exploit"],
            "cross_exam_prediction": pattern["cross_exam_impact"],
            "quantitative_impact": f"{int(pattern['survivability_impact'] * 100)}%"
        }

    @classmethod
    def run_red_team_attack(cls, case_data: Dict, concepts: List[Dict]) -> List[Dict]:
        """
        EXTREMELY HIGH VALUE: Aggressively attacks the Complainant's case.
        Addresses USER REQUEST 6.
        """
        attacks = []
        contradictions = cls.detect_contradictions(case_data, concepts)
        
        for c in contradictions:
            attacks.append({
                "target": c["issue"],
                "attack": f"Destructive exploit of {c['severity'].lower()}",
                "hostile_argument": f"Your entire narrative is a fabrication, as evidenced by the {c['issue']}.",
                "lethality": "FATAL" if "Fatal" in c["severity"] else "HIGH"
            })
            
        # Attack assumptions
        if not case_data.get("loan_via_bank") and float(case_data.get("amount") or 0) > 50000:
            attacks.append({
                "target": "Loan Transaction Assumption",
                "attack": "Violation of S.269SS Income Tax Act",
                "hostile_argument": "This cash transaction never occurred. No withdrawal record exists, and it violates anti-black money statutes.",
                "lethality": "CRITICAL"
            })
            
        if not case_data.get("itr_available"):
            attacks.append({
                "target": "Financial Capacity Assumption",
                "attack": "Basalingappa Inference Attack",
                "hostile_argument": "You are a 'person of small means' with no documented capacity to lend this amount.",
                "lethality": "HIGH"
            })
            
        return attacks

    @classmethod
    def simulate_witness_pressure(cls, case_data: Dict, adversarial_risk: float) -> Dict:
        """
        Simulates psychological pressure on the witness during cross-examination.
        Addresses USER REQUEST 4.
        """
        risk_level = "CRITICAL" if adversarial_risk > 0.6 else ("HIGH" if adversarial_risk > 0.4 else "MODERATE")
        
        stability = 100 - (adversarial_risk * 100)
        
        return {
            "witness_stability_index": f"{int(stability)}%",
            "pressure_points": [
                "Source of funds interrogation (High stress)",
                "Chronology verification (Consistency risk)",
                "Notice demand vs. Actual debt reconciliation"
            ],
            "breakdown_risk": "VERY HIGH" if stability < 40 else ("HIGH" if stability < 60 else "LOW"),
            "fatigue_simulation": "Rapid degradation expected after 2 hours of cross-exam."
        }

    @classmethod
    def map_evidence_dependencies(cls, case_data: Dict) -> List[Dict]:
        """
        Evidence Dependency Mapping: Visualizes how one evidentiary lack affects others.
        Example: No ITR -> Financial capacity weak -> Basalingappa attack stronger -> Cross-exam survivability reduced
        """
        dependencies = []
        amount = float(case_data.get("amount") or 0)
        
        if not case_data.get("complainant_itr_available") and amount > 200000:
            dependencies.append({
                "trigger": "No ITR",
                "chain": [
                    "Financial capacity weak",
                    "Basalingappa attack stronger",
                    "Cross-exam survivability reduced"
                ],
                "impact_score": -35
            })

        if not case_data.get("debt_proven"):
            dependencies.append({
                "trigger": "No Ledger/Contract",
                "chain": [
                    "Presumption u/s 139 weakened",
                    "Security Cheque defense gains traction",
                    "Burden shifts to Complainant prematurely"
                ],
                "impact_score": -25
            })

        if case_data.get("handwriting_different"):
            dependencies.append({
                "trigger": "Handwriting Variation",
                "chain": [
                    "S.87 Material Alteration risk",
                    "FSL Examination demand likely",
                    "Trial duration extends by 18-24 months"
                ],
                "impact_score": -20
            })

        return dependencies

    @classmethod
    def detect_timeline_anomalies(cls, case_data: Dict) -> List[Dict]:
        """
        Timeline Anomaly Detector: Detects suspicious or impossible chronologies.
        Addresses Point 7 (Timeline Anomaly Detector) of the cognitive maturity audit.
        """
        anomalies = []
        from datetime import datetime
        
        def to_date(d_str):
            if not d_str: return None
            try: return datetime.strptime(d_str, "%Y-%m-%d")
            except: return None

        cheque_date = to_date(case_data.get("cheque_date"))
        dishonour_date = to_date(case_data.get("dishonour_date"))
        notice_date = to_date(case_data.get("notice_date"))
        filing_date = to_date(case_data.get("filing_date"))

        # 1. Notice before Dishonour
        if notice_date and dishonour_date and notice_date < dishonour_date:
            anomalies.append({
                "type": "IMPOSSIBLE_SEQUENCE",
                "text": "Notice date is before bank dishonour date. This is a jurisdictional fatal flaw.",
                "severity": "CRITICAL"
            })

        # 2. Filing before Notice period expiry
        if filing_date and notice_date:
            days_diff = (filing_date - notice_date).days
            if days_diff < 15:
                anomalies.append({
                    "type": "PREMATURE_CHRONOLOGY",
                    "text": f"Filing occurred only {days_diff} days after notice. S.138 requires 15 days cure period.",
                    "severity": "CRITICAL"
                })

        # 3. Post-dated Cheque Issue
        # (Assuming we have a 'loan_date')
        loan_date = to_date(case_data.get("loan_date"))
        if loan_date and cheque_date and cheque_date < loan_date:
            anomalies.append({
                "type": "SUSPICIOUS_CHRONOLOGY",
                "text": "Cheque date is prior to the alleged loan date. Causal story is inconsistent.",
                "severity": "HIGH"
            })

        return anomalies

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
