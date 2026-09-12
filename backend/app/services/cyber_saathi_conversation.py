"""Conversation-state helpers for incident resolution and report preparation."""

from __future__ import annotations

import re
from hashlib import sha256

from app.schemas.cyber_saathi import (
    ChecklistStatus,
    ConversationIncident,
    ConversationState,
    CrimeDomain,
    EntityType,
    LanguageCode,
    ReportChecklistItem,
    ReportPreparation,
    TurnPurpose,
    UnderstandingResult,
)
from app.services.cyber_saathi_understanding import UnderstandingEngine


ACTION_BLOCKED_MARKERS = (
    "cannot", "can't", "cant", "could not", "couldn't", "not able",
    "unable", "not possible", "nahi ho", "nahi kar", "nhi ho", "nhi kar",
    "nai ho", "nai kar", "payega", "nahi mil", "nhi mil", "नहीं कर", "नहीं हो",
)
REPORT_PREPARATION_MARKERS = (
    "all done", "did all", "done everything", "sab kar liya", "sab kr liya",
    "ye sab kar liya", "ye sab kr liya", "everything complete", "report ready",
    "prepare report", "fill report", "report bhar", "रिपोर्ट तैयार",
)
NEXT_STEP_MARKERS = (
    "what next", "now what", "ab kya", "aage kya", "next step", "what should i do",
    "kya karu", "kya karoon", "क्या करूं", "अब क्या",
)
CORRECTION_MARKERS = (
    "correction", "actually", "change it", "galat", "sahi amount", "instead",
    "सुधार", "गलत",
)
STOPWORDS = {
    "a", "an", "the", "i", "me", "my", "is", "was", "to", "and", "or", "it",
    "hai", "tha", "thi", "the", "ko", "ke", "ki", "ka", "mein", "me", "se",
    "par", "pe", "aur", "ab", "maine", "mujhe", "mere", "meri",
}


def normalized_text(message: str) -> str:
    return UnderstandingEngine.normalize_query(message)


def message_fingerprint(message: str) -> str:
    normalized = re.sub(r"[^a-z0-9\u0900-\u097f]+", " ", normalized_text(message))
    return sha256(" ".join(normalized.split()).encode("utf-8")).hexdigest()


def _tokens(message: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9\u0900-\u097f]+", normalized_text(message))
        if len(token) > 1 and token not in STOPWORDS
    }


def _similarity(left: str, right: str) -> float:
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    if not left_tokens or not right_tokens:
        return 0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def find_matching_incident(
    state: ConversationState,
    message: str,
    understanding: UnderstandingResult,
) -> ConversationIncident | None:
    fingerprint = message_fingerprint(message)
    best: tuple[float, ConversationIncident] | None = None
    for record in state.incidents:
        if fingerprint in record.message_fingerprints:
            return record
        summary = record.incident.summary or ""
        if summary and message_fingerprint(summary) == fingerprint:
            return record
        domains_compatible = understanding.crime_domain in {
            CrimeDomain.UNKNOWN,
            CrimeDomain.OTHER,
            record.incident.crime_domain,
        }
        if not domains_compatible:
            continue
        score = _similarity(message, summary)
        if score >= 0.68 and (best is None or score > best[0]):
            best = (score, record)
    return best[1] if best else None


def classify_turn_purpose(message: str) -> TurnPurpose:
    lowered = normalized_text(message)
    if any(marker in lowered for marker in REPORT_PREPARATION_MARKERS):
        return TurnPurpose.REPORT_PREPARATION
    if any(marker in lowered for marker in ACTION_BLOCKED_MARKERS):
        return TurnPurpose.ACTION_BLOCKED
    if any(marker in lowered for marker in NEXT_STEP_MARKERS):
        return TurnPurpose.NEXT_STEP
    if any(marker in lowered for marker in CORRECTION_MARKERS):
        return TurnPurpose.CORRECTION
    return TurnPurpose.GENERAL_QUESTION


