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
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from app.domain.models import PageEvidence, FormAuditItem, FormAuditReport


class FormAccessibilityAnalyzer:
    @staticmethod
    def analyze_forms(pages: List[PageEvidence], raw_html_map: Optional[Dict[str, str]] = None) -> FormAuditReport:
        forms_detected: List[FormAuditItem] = []
        if BeautifulSoup is None:
            return FormAuditReport(
                total_forms_found=0,
                forms_with_accessibility_issues=0,
                high_friction_forms_count=0,
                forms=[]
            )
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

                    # Missing labels check & placeholder anti-pattern
                    missing_labels = 0
                    placeholders_as_labels = 0
                    required_count = 0
                    autofill_count = 0
                    mobile_keyboard_ok = True

                    for inp in substantive_inputs:
                        inp_id = inp.get("id")
                        has_explicit_label = bool(inp_id and f.find("label", attrs={"for": inp_id}))
                        has_parent_label = bool(inp.find_parent("label"))
                        has_aria_label = bool(inp.get("aria-label") or inp.get("aria-labelledby"))
                        has_label = has_explicit_label or has_parent_label or has_aria_label
                        has_placeholder = bool(inp.get("placeholder"))

                        if not has_label:
                            missing_labels += 1
                            if has_placeholder:
                                placeholders_as_labels += 1

                        if inp.get("required") is not None or inp.get("aria-required") == "true":
                            required_count += 1

                        if inp.get("autocomplete"):
                            autofill_count += 1

                        # Mobile keyboard check for phone or numeric inputs
                        name_or_id = (inp.get("name") or inp.get("id") or "").lower()
                        i_type = inp.get("type", "text").lower()
                        if any(k in name_or_id for k in ("phone", "tel", "mobile")) and i_type not in ("tel", "number"):
                            mobile_keyboard_ok = False

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

                    # Privacy notice in form or immediate sibling
                    has_privacy = bool(
                        f.find("a", href=re.compile(r"privacy|terms", re.I))
                        or (f.parent and f.parent.find("a", href=re.compile(r"privacy|terms", re.I)))
                    )

                    # Validation messages
                    has_validation = bool(
                        f.find(class_=re.compile(r"error|invalid|feedback|helper|validation", re.I))
                        or f.find(attrs={"aria-describedby": True})
                    )

                    friction_risk = "LOW"
                    if input_count > 6 or missing_labels > 0:
                        friction_risk = "HIGH"
                    elif input_count > 4 or not has_captcha or placeholders_as_labels > 0:
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
                        friction_risk=friction_risk,
                        required_fields_count=required_count,
                        placeholders_as_labels_count=placeholders_as_labels,
                        autofill_supported_count=autofill_count,
                        mobile_keyboard_optimized=mobile_keyboard_ok,
                        privacy_notice_present=has_privacy,
                        validation_messages_present=has_validation,
                    ))
            # If raw HTML not provided, do NOT fabricate or synthesize fake form elements.

        total_forms = len(forms_detected)
        missing_lbl = sum(1 for f in forms_detected if f.missing_labels_count > 0)
        no_captcha = sum(1 for f in forms_detected if not f.has_captcha_or_honeypot)
        no_conf = sum(1 for f in forms_detected if not f.has_confirmation_destination)
        autofill_forms = sum(1 for f in forms_detected if f.autofill_supported_count > 0)
        mobile_kb_forms = sum(1 for f in forms_detected if f.mobile_keyboard_optimized)
        privacy_forms = sum(1 for f in forms_detected if f.privacy_notice_present)

        remedies = []
        if missing_lbl > 0:
            remedies.append(f"Explicitly associate <label for='...'> tags with all inputs across {missing_lbl} form(s) to pass WCAG 2.1 compliance.")
        if no_captcha > 0:
            remedies.append(f"Deploy Cloudflare Turnstile or invisible honeypot fields on {no_captcha} form(s) to eliminate spam submissions without adding friction.")
        if any(f.submit_button_text.lower() == "submit" for f in forms_detected):
            remedies.append("Replace generic 'Submit' button copy with value-driven CTAs (e.g., 'Claim Your Strategy Report' or 'Schedule VIP Demo').")
        if any(f.input_count > 5 for f in forms_detected):
            remedies.append("Consider reducing initial fields on high-friction forms or using a multi-step flow to decrease cognitive fatigue.")
        if any(f.placeholders_as_labels_count > 0 for f in forms_detected):
            remedies.append("Replace disappearing placeholder labels with persistent floating or above-input labels to preserve context during typing.")

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
            actionable_remedies=remedies,
            forms_with_autofill_support=autofill_forms,
            forms_with_mobile_keyboards=mobile_kb_forms,
            forms_with_privacy_notices=privacy_forms,
        )


def analyze_forms(pages: List[PageEvidence], raw_html_map: Optional[Dict[str, str]] = None) -> FormAuditReport:
    return FormAccessibilityAnalyzer.analyze_forms(pages, raw_html_map)
