import re
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def ensure_list(x):
    if x is None: return []
    if isinstance(x, list): return x
    return [x]

NEGATIVE_CONCEPTS = {
    "signature_dispute", "notice_defect", "no_debt_proof", "security_cheque",
    "cheque_misuse", "limitation_issue", "payment_already_made", "dishonour_disputed",
    "cheque_validity_issue", "no_agreement", "joint_account_liability",
    "stop_payment_instructions", "material_alteration", "premature_complaint",
    "unaccounted_cash_loans", "legal_heirs_liability", "litigation_risk"
}

POSITIVE_CONCEPTS = {
    "cheque_bounce", "legal_notice_compliance", "legally_enforceable_debt",
    "strong_documentary_evidence", "partnership_and_firms",
    "power_of_attorney_holder", "interim_compensation", "appeal_deposit",
    "compounding_offence"
}

WEAKNESS_THRESHOLD = 0.22
STRENGTH_THRESHOLD = 0.45

def _convert_to_lawyer_language(raw_trace: list) -> list:
    _PHRASE_MAP = [
        (r"\+\d+\s+instrument\s+present", "The foundational Negotiable Instrument (S.138) is present and verified."),
        (r"\+\d+\s+cheque", "Possession of the original cheque instrument establishes the prima facie cause of action."),
        (r"-\d+\s+instrument\s+missing", "FATAL: Absence of the physical cheque instrument precludes prosecution under S.138 NI Act."),
        (r"\+\d+\s+memo\s+available", "Official Bank Dishonour Memo/Return Slip provides conclusive evidence of non-payment."),
        (r"\+\d+\s+notice\s+compliance", "Service of Statutory Demand Notice (S.138b) is confirmed within the 30-day window."),
        (r"-\d+\s+notice\s+defect", "PROCEDURAL BAR: Failure to serve mandatory statutory notice within 30 days is a jurisdictional defect."),
        (r"\+\d+\s+debt\s+provenance", "Underlying legally enforceable debt is corroborated via documentary evidence."),
        (r"-\d+\s+debt\s+not\s+established", "Evidentiary Risk: Lack of underlying debt documentation weakens the S.139 presumption."),
        (r"\+\d+\s+all\s+mandatory\s+procedural\s+pillars", "Statutory Audit: All four mandatory pillars (Instrument, Dishonour, Notice, Debt) are satisfied."),
        (r"-\d+\s+notice\s+defect\s+\(fatal\)", "FATAL: Jurisdictional defect in statutory notice service renders complaint non-maintainable."),
        (r"OVERRIDE:\s+FATAL", "AUTHORITATIVE OVERRIDE: The case suffers from a fatal statutory defect that precludes legal success."),
        (r"BASALINGAPPA\s+PENALTY", "EVIDENTIARY GAP: High-value debt based solely on verbal testimony is highly vulnerable to 'Financial Capacity' rebuttals (Basalingappa v. Mudibasappa)."),
        (r"FATAL\s+ERROR:\s+PREMATURE", "FATAL PROCEDURAL ERROR: Premature filing before the expiry of the 15-day cure period (Yogendra Pratap Singh v. Savitri Pandey)."),
    ]

    clean_trace = []
    seen = set()
    for item in raw_trace:
        matched = False
        for pattern, substitution in _PHRASE_MAP:
            if re.search(pattern, str(item), re.IGNORECASE):
                if substitution not in seen:
                    clean_trace.append(substitution)
                    seen.add(substitution)
                matched = True
                break
        if not matched:
            cleaned = re.sub(r"^[+-]\d+\s+", "", str(item)).strip()
            if cleaned and not cleaned.startswith("Base score") and not cleaned.startswith("Final score") and not cleaned.startswith("Applied") and cleaned not in seen:
                clean_trace.append(cleaned)
                seen.add(cleaned)
    return clean_trace