def blocked_action(message: str) -> str:
    lowered = normalized_text(message)
    if "screenshot" in lowered or "screen shot" in lowered:
        return "screenshot"
    if any(marker in lowered for marker in ("bank", "provider", "customer care")):
        return "bank_contact"
    if any(marker in lowered for marker in ("transaction", "utr", "reference", "order id")):
        return "reference_number"
    if any(marker in lowered for marker in ("report", "complaint", "portal")):
        return "reporting"
    if any(marker in lowered for marker in ("block", "password", "account")):
        return "account_protection"
    return "recommended_step"


def infer_reporting_for(state: ConversationState) -> tuple[str, str | None]:
    user_text = " ".join(turn.content for turn in state.turns if turn.role == "user")
    lowered = normalized_text(user_text)
    # Every marker here used to be romanised only, so a citizen writing in
    # Devanagari - "मुझे एक आदमी परेशान कर रहा है" - was always UNKNOWN and got
    # asked "did this happen to you, your child, or someone else?" on every turn,
    # having already said so in their first sentence.
    child_other = (
        "my child", "my daughter", "my son", "meri beti", "mera beta", "mere bacche",
        "मेरी बेटी", "मेरा बेटा", "मेरे बच्चे", "मेरा बच्चा", "मेरी बच्ची",
    )
    other = (
        "my father", "my mother", "my wife", "my husband", "my brother", "my sister",
        "mere papa", "meri mummy", "meri maa", "mere bhai", "meri behen", "my friend",
        "my cousin", "meri cousin", "mere cousin",
        "मेरे पिता", "मेरे पापा", "मेरी माँ", "मेरी मां", "मेरी मम्मी", "मेरी पत्नी",
        "मेरे पति", "मेरा भाई", "मेरी बहन", "मेरा दोस्त", "मेरी सहेली",
        "मेरी चचेरी", "मेरे चचेरे",
    )
    if any(marker in lowered for marker in child_other) or UnderstandingEngine.has_child_context(
        lowered
    ):
        return "CHILD", None
    if any(marker in lowered for marker in other):
        return "OTHER", None
    self_markers = (
        "with me", "happened to me", "mere saath", "mujhe", "my account", "my phone",
        "my image", "my photo", "i ordered", "maine", "mere account", "mere bank",
        "meri account", "mera phone", "meri image", "meri photo", "i am minor", "i'm minor",
        "मुझे", "मैंने", "मेरे साथ", "मेरा अकाउंट", "मेरे अकाउंट", "मेरा फोन",
        "मेरी फोटो", "मेरी तस्वीर", "मेरे बैंक", "मेरा बैंक", "मेरी आईडी",
        # "someone is harassing me" names the victim as clearly as "happened to
        # me" does. Tied to a verb of harm rather than a bare "me", so "tell me
        # what to do" is not read as a statement about who was affected.
        "harassing me", "threatening me", "blackmailing me", "stalking me",
        "abusing me", "troubling me", "scammed me", "cheated me", "duped me",
        "sent me", "sending me", "messaging me", "calling me", "hacked my",
        "stole my", "misusing my", "morphed my", "leaked my",
    )
    if any(marker in lowered for marker in self_markers):
        return "SELF", None
    if any(
        owner in lowered.split() for owner in ("my", "mere", "meri", "mera", "मेरे", "मेरी", "मेरा")
    ) and any(
        subject in lowered
        for subject in ("bank account", "account", "phone", "profile", "order", "अकाउंट", "फोन", "प्रोफाइल")
    ):
        return "SELF", None
    return "UNKNOWN", None


