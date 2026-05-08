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
    def map_witness_vulnerabilities(cls, case_data: Dict, concepts: List[Dict]) -> List[Dict]:
        vulnerabilities = []
        concept_names = {c["concept"] for c in concepts}
        
        if "no_debt_proof" in concept_names:
            vulnerabilities.append({
                "witness_trait": "Evidentiary Consistency",
                "attack": "Defence will suggest the debt is a fabrication due to lack of a written agreement.",
                "collapse_scenario": "Witness fumbles during cross-examination when asked about the exact time/place of handing over cash.",
                "vulnerability_level": "CRITICAL"
            })
        
        if "financial_capacity_risk" in concept_names:
            vulnerabilities.append({
                "witness_trait": "Financial Transparency",
                "attack": "Complainant pressured on ITR compliance.",
                "collapse_scenario": "Inability to explain the 'source of funds' leads to judicial skepticism of the entire transaction.",
                "vulnerability_level": "HIGH"
            })
            
        return vulnerabilities

    @classmethod
    def simulate_contradiction_escalation(cls, case_data: Dict, concepts: List[Dict]) -> List[Dict]:
        """Tracks how a single evidentiary gap cascades into multiple legal failures."""
        escalations = []
        concept_names = {c["concept"] for c in concepts}
        
        if "financial_capacity_risk" in concept_names:
            escalations.append({
                "trigger_gap": "Missing ITR / Source of Funds",
                "cascade": [
                    "Step 1: Rebuttal of S.139 Presumption (Basalingappa).",
                    "Step 2: Admission of 'Unaccounted Cash' transaction.",
                    "Step 3: Invalidity of 'Legally Enforceable Debt' (S.138 NI Act).",
                    "Step 4: High probability of acquittal on merits."
                ]
            })
            
        if "material_alteration" in concept_names or case_data.get("handwriting_different"):
            escalations.append({
                "trigger_gap": "Handwriting Mismatch / Different Inks",
                "cascade": [
                    "Step 1: Challenge u/s 87 NI Act (Material Alteration).",
                    "Step 2: Expert testimony (S.45 IEA) creates 'Probable Doubt'.",
                    "Step 3: Voiding of the instrument entirely.",
                    "Step 4: Immediate Quashing / Acquittal."
                ]
            })
            
        return escalations

    @classmethod
    def estimate_quashing_probability(cls, case_data: Dict) -> float:
        """Estimates probability of case being quashed u/s 482 CrPC."""
        prob = 0.0
        if case_data.get("director_resignation_date") and case_data.get("cheque_date"):
            if case_data.get("director_resignation_date") < case_data.get("cheque_date"):
                prob = max(prob, 0.95) # Near certainty for resigned directors
        if case_data.get("notice_sent") is False:
            prob = max(prob, 0.98) # Fatal procedural bar
        return prob

    @classmethod
    def generate_acquittal_tree(cls, chain: Dict) -> Dict:
        """Generates a decision tree leading to acquittal."""
        return {
            "root_vulnerability": chain["name"],
            "acquittal_nodes": [
                {"event": "Defence raises 'probable doubt'", "impact": "Burden shifts to Complainant"},
                {"event": "Complainant fails to produce documentary evidence", "impact": "Adverse Inference drawn"},
                {"event": "Court concludes 'Legally Enforceable Debt' not proven", "impact": "ACQUITTAL"}
            ]
        }

    @classmethod
    def simulate_courtroom_battle(cls, case_data: Dict, concepts: List[Dict]) -> List[Dict]:
        """Simulates deep, fatal courtroom attack/rebuttal trees with Quashing Probability."""
        battle_nodes = []
        chains = cls.simulate_attack_chains(case_data, concepts)
        quashing_prob = cls.estimate_quashing_probability(case_data)
        
        for chain in chains:
            node = {
                "attack_vector": chain["name"],
                "fatal_pathway": cls.generate_acquittal_tree(chain),
                "witness_box_collapse": {
                    "trigger_question": chain["chain"][0] if chain.get("chain") else "Standard cross-exam question",
                    "likely_fumble": "Witness provides inconsistent dates/amounts under pressure.",
                    "contradiction_escalation": "Defence moves application to summon bank records to disprove the witness."
                },
                "destruction_probability": f"{int(chain.get('probability_collapse', 0) * 100)}%",
                "quashing_probability": f"{int(quashing_prob * 100)}%" if quashing_prob > 0.5 else "Low",
                "malicious_prosecution_exposure": "EXTREME" if "resignation" in chain["name"].lower() else "Standard",
                "rebuttal_tree": {
                    "primary_rebuttal": chain.get("rebuttal_strategy", "Rely on S.139."),
                    "secondary_rebuttal": "Produce corroborative oral testimony.",
                    "failure_outcome": "ACQUITTAL"
                }
            }
            battle_nodes.append(node)
        
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

    @classmethod
    def prune_accused(cls, case_data: Dict) -> List[Dict]:
        """Identifies impleaded parties who should be 'pruned' to avoid malicious prosecution risk."""
        pruning = []
        if case_data.get("director_resignation_date") and case_data.get("cheque_date"):
            if case_data.get("director_resignation_date") < case_data.get("cheque_date"):
                pruning.append({
                    "party": "Resigned Director",
                    "reason": "Liability ceased upon resignation before instrument issuance.",
                    "risk": "High - Malicious Prosecution suit risk."
                })
        return pruning

adversarial_engine = AdversarialEngine()