class ResponseBuilder:
    @staticmethod
    def build_final_response(engine_result: Dict[str, Any], case_data: Dict[str, Any]) -> Dict[str, Any]:
        score = engine_result.get("final_score", 0)
        trace = engine_result.get("reasoning_trace", [])
        breakdown = engine_result.get("score_breakdown", [])
        concepts = engine_result.get("concepts", [])

        verdict = "STRONG CASE"
        if score < 40: verdict = "WEAK CASE / HIGH RISK"
        elif score < 70: verdict = "MODERATE CASE"

        risk_level = "LOW"
        if score < 50: risk_level = "CRITICAL"
        elif score < 75: risk_level = "MEDIUM"

        strengths = []
        weaknesses = []

        if case_data.get("cheque_present"):   strengths.append("Prerequisite: Negotiable instrument (cheque) secured")
        if case_data.get("dishonour_memo"):   strengths.append("Prerequisite: Bank dishonour memo / return slip available")
        if case_data.get("notice_sent"):      strengths.append("Prerequisite: Statutory demand notice served (S.138b)")
        if case_data.get("debt_proven"):      strengths.append("Strength: Legally enforceable debt established via corroborative proof")

        for c in concepts:
            concept_name = c.get("concept", "")
            conf = c.get("confidence", 0)
            label = concept_name.replace('_', ' ').title()

            if concept_name in NEGATIVE_CONCEPTS and conf >= WEAKNESS_THRESHOLD:
                severity = "CRITICAL" if conf >= 0.65 else ("HIGH" if conf >= 0.45 else "MEDIUM")
                weaknesses.append(f"{label} [{severity} — conf: {conf:.0%}]")

            elif concept_name in POSITIVE_CONCEPTS and conf >= STRENGTH_THRESHOLD:
                strengths.append(f"{label} detected (conf: {conf:.0%})")

        # ── EVIDENTIARY HARDENING (Advocate Grade) ──────────────────────────
        desc_lower = (case_data.get("description") or "").lower()
        if any(x in desc_lower for x in ["whatsapp", "email", "sms", "digital", "screenshot"]):
             weaknesses.append("Mandatory Admissibility Barrier [CRITICAL]: Missing Section 65B Certificate for digital evidence.")
        
        limitation = engine_result.get("limitation", {})
        if limitation.get("is_premature"):
            weaknesses.append("FATAL PROCEDURAL DEFECT [CRITICAL]: Complaint is Premature. Non-curable defect under NI Act.")
        elif limitation.get("notice_delay_days", 0) > 0:
             weaknesses.append(f"Jurisdictional Bar [HIGH]: Statutory notice delayed by {limitation['notice_delay_days']} days. Application for condonation mandatory.")
        
        if not case_data.get("proof_present", True):
             weaknesses.append("EVIDENTIARY GAP [HIGH]: Proof (Cheque/Memo/Notice) is missing. Results are indicative only.")

        # ── Improvement Suggestions (Aggressive Tone) ────────────────────────
        suggestions = []
        if limitation.get("is_premature"):
             suggestions.append({
                 "id": "action_withdraw",
                 "title": "IMMEDIATE ACTION: Withdraw Complaint",
                 "description": "Withdraw the current complaint with liberty to re-file. Continuing with a premature complaint will lead to final dismissal and waste of time.",
                 "severity": "CRITICAL"
             })
        
        if limitation.get("notice_delay_days", 0) > 0:
             suggestions.append({
                 "id": "action_condonation",
                 "title": "FILE: S.142(1)(b) Condonation Application",
                 "description": "Prepare a formal application showing 'sufficient cause' for the notice delay (e.g., illness, administrative error).",
                 "severity": "HIGH"
             })

        if any(x in desc_lower for x in ["whatsapp", "email", "sms"]):
             suggestions.append({
                 "id": "action_65b",
                 "title": "PREPARE: Section 65B Certificate",
                 "description": "You MUST file an affidavit/certificate under S.65B of the Indian Evidence Act to make WhatsApp/Email records admissible.",
                 "severity": "HIGH"
             })

        if score < 60 and case_data.get("debt_evidence_type") == "Verbal":
             suggestions.append({
                 "id": "action_evidence_corroboration",
                 "title": "COLLECT: Indirect Debt Proof",
                 "description": "Gather bank statements showing the withdrawal of the loan amount or witness affidavits to counter the 'Financial Capacity' rebuttal.",
                 "severity": "HIGH"
             })

        confidence_score = round(sum(c.get("confidence", 0) for c in concepts) / len(concepts), 2) if concepts else None
        
        # ── ADVOCATE AUDIT (Hardening Summary) ───────────────────────────────
        is_cynical = score < 65 or any("CYNICAL" in str(t) for t in trace)
        audit = {
            "mode": "Cynical Advocate" if is_cynical else "Standard Analysis",
            "risk_status": "HIGHLY VULNERABLE" if score < 50 else ("CAUTION" if score < 75 else "BATTLE READY"),
            "critical_vulnerability": weaknesses[0] if weaknesses else "None Detected",
            "strategic_recommendation": suggestions[0]['title'] if suggestions else "Proceed with Caution"
        }

        lawyer_reasoning = _convert_to_lawyer_language(trace)

        concepts_for_response = [
            {
                "concept": c.get("concept", ""),
                "confidence": c.get("confidence", 0),
                "legal_impact": c.get("legal_impact", ""),
                "matched_phrases": c.get("matched_phrases", [])
            }
            for c in concepts
        ]

        NEGATIVE_RISK_ORDER = [
            "limitation_issue", "notice_defect", "notice_not_sent",
            "litigation_risk", "security_cheque", "signature_dispute", "no_debt_proof",
            "no_agreement", "cheque_misuse", "payment_already_made",
            "cheque_validity_issue", "dishonour_disputed"
        ]
        ranked_weaknesses = []
        seen_weak = set()
        for priority_concept in NEGATIVE_RISK_ORDER:
            for c in concepts:
                if c.get("concept") == priority_concept and c.get("confidence", 0) >= WEAKNESS_THRESHOLD and priority_concept not in seen_weak:
                    conf = c.get("confidence", 0)
                    severity = "CRITICAL" if conf >= 0.65 else ("HIGH" if conf >= 0.45 else "MEDIUM")
                    ranked_weaknesses.append({
                        "risk": priority_concept.replace("_", " ").title(),
                        "severity": severity,
                        "confidence": conf,
                        "detail": c.get("legal_impact", "")
                    })
                    seen_weak.add(priority_concept)
        for w in weaknesses:
            pass

        top_3_risks = ranked_weaknesses[:3]

        has_fatal = any(r["severity"] == "CRITICAL" for r in top_3_risks)
        has_high_risk = any(r["severity"] == "HIGH" for r in top_3_risks)

        if not case_data.get("notice_sent"):
            recommended_action = "SEND_NOTICE"
            decision_label = "Send Legal Notice First"
            decision_detail = "Statutory demand notice (S.138b) has not been sent. This is a mandatory pre-condition. The case cannot proceed to court without it."
            next_steps = [
                "Draft and dispatch demand notice via Registered Post (AD)",
                "Include cheque details, dishonour memo reference, and amount in notice",
                "Wait 15 days after notice delivery before filing complaint"
            ]
        elif score > 75 and not has_fatal:
            recommended_action = "FILE_COMPLAINT"
            decision_label = "File Criminal Complaint"
            decision_detail = f"Strong case ({score}/100). All legal prerequisites satisfied. Proceed to file complaint under Section 138 NI Act before the jurisdictional Magistrate."
            next_steps = [
                "Verify all original documents are in hand (cheque, memo, notice, AD card)",
                "File complaint within limitation period (1 month from cause of action)",
                "Engage an advocate to appear before the Magistrate"
            ]
        elif score >= 50 and not has_fatal:
            recommended_action = "FIX_THEN_FILE"
            decision_label = "Address Defects Before Filing"
            decision_detail = f"Moderate case ({score}/100). Foundational elements present but identifiable risks will be exploited by opposition. Strengthen evidence before filing."
            next_steps = [
                f"Priority fix: Resolve — {top_3_risks[0]['risk'] if top_3_risks else 'identified defects'}",
                "Obtain corroborating documents (bank statements, loan agreement, correspondence)",
                "Consult advocate for pre-filing assessment"
            ]
        elif score >= 40 and (has_fatal or has_high_risk):
            recommended_action = "CONSIDER_SETTLEMENT"
            decision_label = "Consider Strategic Settlement (Section 147)"
            top_risk = top_3_risks[0]['risk'] if top_3_risks else 'identified legal defects'
            decision_detail = (
                f"Moderate case ({score}/100) with significant vulnerability: {top_risk}. "
                "Criminal prosecution involves a high burden of proof (beyond reasonable doubt). "
                "A 'Without Prejudice' settlement under Section 147 NI Act allows for immediate recovery and "
                "avoids the risk of acquittal due to procedural defects. Highly recommended for commercial resolution."
            )
            next_steps = [
                "Draft and issue a formal Settlement Proposal with a default clause",
                "Evaluate the 'Time-Value of Money' (Immediate settlement vs. 3-year litigation)",
                "Negotiate interest rates (capped at 12%) to ensure enforceability",
                "If settlement fails, address all identified defects before proceeding to court"
            ]
        else:
            recommended_action = "HIGH_RISK_DEFEND"
            decision_label = "High Risk — Prepare Defence / Do Not File"
            decision_detail = f"Weak case ({score}/100). Critical legal defects present. Filing in current state risks dismissal or acquittal. Evaluate civil recovery as an alternative."
            next_steps = [
                f"Critical defect: {top_3_risks[0]['risk'] if top_3_risks else 'Multiple defects'} must be resolved",
                "Evaluate civil suit for recovery as an alternative to criminal proceedings",
                "If already filed, prepare defence strategy immediately"
            ]

        # === COUNTER-STRATEGY LOGIC (Expert Audit Fix) ===
        counter_strategies = {
            "Security Cheque": "Rebut via 'Sampelly Satyanarayana Rao (2016)'. Prove the cheque was against a crystallised debt via invoices or ledger entries.",
            "Signature Dispute": "Apply for Handwriting Expert comparison (S.45 Evidence Act). Rely on 'Bir Singh (2019)' — signature alone is not a full defense.",
            "No Debt Proof": "Invoke S.139 Presumption. Shift burden to accused to prove 'no debt' as per 'Rangappa v. Mohan (2010)'.",
            "Payment Already Made": "Cross-examine on payment mode. Produce bank statements showing no credit for the claimed repayment amount.",
            "Notice Defect": "If window closed, proceed with Civil Suit for Recovery (Order 37 CPC) which has a 3-year limitation.",
            "Stop Payment Instructions": "Apply 'Laxmi Dyechem (2012)'. Argue that stop payment does not escape S.138 if funds were insufficient or debt existed.",
            "Account Closed": "Cite 'NEPC Micon Ltd. (1999)'. Closing an account is a tactical avoidance that falls under S.138 liability.",
            "Vicarious Liability Defect": "Implead the Company and specifically aver the role of Directors as per 'Aneeta Hada (2012)'."
        }

        
        for risk_obj in top_3_risks:
            risk_name = risk_obj["risk"]
            if risk_name in counter_strategies:
                risk_obj["counter_strategy"] = counter_strategies[risk_name]
            else:
                risk_obj["counter_strategy"] = "Strengthen documentary evidence to rebut this specific defense during cross-examination."

        decision = {
            "recommended_action": recommended_action,
            "decision_label": decision_label,
            "detail": decision_detail,
            "next_steps": next_steps,
            "top_3_risks": top_3_risks,
            "draft_type_generated": engine_result.get("draft_type", "LEGAL_OPINION")
        }

        # === STRATEGY GENERATION ===
        strategy = []
        if score >= 75:
            strategy = [
                "Proceed with immediate filing of criminal complaint under S.138 NI Act.",
                "Ensure original cheque and bank memo are in safe custody.",
                "Prepare for summons delivery to accused's last known address.",
                "Maintain clear records of any subsequent communication from accused."
            ]
        elif score >= 50:
            strategy = [
                "Strengthen evidence of underlying debt before filing.",
                "Attempt one final written settlement proposal to resolve out of court.",
                "Verify jurisdictional facts (where cheque was presented/dishonoured).",
                "Prepare rebuttal for common defenses like 'security cheque'."
            ]
        else:
            strategy = [
                "Evaluate civil recovery suit as primary alternative.",
                "Address critical defects (notice/limitation) if still within window.",
                "Gather missing evidence (loan agreements, bank transfers).",
                "Consult senior counsel for specialized litigation strategy."
            ]

        # === ALTERNATIVE EVIDENCE SUGGESTIONS (Expert Audit Fix) ===
        alternative_evidence = []
        if not case_data.get("debt_proven"):
            alternative_evidence = [
                "WhatsApp/Email correspondence admitting liability",
                "Bank statements showing partial interest payments",
                "Ledger account entries/Tally records",
                "SMS logs discussing the repayment schedule"
            ]

        # === FALLBACK WEAKNESSES (even for strong cases) ===
        final_weaknesses = [f"{r['risk']} [{r['severity']} — conf: {r['confidence']:.0%}]" for r in ranked_weaknesses]
        if not final_weaknesses:
            if score >= 90:
                final_weaknesses = ["Standard litigation delays in jurisdictional courts", "Potential for accused to dispute signature (generic risk)"]
            else:
                final_weaknesses = ["Evidentiary burden of proof remains on complainant", "Potential for defense to delay proceedings through procedural applications"]

        return {
            "score":              score,
            "verdict":            verdict,
            "risk_level":         risk_level,
            "analysis_confidence": confidence_score,
            "decision":           decision,
            "strengths":          strengths,
            "weaknesses":         final_weaknesses,
            "issues":             [f"{r['risk']} ({r['severity']})" for r in ranked_weaknesses if r['severity'] in ['CRITICAL', 'HIGH']],
            "legal_strategy":     strategy,
            "alternative_evidence": alternative_evidence,
            "judicial_caveats":   engine_result.get("discretionary_caveats", []),
            "reasoning_trace":    lawyer_reasoning,
            "semantic_analysis": {
                "concepts_detected": concepts_for_response,
                "total_confidence":  confidence_score,
                "count":             len(concepts)
            },
            "executive_summary": {
                "score":              score,
                "recommended_action": recommended_action,
                "decision_label":     decision_label,
                "top_3_risks":        [r["risk"] for r in top_3_risks] or ["Standard litigation risks"],
                "top_strengths":      strengths[:3] or ["Pillar compliance"],
                "next_steps":         next_steps
            },
            "legal_analysis":    "\n".join(lawyer_reasoning) if lawyer_reasoning else "Standard legal analysis applied based on provided case pillars.",
            "analysis_details": {
                "issues":    [f"{r['risk']} [{r['severity']}]" for r in ranked_weaknesses],
                "strengths": strengths,
                "reasoning": lawyer_reasoning,
                "breakdown": breakdown
            },
            "defence_strategy":          engine_result.get("defences", []),
            "draft":                     engine_result.get("draft", ""),
            "draft_type":                engine_result.get("draft_type", "LEGAL_OPINION"),
            "timeline":                  engine_result.get("timeline", []),
            "limitation":                engine_result.get("limitation", {}),
            # Reasoning Layer
            "case_summary":              engine_result.get("case_summary", ""),
            "precedents":                engine_result.get("precedents", []),
            "statutory_interpretation":  engine_result.get("statutory_interpretation", []),
            "reasoning_trail":           engine_result.get("reasoning_trail", []),
            # Decision-Support Layer
            "risks_and_rebuttals":       engine_result.get("risks_and_rebuttals", []),
            "outcome_prediction":        engine_result.get("outcome_prediction", {}),
            "translated_verdict":        engine_result.get("translated_verdict", ""),
            "evidence_suggestions":      engine_result.get("evidence_suggestions", []),
            "advocate_audit":            audit,
            "case_data":                 case_data,
            "analysis_mode":             case_data.get("analysis_mode", "detailed"),
            "proof_present":             case_data.get("proof_present", True),
            "timestamp":      datetime.now().isoformat(),
            "engine_version": "v20.0-JUDIQ-ARCH"
        }