def build_report_preparation(
    state: ConversationState,
    record: ConversationIncident,
) -> ReportPreparation:
    incident = record.incident
    reporting_for, affected_name = infer_reporting_for(state)
    existing = record.report_preparation
    if existing.reporting_for != "UNKNOWN":
        reporting_for = existing.reporting_for
        affected_name = existing.affected_person_name

    entities_by_type = {entity.type: entity for entity in incident.entities}
    language = state.language
    labels = _labels(language)
    requires_safety_evidence = incident.crime_domain in {
        CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
        CrimeDomain.CHILD_SAFETY,
        CrimeDomain.ONLINE_HARASSMENT,
        CrimeDomain.CYBERSTALKING,
    }

    def item(
        key: str,
        *,
        collected: bool,
        required: bool = True,
        preview: str | None = None,
        unavailable: bool = False,
    ) -> ReportChecklistItem:
        status = (
            ChecklistStatus.NOT_AVAILABLE
            if unavailable
            else ChecklistStatus.COLLECTED
            if collected
            else ChecklistStatus.MISSING
            if required
            else ChecklistStatus.OPTIONAL
        )
        safe_preview = preview[:297] + "..." if preview and len(preview) > 300 else preview
        return ReportChecklistItem(
            key=key,
            label=labels[key],
            status=status,
            required=required,
            value_preview=safe_preview,
        )

    checklist = [
        item("incident_description", collected=bool(incident.summary), preview=incident.summary),
        item(
            "affected_person",
            collected=reporting_for != "UNKNOWN",
            preview=reporting_for if reporting_for != "UNKNOWN" else None,
        ),
        item(
            "incident_time",
            collected=EntityType.DATE in entities_by_type or EntityType.DATE_TIME in entities_by_type,
            required=False,
            preview=(entities_by_type.get(EntityType.DATE) or entities_by_type.get(EntityType.DATE_TIME)).value
            if EntityType.DATE in entities_by_type or EntityType.DATE_TIME in entities_by_type
            else None,
        ),
        item(
            "evidence",
            collected=bool(existing.attachments),
            required=requires_safety_evidence,
            preview=f"{len(existing.attachments)} attachment(s)" if existing.attachments else None,
            unavailable=record.blocked_actions.get("screenshot", 0) > 0 and not existing.attachments,
        ),
    ]
    identifier_entities = [
        entity
        for entity in incident.entities
        if entity.type
        in {
            EntityType.PHONE_NUMBER,
            EntityType.EMAIL,
            EntityType.UPI_ID,
            EntityType.URL,
            EntityType.USERNAME,
            EntityType.ACCOUNT_ID,
        }
    ]
    checklist.append(
        item(
            "suspect_details",
            collected=bool(identifier_entities or existing.suspect_details),
            required=False,
            preview=(
                ", ".join(entity.value for entity in identifier_entities[:4])
                or existing.suspect_details
            ),
        )
    )
    if incident.crime_domain == CrimeDomain.FINANCIAL_FRAUD:
        protected = bool(
            {"bank_contacted", "bank_protection_requested"}
            & set(record.completed_actions)
        )
        checklist.append(
            item(
                "bank_action",
                collected=protected,
                required=False,
                preview=labels["bank_action_done"] if protected else None,
            )
        )
        for key, entity_type in (
            ("amount", EntityType.AMOUNT),
            ("transaction_id", EntityType.TRANSACTION_ID),
            ("provider", EntityType.PROVIDER),
        ):
            entity = entities_by_type.get(entity_type)
            preview = None
            if entity is not None:
                preview = (
                    UnderstandingEngine.format_amount_for_display(entity.normalized_value)
                    if entity.type == EntityType.AMOUNT and entity.normalized_value
                    else entity.value
                )
            checklist.append(item(key, collected=entity is not None, required=key == "amount", preview=preview))
    elif incident.crime_domain == CrimeDomain.ECOMMERCE_FRAUD:
        checklist.extend(
            (
                item("order_reference", collected=EntityType.TRANSACTION_ID in entities_by_type, required=False),
                item("seller_or_website", collected=EntityType.URL in entities_by_type, required=False),
            )
        )
    elif incident.crime_domain in {CrimeDomain.PHISHING_SCAM, CrimeDomain.IMPERSONATION}:
        checklist.append(
            item(
                "sender_or_link",
                collected=bool(identifier_entities),
                required=False,
                preview=", ".join(entity.value for entity in identifier_entities[:4]) or None,
            )
        )
    elif incident.crime_domain in {CrimeDomain.ACCOUNT_COMPROMISE, CrimeDomain.IDENTITY_THEFT}:
        account = entities_by_type.get(EntityType.ACCOUNT_SERVICE) or entities_by_type.get(EntityType.USERNAME)
        checklist.append(
            item(
                "affected_account",
                collected=account is not None,
                required=False,
                preview=account.value if account else None,
            )
        )
    elif incident.crime_domain in {CrimeDomain.MALWARE, CrimeDomain.CYBER_TERRORISM, CrimeDomain.MISINFORMATION}:
        source = entities_by_type.get(EntityType.URL) or entities_by_type.get(EntityType.ACCOUNT_SERVICE)
        checklist.append(
            item(
                "source_or_device",
                collected=source is not None,
                required=False,
                preview=source.value if source else None,
            )
        )
    elif incident.crime_domain in {
        CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
        CrimeDomain.CHILD_SAFETY,
        CrimeDomain.ONLINE_HARASSMENT,
        CrimeDomain.CYBERSTALKING,
    }:
        platform = entities_by_type.get(EntityType.SOCIAL_PLATFORM)
        username = entities_by_type.get(EntityType.USERNAME)
        checklist.extend(
            (
                item("platform", collected=platform is not None, required=True, preview=platform.value if platform else None),
                item("profile_identifier", collected=username is not None, required=False, preview=username.value if username else None),
            )
        )

    missing = [entry.key for entry in checklist if entry.required and entry.status == ChecklistStatus.MISSING]
    return ReportPreparation(
        reporting_for=reporting_for,
        affected_person_name=affected_name,
        checklist=checklist,
        attachments=existing.attachments,
        missing_required_keys=missing,
        ready_for_review=not missing,
        packet_ready=existing.packet_ready,
        draft_prepared=existing.draft_prepared,
        suspect_details=existing.suspect_details,
    )


