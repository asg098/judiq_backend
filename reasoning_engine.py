import logging
from typing import List, Dict, Any
from kb_manager import kb_manager
from precedent_manager import precedent_manager

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """
    Reasoning Layer — Summarization, Statutory Interpretation, Precedent Matching,
    and Explainability Trail Generation.
    """

    # ── 1. Case Summarization ─────────────────────────────────────────────────
    @staticmethod
    def summarize_case(case_data: Dict) -> str:
        complainant = case_data.get("complainant_name") or "Complainant"
        accused     = case_data.get("accused_name")     or "Accused"
        amount      = case_data.get("amount")           or case_data.get("cheque_amount") or "an unspecified amount"
        cheque_no   = case_data.get("cheque_number")    or "N/A"
        reason      = case_data.get("dishonour_reason") or "Insufficient Funds"
        bank        = case_data.get("bank_name")        or "the drawee bank"
        accused_type = case_data.get("accused_type", "Individual")

        summary = (
            f"Case: {complainant} vs {accused} — Prosecution for Dishonour of Cheque No. {cheque_no} "
            f"valued at ₹{amount}. Reason: '{reason}'. "
        )

        # Statutory Pillars Audit
        missing_pillars = []
        if not case_data.get("notice_sent"): missing_pillars.append("Statutory Notice (S.138b)")
        if not case_data.get("debt_proven"): missing_pillars.append("Legally Enforceable Debt (S.139)")
        if not case_data.get("cheque_present"): missing_pillars.append("Negotiable Instrument (S.138)")

        if missing_pillars:
            summary += f"⚖️ LEGAL WARNING: Critical statutory pillars are MISSING: {', '.join(missing_pillars)}. "

        # Notice status
        if case_data.get("notice_sent"):
            mode = case_data.get("notice_mode") or "registered post"
            summary += f" Mandatory demand notice served via {mode}."
        else:
            summary += " CRITICAL: Statutory notice NOT served. Filing without notice is legally non-maintainable."

        # Debt / evidence status
        if case_data.get("debt_proven"):
            summary += " Underlying debt relationship is documented."
        else:
            summary += " Evidentiary Gap: Lack of debt documentation creates high acquittal risk via rebuttal of S.139 presumption."

        # Corporate flag
        if accused_type in ("Pvt Ltd/Ltd Company", "Company", "Partnership Firm"):
            directors = case_data.get("directors_named", False)
            if directors:
                summary += f" Corporate accused ({accused_type}) impleaded correctly with responsible officers."
            else:
                summary += f" FATAL DEFECT: Corporate accused ({accused_type}) impleaded WITHOUT naming responsible officers (S.141)."

        return summary


    # ── 2. Precedent Matching ─────────────────────────────────────────────────
    @staticmethod
    def match_precedents(concepts: List[Dict]) -> List[Dict]:
        matched: List[Dict] = []
        seen_citations: set = set()

        for concept_entry in concepts:
            concept_name = concept_entry.get("concept", "")
            confidence   = concept_entry.get("confidence", 0.5)

            # Pull structured precedents from statutes.json
            statute_precedents = kb_manager.get_precedents_for_concept(concept_name)
            for p in statute_precedents:
                citation = p.get("citation", "")
                if citation not in seen_citations:
                    seen_citations.add(citation)
                    matched.append({
                        "concept":      concept_name,
                        "case":         p.get("case", ""),
                        "citation":     citation,
                        "court":        p.get("court", "Supreme Court of India"),
                        "principle":    p.get("principle", ""),
                        "relevance":    round(min(p.get("relevance_score", confidence), 1.0), 2),
                        "is_live":      False
                    })

            # Pull any inline precedents from knowledge_base.json
            kb = kb_manager.get_knowledge_base()
            if concept_name in kb:
                kb_prec = kb[concept_name].get("precedent")
                if kb_prec and kb_prec not in seen_citations:
                    seen_citations.add(kb_prec)
                    matched.append({
                        "concept":   concept_name,
                        "case":      kb_prec,
                        "citation":  kb_prec,
                        "court":     "Supreme Court of India",
                        "principle": kb[concept_name].get("legal_impact", ""),
                        "relevance": round(confidence, 2),
                        "is_live":   False
                    })

        # Attach latest live precedents (from precedent_log.json)
        for p in precedent_manager.get_latest_precedents(3):
            title    = p.get("title", "")
            citation = p.get("citation", "")
            key      = citation or title
            if key and key not in seen_citations:
                seen_citations.add(key)
                matched.append({
                    "concept":   p.get("impact_area", "general"),
                    "case":      title,
                    "citation":  citation,
                    "court":     "Supreme Court of India",
                    "principle": p.get("summary", ""),
                    "relevance": 0.85,
                    "is_live":   True
                })

        # Sort by relevance descending, cap at 8
        matched.sort(key=lambda x: x["relevance"], reverse=True)
        return matched[:8]

    # ── 3. Statutory Interpretation ───────────────────────────────────────────
    @staticmethod
    def interpret_statutes(case_data: Dict, concepts: List[Dict]) -> List[Dict]:
        concept_names = {c["concept"] for c in concepts}
        interpretations: List[Dict] = []

        # ─ Section 138 ───────────────────────────────────────────────────────
        sec138 = kb_manager.get_ni_act_section("138")
        if case_data.get("cheque_present"):
            cond_met  = []
            cond_fail = []
            conditions = sec138.get("conditions", [])
            for cond in conditions:
                if "Notice" in cond and not case_data.get("notice_sent"):
                    cond_fail.append(cond)
                elif "debt" in cond.lower() and not case_data.get("debt_proven"):
                    cond_fail.append(cond)
                else:
                    cond_met.append(cond)

            status = "SATISFIED" if not cond_fail else ("PARTIAL" if cond_met else "DEFECTIVE")
            interpretations.append({
                "section":   "138",
                "title":     sec138.get("title", "Dishonour of cheque"),
                "status":    status,
                "finding":   (
                    "All Section 138 ingredients are satisfied. The case is prosecution-ready."
                    if status == "SATISFIED" else
                    f"Section 138 partially satisfied. Missing: {'; '.join(cond_fail)}."
                ),
                "punishment":    sec138.get("punishment", ""),
                "conditions_met":    cond_met,
                "conditions_failed": cond_fail,
            })
        else:
            interpretations.append({
                "section": "138",
                "title":   sec138.get("title", "Dishonour of cheque"),
                "status":  "NOT APPLICABLE",
                "finding": "FATAL: No cheque instrument present. Section 138 NI Act cannot be invoked without a negotiable instrument.",
                "conditions_met": [], "conditions_failed": []
            })

        # ─ Section 139 ───────────────────────────────────────────────────────
        sec139 = kb_manager.get_ni_act_section("139")
        interpretations.append({
            "section": "139",
            "title":   sec139.get("title", "Presumption in favour of holder"),
            "status":  "ACTIVE",
            "finding": (
                "The statutory presumption under S.139 is active in your favour. "
                "The burden is on the ACCUSED to prove no debt existed, not on you."
            ) if case_data.get("cheque_present") else (
                "S.139 presumption is not invocable without a cheque instrument."
            ),
            "interpretation": sec139.get("interpretation", ""),
        })

        # ─ Section 141 (Corporate only) ───────────────────────────────────────
        accused_type = case_data.get("accused_type", "Individual")
        if accused_type in ("Pvt Ltd/Ltd Company", "Company", "Partnership Firm"):
            sec141 = kb_manager.get_ni_act_section("141")
            has_directors = case_data.get("directors_named", False)
            interpretations.append({
                "section": "141",
                "title":   sec141.get("title", "Offences by companies"),
                "status":  "SATISFIED" if has_directors else "CRITICAL_DEFECT",
                "finding": (
                    "Responsible officers/directors have been named. S.141 vicarious liability is properly pleaded."
                    if has_directors else
                    "CRITICAL: The accused is a company but NO officers/directors are named in the complaint. "
                    "Per Aneeta Hada v. Godfather Travels (2012) 5 SCC 661, prosecution will FAIL without specific averments."
                ),
                "requirement": sec141.get("requirement", ""),
            })

        # ─ Section 142 (Limitation) ───────────────────────────────────────────
        sec142 = kb_manager.get_ni_act_section("142")
        interpretations.append({
            "section": "142",
            "title":   sec142.get("title", "Cognizance of offences"),
            "status":  "NOTE",
            "finding": (
                "Complaint must be filed within 1 month of the cause of action arising "
                "(expiry of 15-day payment window after notice). Verify your limitation period immediately."
            ),
            "limitation": sec142.get("limitation", ""),
        })

        # ─ Section 143A (Interim Compensation) ───────────────────────────────
        sec143a = kb_manager.get_ni_act_section("143A")
        interpretations.append({
            "section": "143A",
            "title":   sec143a.get("title", "Power to direct interim compensation"),
            "status":  "AVAILABLE",
            "finding": (
                "You may apply for interim compensation of up to 20% of the cheque amount "
                "at the stage of summoning the accused. This is an important interim relief."
            ),
            "limit": sec143a.get("limit", ""),
        })

        return interpretations

    # ── 4. Reasoning Trail (Explainability) ───────────────────────────────────
    @classmethod
    def generate_reasoning_trail(cls, case_data: Dict, concepts: List[Dict]) -> List[str]:
        trail: List[str] = []
        
        # 1. Fact Verification
        pillars = []
        if case_data.get("cheque_present"): pillars.append("S.138 instrument verified")
        if case_data.get("notice_sent"):    pillars.append("Demand notice complied")
        if case_data.get("debt_proven"):    pillars.append("Enforceable debt established")
        
        trail.append(
            f"RULE-BASED AUDIT: Verified {len(pillars)}/3 statutory pillars. "
            + (f"Compliance confirmed: {', '.join(pillars)}." if pillars else "FATAL ERROR: No statutory pillars satisfied.")
        )

        # 2. Semantic Intersection
        pos = [c for c in concepts if c.get("confidence", 0) >= 0.5 and "defect" not in c["concept"] and "no_" not in c["concept"]]
        neg = [c for c in concepts if c.get("confidence", 0) >= 0.5 and ("defect" in c["concept"] or "no_" in c["concept"] or "security" in c["concept"])]
        
        trail.append(
            f"SEMANTIC INFERENCE: Engine cross-referenced facts against legal DNA. "
            f"Detected {len(pos)} positive merits vs {len(neg)} procedural/strategic risks. "
            f"Top concepts: {', '.join([c['concept'].upper() for c in concepts[:3]]) or 'NONE'}."
        )

        # 3. Precedent Binding
        precs = cls.match_precedents(concepts)
        if precs:
            trail.append(
                f"PRECEDENT BINDING: Case facts anchored to {len(precs)} landmark judgments. "
                f"Primary legal authority applied: {precs[0]['case']} ({precs[0]['citation']})."
            )
        else:
            trail.append("AUTHORITY CHECK: No specific case-law match. Reverting to basic statutory interpretation.")

        # 4. Final Verdict Logic
        trail.append(
            "SYNTHETIC VERDICT: Final weighting based on statutory mandatory requirements + evidentiary strength + precedent alignment. "
            "Verdict generated via strict legal-logic thresholding (No Black Box)."
        )

        return trail

