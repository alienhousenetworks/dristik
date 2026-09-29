"""
Dristik AI Web Form Accessibility & CRO Friction Analyzer
Inspects <form> elements on crawled pages:
- input counts, types (email, tel, text, password)
- missing <label for> associations (WCAG 2.1 accessibility violations)
- submit button text (generic "Submit" vs high-intent conversion CTA)
- captcha / honeypot bot defense presence
- thank-you / confirmation destination
"""
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from app.domain.models import PageEvidence, FormAuditItem, FormAuditReport


class FormAccessibilityAnalyzer:
    @staticmethod
    def analyze_forms(pages: List[PageEvidence], raw_html_map: Optional[Dict[str, str]] = None) -> FormAuditReport:
        forms_detected: List[FormAuditItem] = []
        raw_html_map = raw_html_map or {}

        for p in pages:
            html = raw_html_map.get(p.url) or getattr(p, "raw_html", None)
            if not html and getattr(p, "snapshot_path", None):
                try:
                    from pathlib import Path
                    sp = Path(p.snapshot_path)
                    if sp.exists():
                        html = sp.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass
            if html:
                soup = BeautifulSoup(html, "html.parser")
                form_tags = soup.find_all("form")
                for idx, f in enumerate(form_tags):
                    f_id = f.get("id") or f"form_{idx + 1}"
                    f_action = f.get("action") or ""

                    # Find all inputs, selects, textareas
                    inputs = f.find_all(["input", "textarea", "select"])
                    # Filter out hidden or submit inputs
                    substantive_inputs = [
                        inp for inp in inputs
                        if inp.get("type") not in ("hidden", "submit", "image", "button")
                    ]

                    input_count = len(substantive_inputs)
                    input_types = [inp.get("type", "text").lower() for inp in substantive_inputs]

                    # Missing labels check (missing 'id' matching a <label for="id"> or not wrapped in <label>)
                    missing_labels = 0
                    for inp in substantive_inputs:
                        inp_id = inp.get("id")
                        has_explicit_label = bool(inp_id and f.find("label", attrs={"for": inp_id}))
                        has_parent_label = bool(inp.find_parent("label"))
                        has_aria_label = bool(inp.get("aria-label") or inp.get("aria-labelledby"))
                        if not (has_explicit_label or has_parent_label or has_aria_label):
                            missing_labels += 1

                    # Submit button text
                    submit_btn = f.find(["button", "input"], attrs={"type": "submit"}) or f.find("button")
                    submit_text = (submit_btn.get_text(strip=True) if submit_btn else "") or (submit_btn.get("value") if submit_btn else "") or "Submit"

                    # Captcha / honeypot detection
                    f_str = str(f).lower()
                    has_captcha = any(
                        term in f_str
                        for term in ["recaptcha", "hcaptcha", "turnstile", "cf-turnstile", "honeypot", "g-recaptcha", "captcha"]
                    )

                    # Confirmation destination
                    has_conf = bool(f_action and ("thank" in f_action.lower() or "confirm" in f_action.lower() or "success" in f_action.lower()))

                    friction_risk = "LOW"
                    if input_count > 6 or missing_labels > 0:
                        friction_risk = "HIGH"
                    elif input_count > 4 or not has_captcha:
                        friction_risk = "MEDIUM"

                    forms_detected.append(FormAuditItem(
                        page_url=p.url,
                        form_id=f_id,
                        form_action=f_action or None,
                        input_count=input_count,
                        missing_labels_count=missing_labels,
                        input_types=input_types,
                        submit_button_text=submit_text,
                        has_captcha_or_honeypot=has_captcha,
                        has_confirmation_destination=has_conf,
                        friction_risk=friction_risk
                    ))
            # If raw HTML not provided, do NOT fabricate or synthesize fake form elements.

        total_forms = len(forms_detected)
        missing_lbl = sum(1 for f in forms_detected if f.missing_labels_count > 0)
        no_captcha = sum(1 for f in forms_detected if not f.has_captcha_or_honeypot)
        no_conf = sum(1 for f in forms_detected if not f.has_confirmation_destination)

        remedies = []
        if missing_lbl > 0:
            remedies.append(f"Explicitly associate <label for='...'> tags with all inputs across {missing_lbl} form(s) to pass WCAG 2.1 compliance.")
        if no_captcha > 0:
            remedies.append(f"Deploy Cloudflare Turnstile or invisible honeypot fields on {no_captcha} form(s) to eliminate spam submissions without adding friction.")
        if any(f.submit_button_text.lower() == "submit" for f in forms_detected):
            remedies.append("Replace generic 'Submit' button copy with value-driven CTAs (e.g., 'Claim Your Strategy Report' or 'Schedule VIP Demo').")
        if any(f.input_count > 5 for f in forms_detected):
            remedies.append("Consider reducing initial fields on high-friction forms or using a multi-step flow to decrease cognitive fatigue.")

        if total_forms == 0:
            grade = "N/A"
            friction_score = 0.0
            remedies = ["No interactive web forms detected on crawled pages."]
        else:
            friction_score = (missing_lbl * 20.0) + (no_captcha * 15.0) + (no_conf * 10.0)
            friction_score = min(100.0, friction_score)
            if friction_score < 15.0:
                grade = "A"
            elif friction_score < 35.0:
                grade = "B"
            elif friction_score < 60.0:
                grade = "C"
            else:
                grade = "D"

        return FormAuditReport(
            total_forms_detected=total_forms,
            forms=forms_detected,
            forms_with_missing_labels=missing_lbl,
            forms_without_captcha=no_captcha,
            forms_without_confirmation=no_conf,
            cro_friction_grade=grade,
            friction_score=friction_score,
            actionable_remedies=remedies
        )


def analyze_forms(pages: List[PageEvidence], raw_html_map: Optional[Dict[str, str]] = None) -> FormAuditReport:
    return FormAccessibilityAnalyzer.analyze_forms(pages, raw_html_map)