def _labels(language: LanguageCode) -> dict[str, str]:
    english = {
        "incident_description": "What happened",
        "affected_person": "Who was affected",
        "incident_time": "Approximate date and time (if known)",
        "evidence": "Screenshots, PDF, payment proof or messages (optional)",
        "amount": "Amount lost",
        "transaction_id": "Transaction/UTR/reference number (if known)",
        "provider": "Bank or payment provider (if known)",
        "order_reference": "Order/reference number (if known)",
        "seller_or_website": "Seller or website details (if known)",
        "platform": "App or social platform (if known)",
        "profile_identifier": "Profile/username/URL (if known)",
        "suspect_details": "Suspect number, link, account or profile (if known)",
        "bank_action": "Bank/UPI protection action",
        "bank_action_done": "Official provider contacted / protection requested",
        "sender_or_link": "Sender, caller, profile or link (if known)",
        "affected_account": "Affected account or service (if known)",
        "source_or_device": "Source, URL, app or affected device detail (if known)",
    }
    if language == LanguageCode.HI:
        return {
            **english,
            "incident_description": "क्या हुआ",
            "affected_person": "कौन प्रभावित हुआ",
            "incident_time": "अनुमानित तारीख और समय (यदि पता हो)",
            "evidence": "स्क्रीनशॉट, PDF, भुगतान प्रमाण या संदेश (वैकल्पिक)",
            "amount": "गई हुई राशि",
            "suspect_details": "संदिग्ध नंबर, लिंक, अकाउंट या प्रोफाइल (यदि पता हो)",
            "bank_action": "बैंक/UPI सुरक्षा कार्रवाई",
            "bank_action_done": "आधिकारिक सेवा से संपर्क / सुरक्षा अनुरोध दर्ज",
            "sender_or_link": "भेजने वाला, कॉलर, प्रोफाइल या लिंक (यदि पता हो)",
            "affected_account": "प्रभावित अकाउंट या सेवा (यदि पता हो)",
            "source_or_device": "स्रोत, URL, ऐप या प्रभावित डिवाइस विवरण (यदि पता हो)",
        }
    if language == LanguageCode.HINGLISH:
        return {
            **english,
            "incident_description": "Kya hua",
            "affected_person": "Kaun affected hua",
            "incident_time": "Approximate date aur time (agar pata ho)",
            "evidence": "Screenshots, PDF, payment proof ya messages (optional)",
            "amount": "Kitna amount gaya",
            "suspect_details": "Suspect number, link, account ya profile (agar pata ho)",
            "bank_action": "Bank/UPI protection action",
            "bank_action_done": "Official provider contacted / protection request recorded",
            "sender_or_link": "Sender, caller, profile ya link (agar pata ho)",
            "affected_account": "Affected account ya service (agar pata ho)",
            "source_or_device": "Source, URL, app ya affected device detail (agar pata ho)",
        }
    return english
