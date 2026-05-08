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
                                   raw_input: Dict = None) -> Dict:
        """
        REALISTIC SCORING ENGINE - Produces varied scores based on actual case strength
        Includes Procedural, Evidentiary, and Strategic breakdown.
        """
        concepts = cls.resolve_conflicts(ensure_list(concepts))
        trace = []
        base_score = 15
        score = base_score
        trace.append(f"Base score: {base_score} (Standard Litigation Baseline)")
        
        # 1. PILLARS & COMPLIANCE SCORECARD
        cheque = bool(case_data.get('cheque_present'))
        memo = bool(case_data.get('dishonour_memo'))
        notice = bool(case_data.get('notice_sent'))
        debt = bool(case_data.get('debt_proven'))
        
        pillars_count = sum([1 for p in [cheque, memo, notice, debt] if p])
        compliance_pct = (pillars_count / 4.0) * 100
        
        # PILLAR 1: CHEQUE (up to 28 points)
        if cheque: 
            cheque_type = case_data.get("cheque_proof_type", "original").lower()
            cheque_points = 22 if cheque_type == "original" else 15
            score += cheque_points
            trace.append(f"+{cheque_points} Cheque available ({cheque_type})")
        else:
            score -= 35
            trace.append("-35 FATAL: Original cheque missing")

        # PILLAR 2: DISHONOUR MEMO (up to 15 points)
        if memo:
            memo_points = 12
            score += memo_points
            trace.append(f"+{memo_points} Bank dishonour memo secured")
        else:
            score -= 15
            trace.append("-15 CRITICAL: Bank memo missing")

        # PILLAR 3: STATUTORY NOTICE (up to 32 points)
        if notice:
            within_30 = case_data.get("within_30_days", "Yes") == "Yes"
            notice_points = 28 if within_30 else 10
            score += notice_points
            trace.append(f"+{notice_points} Statutory notice compliance")
        else:
            score -= 45
            trace.append("-45 FATAL: No demand notice sent (S.138b violation)")

        # PILLAR 4: DEBT PROOF (up to 25 points)
        if debt:
            debt_points = 22
            
            # Stamping & Registration Trap
            if not case_data.get("agreement_stamped"):
                debt_points -= 15
                trace.append("-15 EVIDENTIARY DEFECT: Loan agreement NOT properly stamped. Inadmissible under Indian Stamp Act until impounded.")
            if not case_data.get("agreement_registered") and amount > 1000000:
                debt_points -= 10
                trace.append("-10 RISK: High-value agreement not registered. Weakens secondary evidence claims.")
                
            score += debt_points
            trace.append(f"+{debt_points} Debt/Liability established")
        else:
            score -= 20
            trace.append("-20 Presumption u/s 139 weakened (No debt proof)")

        # EXPERT AUDITS (Corporate & Financial Capacity)
        accused_name = str(case_data.get("accused_name", "")).lower()
        is_company = any(x in accused_name for x in ["pvt", "ltd", "corp", "inc", "co.", "company"])
        if is_company:
            if not case_data.get("directors_named"):
                score -= 40
                trace.append("-40 FATAL: S.141 defect - Directors not named with exact roles for corporate accused (Aneeta Hada rule)")
            
            # Resignation Trap
            cheque_date = case_data.get("cheque_date")
            resignation_date = case_data.get("director_resignation_date")
            if resignation_date and cheque_date:
                try:
                    res_dt = datetime.fromisoformat(resignation_date) if isinstance(resignation_date, str) else resignation_date
                    chq_dt = datetime.fromisoformat(cheque_date) if isinstance(cheque_date, str) else cheque_date
                    if res_dt < chq_dt:
                        score -= 50
                        trace.append("-50 FATAL: Vicarious Liability Gap. Director resigned BEFORE the cheque was issued. Impleading them is 'Malicious Prosecution' and leads to quashing.")
                except:
                    pass

        # Authorization Trap (A.C. Narayanan)
        complainant_type = case_data.get("complainant_type", "Individual")
        if complainant_type != "Individual":
            is_authorized = case_data.get("is_authorized", False)
            if not is_authorized:
                score -= 40
                trace.append("-40 FATAL: Authorization Trap. Missing Board Resolution naming the specific signer BEFORE notice date (A.C. Narayanan)")

        # Basalingappa & Sushil Kumar (2026) Check
        amount = ensure_number(case_data.get("amount", 0))
        if amount > 2000000 and not case_data.get("loan_via_bank") and not case_data.get("complainant_itr_available"):
            score -= 60
            trace.append("-60 FATAL EVIDENTIARY GAP: Very high-value cash loan (₹20 Lakhs+) without ITR records. Prosecution is doomed under the Basalingappa doctrine.")
        elif amount > 500000 and not case_data.get("loan_via_bank") and not case_data.get("complainant_itr_available"):
            score -= 45
            trace.append("-45 REBUTTAL RISK: High-value cash loan (₹5 Lakhs+) without ITR/Source proof (Sushil Kumar v. Sandeep Kumar, 2026)")
        elif amount > 150000 and not case_data.get("loan_via_bank") and not case_data.get("complainant_itr_available"):
            score -= 30
            trace.append("-30 REBUTTAL RISK: High-value cash loan without ITR proof (Basalingappa rule)")

        # Signature Mismatch Trap
        dishonour_reason = case_data.get("dishonour_reason", "").lower()
        if "signature" in dishonour_reason and "mismatch" in dishonour_reason:
            score -= 15
            trace.append("-15 EVIDENTIARY TRAP: Signature Mismatch shifts burden. Requires Handwriting Expert.")

        # Procedural Fragility: Email Notice
        notice_mode = case_data.get("notice_mode", "rpad").lower()
        if "email" in notice_mode and "rpad" not in notice_mode:
            score -= 20
            trace.append("-20 PROCEDURAL RISK: Notice via Email lacks delivery proof of RPAD and requires S.63 BSA Certificate.")

        # 3. BREAKDOWN CALCULATION
        existing_concepts = [c["concept"] for c in concepts]
        
        # ── ENEMY TACTICS KILL-SWITCH (Hardening) ──────────────────────────
        if "limitation_issue" in existing_concepts:
            score -= 30
            trace.append("-30 CRITICAL: Limitation Period delay detected (S.142 violation)")
        
        if "notice_defect" in existing_concepts:
            score -= 25
            trace.append("-25 CRITICAL: Defective statutory notice")

        if case_data.get("handwriting_different") or "material_alteration" in existing_concepts:
            score -= 40
            trace.append("-40 FATAL: Material Alteration Trap (S.87). Different handwriting/inks voids the instrument.")

        if "defective_goods" in existing_concepts:
            score -= 20
            trace.append("-20 RISK: 'Civil Dispute' Camouflage. Disputed amount can invalidate the entire notice.")

        # Notice of Service Ghost
        if case_data.get("notice_sent") and not case_data.get("ad_card_received"):
            score -= 15
            trace.append("-15 RISK: 'Notice of Service Ghost'. Missing AD Card signature or vague tracking report.")

        # Procedural Score: Pillars + Limitation
        pro_score = (sum([1 for p in [cheque, memo, notice] if p]) / 3.0) * 100
        if "notice_defect" in existing_concepts or "limitation_issue" in existing_concepts:
            pro_score *= 0.35 # Even harsher penalty
        
        # Evidentiary Score: Debt + Proof presence
        evi_score = (90 if debt else 30)
        if not case_data.get("proof_present", True): evi_score -= 20
        if case_data.get("communication_records"): evi_score += 10
        
        # Final Score Cap
        final_score = max(0, min(99, score))
        
        # FATAL CAP: If original cheque or notice is missing, score cannot exceed 30
        if not cheque or not notice:
            final_score = min(final_score, 30)
            trace.append("! SCORE CAPPED: Fatal statutory defect identified.")

        # Strategic Score: Derived from final strength
        strat_score = final_score

        # ── COURTROOM READINESS INDEX (CRI) ───────────────────────────
        # A measure of 'Trial Readiness' beyond just legal compliance.
        cri_components = []
        if cheque: cri_components.append(25) # Original doc
        if memo: cri_components.append(15)   # Official record
        if notice: cri_components.append(15) # Procedural compliance
        if debt: cri_components.append(20)   # Evidence strength
        if case_data.get("communication_records"): cri_components.append(10) # Corroboration
        if case_data.get("is_authorized"): cri_components.append(15) # Authorization
        
        cri_score = sum(cri_components)
        if "limitation_issue" in existing_concepts: cri_score -= 20
        if "notice_defect" in existing_concepts: cri_score -= 15
        
        cri_final = max(0, min(100, cri_score))

        return {
            "score": int(final_score),
            "final_score": int(final_score), # Compatibility
            "compliance_pct": int(compliance_pct),
            "cri_score": int(cri_final),
            "breakdown": {
                "procedural": int(max(0, min(100, pro_score))),
                "evidentiary": int(max(0, min(100, evi_score))),
                "strategic": int(max(0, min(100, strat_score))),
                "readiness": int(cri_final)
            },
            "reasoning_trace": trace,
            "score_breakdown": trace, # Compatibility
            "limitation": case_data.get("limitation", {}),
            "discretionary_caveats": [
                "JUDICIAL DISCRETION CAVEAT: While this AI employs 'Cynical Advocate' logic, do not entirely abandon a 'Moderate' case. A sympathetic Magistrate may exercise judicial discretion and overlook minor technical defects if glaring financial fraud or bad faith by the accused is evident."
            ]
        }
