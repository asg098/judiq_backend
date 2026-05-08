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
            "rebuttal_strategy": "Verify ROC records BEFORE filing. Only implead directors active on the date of cheque issuance AND date of default."
        },
        "basalingappa_rebuttal": {
            "name": "The Financial Capacity Attack",
            "trigger": "amount > 500000 and not complainant_itr_available",
            "chain": [
                "1. Defence cross-examines on source of funds.",
                "2. Demands ITR records during cross-examination.",
                "3. Moves application for production of documents (S.91 CrPC).",
                "4. Failure to produce documents leads to adverse inference (S.114 Indian Evidence Act).",
                "5. S.139 Presumption is successfully rebutted."
            ],
            "probability_collapse": 0.65,
            "rebuttal_strategy": "Produce bank passbooks showing historical savings. Argue that S.139 presumption remains until 'probable' doubt is created by evidence, not just questions."
        },
        "vague_tracking_ghost": {
            "name": "The Service Proof Attack",
            "trigger": "not ad_card_received or not tracking_confirmed",
            "chain": [
                "1. Defence denies receipt of demand notice.",
                "2. Challenges 'Deemed Service' under S.27 GCA.",
                "3. Argues that the address was incorrect or tracking is unverified.",
                "4. If service is not proven, the entire S.138 cause of action fails."
            ],
            "probability_collapse": 0.45,
            "rebuttal_strategy": "Secure 'Postal Certificate' or 'Delivery Report' from the Post Office. Use Section 114(f) Evidence Act for presumption of delivery in the regular course of post."
        },
        "security_cheque_pivot": {
            "name": "The Security Cheque Pivot",
            "trigger": "security_cheque_defense",
            "chain": [
                "1. Defence proves the cheque was given for 'security' (e.g. via business contract).",
                "2. Argues no 'legally enforceable debt' existed on the cheque date.",
                "3. Pivots to 'Indus Airways' or 'Sampelly' landmark exceptions.",
                "4. Acquittal if debt didn't crystallize by the presentation date."
            ],
            "probability_collapse": 0.40,
            "rebuttal_strategy": "Establish that as per 'Sampelly Satyanarayana Rao', a security cheque becomes an enforceable instrument once the liability matures."
        }
    }

    @classmethod
    def simulate_attack_chains(cls, case_data: Dict, concepts: List[Dict]) -> List[Dict]:
        """
        Processes detected concepts and simulates adversarial branching.
        """
        chains = []
        concept_names = {c["concept"] for c in concepts}
        amount = float(case_data.get("amount") or 0)
        
        # 1. Check for Resignation Trap
        res_date = case_data.get("director_resignation_date")
        chq_date = case_data.get("cheque_date")
        if res_date and chq_date and res_date < chq_date:
            chains.append(cls.ATTACK_TREES["resignation_trap"])

        # 2. Check for Basalingappa Rebuttal
        if amount > 500000 and not case_data.get("complainant_itr_available"):
            chains.append(cls.ATTACK_TREES["basalingappa_rebuttal"])

        # 3. Check for Service Proof Attack
        if not case_data.get("ad_card_received"):
            chains.append(cls.ATTACK_TREES["vague_tracking_ghost"])

        # 4. Check for Security Cheque Pivot
        if "security_cheque" in concept_names:
            chains.append(cls.ATTACK_TREES["security_cheque_pivot"])

        return chains

    @classmethod
    def calculate_adversarial_risk(cls, chains: List[Dict]) -> float:
        """
        Calculates a cumulative risk factor based on the severity of attack chains.
        """
        if not chains: return 0.0
        
        # We use a compounding risk formula
        cumulative_risk = 0.0
        for chain in chains:
            risk = chain.get("probability_collapse", 0.0)
            cumulative_risk = cumulative_risk + (risk * (1.0 - cumulative_risk))
            
        return round(cumulative_risk, 2)

    @classmethod
    def map_witness_vulnerabilities(cls, case_data: Dict, concepts: List[Dict]) -> List[Dict]:
        """Maps case gaps to specific witness vulnerabilities."""
        vulnerabilities = []
        concept_names = {c["concept"] for c in concepts}
        
        if "no_debt_proof" in concept_names:
            vulnerabilities.append({
                "witness_trait": "Evidentiary Consistency",
                "attack": "Defence will suggest the debt is a fabrication or 'black money' due to lack of a written agreement.",
                "vulnerability_level": "CRITICAL"
            })
        
        if "financial_capacity_risk" in concept_names:
            vulnerabilities.append({
                "witness_trait": "Financial Transparency",
                "attack": "Complainant will be pressured to disclose personal income sources and IT compliance.",
                "vulnerability_level": "HIGH"
            })
            
        if case_data.get("handwriting_different"):
            vulnerabilities.append({
                "witness_trait": "Document Integrity",
                "attack": "Complainant will be accused of 'Material Alteration' and asked when and where the blank cheque was filled.",
                "vulnerability_level": "FATAL"
            })
            
        return vulnerabilities

adversarial_engine = AdversarialEngine()
