import logging
from typing import List, Dict, Any
from kb_manager import kb_manager

logger = logging.getLogger(__name__)

def ensure_list(x):
    if x is None: return []
    if isinstance(x, list): return x
    return [x]

def ensure_number(x, default=0):
    try: return float(x)
    except: return default

class ScoringEngineV12:
    @classmethod
    def resolve_conflicts(cls, concepts: List[Dict]) -> List[Dict]:
        """Resolve conflicting concepts - keep higher confidence one"""
        concept_names = [c["concept"] for c in concepts]
        resolved = []
        conflicts = [
            ("legally_enforceable_debt", "no_debt_proof"),
            ("legal_notice_compliance", "notice_defect"),
            ("cheque_bounce", "dishonour_disputed")
        ]
        conf_map = {c["concept"]: c["confidence"] for c in concepts}
        blacklisted = set()
        
        for pos, neg in conflicts:
            if pos in concept_names and neg in concept_names:
                if conf_map[pos] > conf_map[neg] + 0.15:
                    blacklisted.add(neg)
                elif conf_map[neg] > conf_map[pos] + 0.15:
                    blacklisted.add(pos)
                else:
                    blacklisted.add(pos)  # Conservative - keep negative
        
        for c in concepts:
            if c["concept"] not in blacklisted:
                resolved.append(c)
        
        return resolved

    @classmethod
    def calculate_score_with_trace(cls, 
                                   case_data: Dict,
                                   concepts: List[Dict],
                                   contradictions: List[Dict],
                                   evidence_assessment: Dict,
                                   raw_input: Dict = None) -> Dict:  # Added for backward compatibility
        """
        REALISTIC SCORING ENGINE - Produces varied scores based on actual case strength
        
        Scoring Philosophy:
        - Base: 15 points (realistic starting point)
        - Four Pillars: Cheque(0-28), Memo(0-15), Notice(0-32), Debt(0-28) = up to 103
        - Concept impacts: Negatives (-5 to -45), Positives (+3 to +12)
        - Quality matters: Original docs score higher than copies
        - Strong case: 75-100, Moderate: 40-74, Weak: 0-39
        
        Note: raw_input parameter is deprecated but kept for backward compatibility
        """
        concepts = cls.resolve_conflicts(ensure_list(concepts))
        trace = []
        base_score = 15
        score = base_score
        trace.append(f"Base score: {base_score}")
        
        # === FOUR PILLARS ANALYSIS (CRITICAL) ===
        cheque = bool(case_data.get('cheque_present'))
        memo = bool(case_data.get('dishonour_memo'))
        notice = bool(case_data.get('notice_sent'))
        debt = bool(case_data.get('debt_proven'))
        
        # PILLAR 1: CHEQUE (up to 28 points)
        if cheque: 
            cheque_type = case_data.get("cheque_proof_type", "original").lower()
            if cheque_type == "original":
                cheque_points = 28
                trace.append(f"+{cheque_points} original cheque secured (critical pillar)")
            elif "copy" in cheque_type or "xerox" in cheque_type:
                cheque_points = 14
                trace.append(f"+{cheque_points} photocopy cheque (reduced evidentiary value)")
            else:
                cheque_points = 20
                trace.append(f"+{cheque_points} cheque available")
            score += cheque_points
            
            # Risk Interaction: PDC + Security Claim (Expert Fix)
            if case_data.get("is_post_dated") and case_data.get("cheque_security_claim"):
                penalty = -12
                score += penalty
                trace.append(f"{penalty} HIGHER RISK: Post-Dated Cheque combined with Security Cheque claim (defense stronger)")
        else: 
            penalty = -32
            score += penalty
            trace.append(f"{penalty} NO CHEQUE - fatal defect for S.138 prosecution")
        
        # PILLAR 2: DISHONOUR MEMO (up to 15 points)
        if memo:
            memo_type = case_data.get("memo_type", "original").lower()
            if memo_type == "original":
                memo_points = 15
                trace.append(f"+{memo_points} original bank dishonour memo (strong evidence)")
            else:
                memo_points = 8
                trace.append(f"+{memo_points} memo copy available (acceptable)")
            score += memo_points
        else:
            penalty = -12
            score += penalty
            trace.append(f"{penalty} dishonour memo missing (weakens proof)")
        
        # PILLAR 3: STATUTORY NOTICE (up to 32 points) - MOST CRITICAL
        if notice:
            notice_proof = case_data.get("notice_served_proof", True)
            within_30_days = case_data.get("within_30_days", "Yes") == "Yes"
            notice_mode = case_data.get("notice_mode", "").lower()
            
            if notice_proof and within_30_days:
                if "registered" in notice_mode or "speed" in notice_mode:
                    notice_points = 32
                    trace.append(f"+{notice_points} statutory notice served via Registered/Speed Post (Strong S.138b compliance)")
                else:
                    notice_points = 26
                    trace.append(f"+{notice_points} statutory notice served within 30 days (Proof available)")
            elif notice_proof:
                notice_points = 22
                trace.append(f"+{notice_points} notice served with proof (timeline unclear)")
            elif within_30_days:
                notice_points = 15
                trace.append(f"+{notice_points} notice sent within 30 days (service proof weak)")
            else:
                notice_points = 10
                trace.append(f"+{notice_points} notice sent (service proof and timing unclear)")
            score += notice_points
        else:
            penalty = -45
            score += penalty
            trace.append(f"{penalty} STATUTORY NOTICE NOT SENT - FATAL PROCEDURAL DEFECT (S.138b mandatory)")
        
        # PILLAR 4: DEBT PROOF (up to 28 points)
        if debt:
            proof_method = case_data.get("debt_proof_type", "written_agreement").lower()
            if proof_method in ["loan_agreement", "written_agreement", "promissory_note"]:
                debt_points = 28
                trace.append(f"+{debt_points} strong written debt proof ({proof_method})")
            elif proof_method == "invoice":
                debt_points = 20
                trace.append(f"+{debt_points} invoice-based debt proof (acceptable)")
            elif proof_method == "verbal":
                debt_points = 6
                trace.append(f"+{debt_points} verbal debt claim only (very weak)")
            else:
                debt_points = 16
                trace.append(f"+{debt_points} debt documented ({proof_method})")
            score += debt_points
        else:
            penalty = -38
            score += penalty
            trace.append(f"{penalty} NO DEBT PROOF - S.139 presumption significantly weakened")
        
        # === SECTION 141 & 142 COMPLIANCE (Expert Audit Fix) ===
        # Accused Corporate Check (Section 141 Vicarious Liability)
        accused_name = str(case_data.get("accused_name", "")).lower()
        is_company = any(x in accused_name for x in ["pvt", "ltd", "corp", "inc", "co.", "company"])
        
        if is_company:
            has_directors = bool(case_data.get("directors_named", False))
            if not has_directors:
                penalty = -45
                score += penalty
                trace.append(f"{penalty} FATAL DEFECT: Section 141 Vicarious Liability (Directors not named for corporate accused)")
            else:
                trace.append("✅ Section 141 Compliance: Directors/Authorized Officers named")

        # Complainant Corporate Check (Section 142 Competency to File)
        complainant_type = case_data.get("complainant_type", "Individual")
        if complainant_type != "Individual":
            is_authorized = bool(case_data.get("is_authorized", False))
            if not is_authorized:
                penalty = -30
                score += penalty
                trace.append(f"{penalty} STRUCTURAL DEFECT: Lack of Authorization/Board Resolution (Complainant competency)")
            else:
                trace.append("✅ Complainant Competency: Authorization/Board Resolution provided")

        # === CORROBORATIVE EVIDENCE WEIGHTAGE ===
        pillars_satisfied = sum([cheque, memo, notice, debt])
        if pillars_satisfied == 4:
            weightage = 10
            score += weightage
            trace.append(f"+{weightage} all mandatory procedural pillars satisfied (corroborative weightage)")
        elif pillars_satisfied <= 2:
            penalty = -8
            score += penalty
            trace.append(f"{penalty} multiple mandatory procedural pillars missing (compounding weakness)")
        
        # === CONCEPT-BASED ADJUSTMENTS ===
        catalogue = kb_manager.get_scoring_catalogue()
        score_breakdown = []
        
        positive_concepts = {
            "legally_enforceable_debt": 8,
            "legal_notice_compliance": 6,
            "strong_documentary_evidence": 7,
            "cheque_bounce": 5
        }
        
        for concept_det in concepts:
            concept = concept_det.get("concept", "unknown")
            confidence = ensure_number(concept_det.get("confidence", 0))
            
            if confidence < 0.2:
                continue
            
            # Handle positive concepts
            if concept in positive_concepts:
                max_boost = positive_concepts[concept]
                boost = int(confidence * max_boost)
                score += boost
                trace.append(f"+{boost} {concept.replace('_', ' ')} reinforcement")
                score_breakdown.append(f"{concept} (+{boost})")
                continue
            
            # Handle negative concepts
            lookup_concept = concept
            if lookup_concept not in catalogue:
                alias_map = {
                    "signature_disputed": "signature_dispute",
                    "notice_not_sent": "notice_defect",
                    "no_debt_proof": "no_debt_proof",
                    "cheque_misuse": "cheque_misuse"
                }
                lookup_concept = alias_map.get(concept, concept)
                if lookup_concept not in catalogue:
                    continue
            
            base_penalty, legal_weight, _ = catalogue[lookup_concept]
            
            # 🔥 CRITICAL FIX: Massive penalty for high-confidence negative signals
            # If we are >70% sure of a "case-killer" like forged signature, tank the score.
            if confidence >= 0.7:
                penalty_factor = 2.5  # Doubled impact
            elif confidence >= 0.4:
                penalty_factor = 1.5
            else:
                penalty_factor = 0.8
            
            scaled_penalty = int(confidence * legal_weight * base_penalty * penalty_factor)
            
            # Extra penalty for specific fatal flaws
            fatal_flaws = ["signature_dispute", "signature_disputed", "cheque_misuse", "notice_defect", "no_debt_proof"]
            if lookup_concept in fatal_flaws and confidence > 0.6:
                scaled_penalty -= 25 # Explicit flat penalty for fatal flaws
                trace.append(f"⚠️ FATAL LEGAL DEFECT: {concept.replace('_', ' ')}")

            score += scaled_penalty
            trace.append(f"{scaled_penalty:+d} {concept.replace('_', ' ')} risk (conf: {confidence:.0%})")
            score_breakdown.append(f"{concept} ({scaled_penalty})")
        
        # === EVIDENCE QUALITY ADJUSTMENTS ===
        evidence_strength = evidence_assessment.get("strength", "MODERATE")
        if evidence_strength == "STRONG":
            bonus = 5
            score += bonus
            trace.append(f"+{bonus} strong evidence quality bonus")
        elif evidence_strength == "WEAK":
            penalty = -5
            score += penalty
            trace.append(f"{penalty} weak evidence quality penalty")
        
        # === FINAL BOUNDARIES & STRICT STATUTORY GATES (Expert Force-Fix) ===
        # REFINEMENT: No case is 100% perfect. Max score is 91 to account for judicial discretion and litigation risk.
        
        # Apply standard litigation friction (the 9% uncertainty)
        score -= 9
        trace.append("-9 Standard Litigation Friction (Inherent risk of trial, judicial discretion, and procedural delays)")
        
        score = max(0, min(score, 91))

        # 🔥 HARD GATE: STATUTORY OVERRIDE
        # If mandatory pillars are missing, the case is non-maintainable in court.
        if not cheque:
            score = min(score, 5)
            trace.append("⚖️ STATUTORY OVERRIDE: FATAL - No cheque instrument. Case non-maintainable.")
        elif not notice:
            score = min(score, 15)
            trace.append("⚖️ STATUTORY OVERRIDE: FATAL - No demand notice. Jurisdictional bar active.")
        elif is_company and not has_directors:
            score = min(score, 25)
            trace.append("⚖️ STATUTORY OVERRIDE: CRITICAL - S.141 defect (Corporate liability). High dismissal risk.")
        
        # FINAL CAP
        score = max(0, min(score, 91))
        
        # === JUDICIAL DISCRETION MODE (Expert Fix) ===
        discretion_notes = []
        if any("Limitation" in str(t) for t in trace):
            discretion_notes.append("Limitation Bar: While mathematically expired, courts may condone delay under Section 5 of the Limitation Act if 'sufficient cause' is proven.")
        if any("Section 141" in str(t) for t in trace):
            discretion_notes.append("Corporate Liability: Technical defects in naming directors can sometimes be cured through an amendment application (S.147/S.482).")

        return {
            "final_score": score,
            "reasoning_trace": trace,
            "score_breakdown": score_breakdown or ["Standard scoring applied"],
            "discretionary_caveats": discretion_notes
        }
