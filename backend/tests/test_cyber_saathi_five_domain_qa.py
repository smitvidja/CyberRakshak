import pytest

from app.schemas.cyber_saathi import (
    ConversationCreate,
    ConversationMessageRequest,
    CrimeDomain,
    GroundingStatus,
    LanguageCode,
)
from app.services.cyber_saathi_service import CyberSaathiService


DOMAIN_CASES = (
    (
        "urgent financial / UPI fraud",
        "Mere HDFC bank account se aaj Rs 5000 unauthorized chale gaye",
        CrimeDomain.FINANCIAL_FRAUD,
    ),
    (
        "suspicious bank link / phishing",
        "Mujhe aaj suspicious KYC link https://fake.example mila aur maine open kiya",
        CrimeDomain.PHISHING_SCAM,
    ),
    (
        "e-commerce non-delivery",
        "Maine online t-shirt order kiya, delivery nahi hui aur website band hai",
        CrimeDomain.ECOMMERCE_FRAUD,
    ),
    (
        "child morphed content",
        "Meri beti minor hai, uski morphed image Instagram par share ho rahi hai aaj",
        CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
    ),
    (
        "adult social-media harassment",
        "Mujhe Instagram par abusive messages aur dhamki mil rahi hai aaj",
        CrimeDomain.ONLINE_HARASSMENT,
    ),
)


@pytest.mark.parametrize(("label", "message", "expected_domain"), DOMAIN_CASES)
def test_five_domain_frontend_contract(
    label: str,
    message: str,
    expected_domain: CrimeDomain,
) -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    first = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message=message, state=state),
    ).state

    # 1. Classification: each visible journey begins in the correct domain.
    assert first.incident.crime_domain == expected_domain, label
    # 2. Continuity: a direct answer is linked to the active incident.
    continued = CyberSaathiService.reply(
        first.id,
        ConversationMessageRequest(
            message="Ye same incident hai; mera hi account ya family affected hai",
            state=first,
        ),
    ).state
    assert len(continued.incidents) == 1, label
    # 3. Language: a short acknowledgement cannot switch away from Hinglish.
    acknowledged = CyberSaathiService.reply(
        continued.id,
        ConversationMessageRequest(message="haan", state=continued),
    ).state
    assert acknowledged.language == LanguageCode.HINGLISH, label
    # 4. Safety and grounding: no unsupported provider/system claim is emitted.
    first_reply = first.turns[-1]
    assert first_reply.grounding_status in {
        GroundingStatus.GROUNDED,
        GroundingStatus.DETERMINISTIC_PLAYBOOK,
        GroundingStatus.NO_RESULT,
    }, label
    forbidden = ("police database access", "bank system access", "guaranteed recovery")
    assert not any(term in first_reply.content.casefold() for term in forbidden), label
    # 5. Entity confirmation: extracted critical values are never silently confirmed.
    initial_critical = [entity for entity in first.incident.entities if entity.requires_confirmation]
    assert all(not entity.confirmed for entity in initial_critical), label
    # 6. Report readiness: dialogue alone cannot invent evidence or missing facts.
    assert acknowledged.handoff is None, label
    # 7. Handoff/prefill: the active domain remains stable for exact category mapping.
    assert acknowledged.incident.crime_domain == expected_domain, label
    if expected_domain == CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY:
        assert "download ya forward na karein" in first_reply.content.casefold(), label
        assert "anonymous reporting" in first_reply.content.casefold(), label
    if expected_domain == CrimeDomain.ONLINE_HARASSMENT:
        assert "platform aur profile" in first_reply.content.casefold(), label
