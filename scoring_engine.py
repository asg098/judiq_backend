from datetime import datetime
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
        Includes Procedural, Evidentiary, and Strategic breakdown with Explicit Causality.
        """
        concepts = cls.resolve_conflicts(ensure_list(concepts))
        trace = []
        causality_map = [] 
        base_score = 15
        score = base_score
        trace.append(f"Base score: {base_score} (Standard Litigation Baseline)")
        causality_map.append({"fact": "Litigation Baseline", "impact": base_score, "type": "neutral", "rationale": "Base probability of recovery in Indian courts."})
        
        amount = ensure_number(case_data.get("amount", 0))
        
        # 1. PILLARS & COMPLIANCE SCORECARD
        cheque = bool(case_data.get('cheque_present'))
        memo = bool(case_data.get('dishonour_memo'))
        notice = bool(case_data.get('notice_sent'))
        debt = bool(case_data.get('debt_proven'))
        
        # PILLAR 1: CHEQUE
        if cheque: 
            cheque_type = case_data.get("cheque_proof_type", "original").lower()
            cheque_points = 22 if cheque_type == "original" else 15
            score += cheque_points
            trace.append(f"+{cheque_points} Cheque available ({cheque_type})")
            causality_map.append({"fact": f"Cheque ({cheque_type})", "impact": cheque_points, "type": "positive", "rationale": "Possession of original instrument is 70% of the battle."})
        else:
            score -= 40
            trace.append("-40 FATAL: Original cheque missing")
            causality_map.append({"fact": "Missing Original Cheque", "impact": -40, "type": "negative", "rationale": "S.138 requires the instrument. Photocopies are rarely admissible without S.65B."})

        # PILLAR 2: DISHONOUR MEMO
        if memo:
            memo_points = 12
            score += memo_points
            trace.append(f"+{memo_points} Bank dishonour memo secured")
            causality_map.append({"fact": "Bank Memo Presence", "impact": memo_points, "type": "positive", "rationale": "Formal proof of dishonour by the banking institution."})
        else:
            score -= 20
            trace.append("-20 CRITICAL: Bank memo missing")
            causality_map.append({"fact": "Missing Bank Memo", "impact": -20, "type": "negative", "rationale": "Magistrate cannot take cognizance without a return memo/debit advice."})

        # PILLAR 3: STATUTORY NOTICE
        if notice:
            within_30 = case_data.get("within_30_days", "Yes") == "Yes"
            notice_points = 25 if within_30 else 5
            score += notice_points
            trace.append(f"+{notice_points} Statutory demand notice served")
            causality_map.append({"fact": "S.138(b) Notice Compliance", "impact": notice_points, "type": "positive", "rationale": "Statutory notice window adhered to. Cause of action established."})
            if not within_30:
                causality_map.append({"fact": "Notice Delay", "impact": -15, "type": "negative", "rationale": "Notice sent beyond 30 days of dishonour. Requires condonation application."})
        else:
            score -= 50
            trace.append("-50 FATAL: Statutory notice NOT SENT")
            causality_map.append({"fact": "Notice Not Sent", "impact": -50, "type": "negative", "rationale": "Mandatory requirement. Complaint is non-maintainable without S.138 notice."})

        # PILLAR 4: DEBT
        compliance_pct = (sum([1 for p in [cheque, memo, notice, debt] if p]) / 4.0) * 100
        if debt:
            debt_points = 20
            if amount > 100000 and not case_data.get("agreement_registered"):
                debt_points -= 10
                trace.append("-10 RISK: High-value agreement not registered.")
                causality_map.append({"fact": "Unregistered Agreement", "penalty": -10, "rationale": "Weakens secondary evidence claims."})
            score += debt_points
            trace.append(f"+{debt_points} Debt/Liability established")
            causality_map.append({"fact": "Debt Liability Proof", "impact": debt_points, "type": "positive", "rationale": "S.139 requires a legally enforceable debt."})
        else:
            score -= 20
            trace.append("-20 Presumption u/s 139 weakened (No debt proof)")
            causality_map.append({"fact": "No Liability Proof", "penalty": -20, "rationale": "S.139 presumption is rebuttable."})

        # EXPERT AUDITS
        accused_name = str(case_data.get("accused_name", "")).lower()
        is_company = any(x in accused_name for x in ["pvt", "ltd", "corp", "inc", "co.", "company"])
        if is_company:
            if not case_data.get("directors_named"):
                score -= 40
                trace.append("-40 FATAL: S.141 defect - Directors not named.")
                causality_map.append({"fact": "S.141 Defect", "penalty": -40, "rationale": "Company prosecution fails without naming responsible officers."})
            
            resignation_date = case_data.get("director_resignation_date")
            cheque_date = case_data.get("cheque_date")
            if resignation_date and cheque_date:
                try:
                    res_dt = datetime.fromisoformat(resignation_date) if isinstance(resignation_date, str) else resignation_date
                    chq_dt = datetime.fromisoformat(cheque_date) if isinstance(cheque_date, str) else cheque_date
                    if res_dt < chq_dt:
                        score -= 50
                        trace.append("-50 FATAL: Vicarious Liability Gap (Resignation).")
                        causality_map.append({"fact": "Director Resignation", "penalty": -50, "rationale": "Director resigned BEFORE instrument issuance. High Malicious Prosecution risk."})
                except: pass

        # Basalingappa & Sushil Kumar Check
        if amount > 2000000 and not case_data.get("loan_via_bank") and not case_data.get("complainant_itr_available"):
            score -= 60
            trace.append("-60 FATAL EVIDENTIARY GAP: ₹20L+ cash loan without ITR.")
            causality_map.append({"fact": "Basalingappa Fatal", "penalty": -60, "rationale": "High-value cash loans without source proof are fatal."})
        elif amount > 500000 and not case_data.get("loan_via_bank") and not case_data.get("complainant_itr_available"):
            score -= 45
            trace.append("-45 REBUTTAL RISK: High-value cash loan without ITR.")
            causality_map.append({"fact": "Basalingappa High Risk", "penalty": -45, "rationale": "Lending capacity is a standard defence attack."})

        # Limitation & Notice Defects
        existing_concepts = [c["concept"] for c in concepts]
        if "limitation_issue" in existing_concepts:
            score -= 30
            trace.append("-30 CRITICAL: Limitation Period delay (S.142 violation)")
            causality_map.append({"fact": "Limitation Delay", "penalty": -30, "rationale": "S.142 is a jurisdictional bar."})
        
        if "notice_defect" in existing_concepts:
            score -= 25
            trace.append("-25 CRITICAL: Defective statutory notice")
            causality_map.append({"fact": "Notice Defect", "penalty": -25, "rationale": "Statutory notice must be perfect."})

        # Signature & Alteration
        if case_data.get("handwriting_different") or "material_alteration" in existing_concepts:
            score -= 40
            trace.append("-40 FATAL: Material Alteration Trap (S.87).")
            causality_map.append({"fact": "Material Alteration", "penalty": -40, "impact": -40, "rationale": "Different inks/handwriting voids the instrument."})

        # Final Score Cap
        final_score = max(0, min(99, score))
        if not cheque or not notice:
            final_score = min(final_score, 30)
            trace.append("! SCORE CAPPED: Fatal statutory defect identified.")

        # Readiness Score
        cri_components = []
        if cheque: cri_components.append(25)
        if memo: cri_components.append(15)
        if notice: cri_components.append(15)
        if debt: cri_components.append(20)
        if case_data.get("is_authorized"): cri_components.append(15)
        cri_final = max(0, min(100, sum(cri_components)))

        # ── EXPLICIT CAUSALITY: Score Delta & Penalty Index ──────────────────
        potential_score = 99
        causality_delta = []
        for item in causality_map:
            val = item.get("penalty") or item.get("impact") or 0
            causality_delta.append({
                "factor": item["fact"],
                "impact": val,
                "reasoning": item["rationale"]
            })

        # ── EXPLICIT CAUSALITY: Factor-Level Scoring ────────────────────────
        explicit_penalties = []
        for item in causality_map:
            explicit_penalties.append(f"{item['penalty']} because {item['fact']}")

        # ── EXPLICIT RISK PROPAGATION: Visible Causal Weights ───────────────
        explicit_risk_propagation = []
        for item in causality_map:
            weight_str = f"{item['penalty']} because {item['fact']}"
            explicit_risk_propagation.append(weight_str)

        return {
            "score": int(final_score),
            "final_score": int(final_score),
            "potential_score": potential_score,
            "causality_delta": causality_delta,
            "explicit_risk_propagation": explicit_risk_propagation, # THE REQUESTED FORMAT
            "compliance_pct": int(compliance_pct),
            "cri_score": int(cri_final),
            "causality_map": causality_map,
            "top_penalties": sorted(causality_delta, key=lambda x: x["impact"])[:3],
            "breakdown": {
                "procedural": int(max(0, min(100, (sum([1 for p in [cheque, memo, notice] if p])/3.0)*100))),
                "evidentiary": int(max(0, min(100, score))),
                "strategic": int(max(0, min(100, final_score))),
                "readiness": int(cri_final)
            },
            "reasoning_trace": trace,
            "score_breakdown": trace,
            "discretionary_caveats": [
                "JUDICIAL DISCRETION CAVEAT: Magistrates may exercise discretion if bad faith by the accused is evident."
            ]
        }
