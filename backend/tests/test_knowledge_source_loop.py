"""Closing a knowledge gap: propose an official source, a second admin approves, publish.

The safety properties under test:
- only administrators touch proposals, and only official https sources are accepted
- nobody approves their own proposal (two people stand behind every new source)
- nothing reaches the corpus until the publish step writes the versioned pack
- publishing never silently drops semantic embeddings, and restores the files on failure
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.security import hash_password
from app.models import KnowledgeGapSignal, KnowledgeSourceProposal, User
from app.models.enums import UserRole
from app.schemas.cyber_saathi import KnowledgeDomain, KnowledgeSearchRequest
from app.services.cyber_saathi import knowledge as knowledge_module
from app.services.knowledge_gap_service import KnowledgeGapService
from app.services.knowledge_source_service import KnowledgeSourceService

REAL_PACK = knowledge_module.SOURCE_PACK_PATH
REAL_INDEX = knowledge_module.INDEX_PATH


def _admin(client, session) -> tuple[dict[str, str], User]:
    email = f"source-admin-{uuid4().hex}@example.com"
    user = User(email=email, password_hash=hash_password("not-a-real-password"), role=UserRole.ADMIN)
    session.add(user)
    session.commit()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "not-a-real-password"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}, user


def _warrior(client) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"warrior-{suffix}@example.com"
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "phone": f"+9177{suffix[:8]}", "password": "not-a-real-password", "role": "CYBER_WARRIOR"},
    ).status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "not-a-real-password"})
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def _gap(session) -> KnowledgeGapSignal:
    signal = KnowledgeGapService.record(
        session,
        question=f"What do I do if my SIM suddenly stops working {uuid4().hex[:6]}",
        crime_domain="account_compromise",
        knowledge_domain=None,
        language="EN",
    )
    session.commit()
    assert signal is not None
    return signal


def _payload(**overrides) -> dict:
    payload = {
        "source_title": "Sanchar Saathi - report a suspected SIM swap",
        "source_url": "https://sancharsaathi.gov.in/sfc/",
        "source_type": "official_public_service",
        "language": "EN",
        "domains": ["account_compromise"],
        "published_on": "2026-10-01",
        "section_title": "If your mobile network stops working unexpectedly",
        "text": (
            "If your phone suddenly loses mobile network and you start receiving OTP or bank "
            "alerts you did not request, someone may have obtained a duplicate SIM. Contact "
            "your telecom operator at once to block the SIM, and call your bank to freeze "
            "transactions before reporting at cybercrime.gov.in or 1930."
        ),
        "retrieval_terms": ["sim swap", "duplicate sim", "lost mobile network"],
    }
    payload.update(overrides)
    return payload


# --- access and validation -----------------------------------------------------


def test_only_administrators_can_use_the_proposal_api(api_client) -> None:
    client, _ = api_client
    assert client.get("/api/v1/admin/knowledge-sources").status_code == 401
    warrior = _warrior(client)
    assert client.get("/api/v1/admin/knowledge-sources", headers=warrior).status_code == 403
    assert client.post("/api/v1/admin/knowledge-sources", headers=warrior, json=_payload()).status_code == 403
    assert client.patch(
        f"/api/v1/admin/knowledge-sources/{uuid4()}/review", headers=warrior, json={"decision": "APPROVED"}
    ).status_code == 403


@pytest.mark.parametrize(
    "override",
    [
        {"source_url": "https://example.com/advice"},  # not an official domain
        {"source_url": "http://cybercrime.gov.in/advice"},  # not https
        {"source_url": "https://cybercrime.gov.in.attacker.net/x"},  # lookalike host
        {"source_type": "blog_post"},
        {"text": "Too short to be a real excerpt."},
        {"published_on": "2026-02-30"},
        {"domains": []},
        {"domains": ["phishing", "phishing"]},
        {"language": "FR"},
    ],
)
def test_proposals_must_be_well_formed_official_sources(api_client, override) -> None:
    client, session = api_client
    headers, _ = _admin(client, session)
    response = client.post("/api/v1/admin/knowledge-sources", headers=headers, json=_payload(**override))
    assert response.status_code == 422, override


def test_a_proposal_for_an_unknown_gap_is_refused(api_client) -> None:
    client, session = api_client
    headers, _ = _admin(client, session)
    response = client.post("/api/v1/admin/knowledge-sources", headers=headers, json=_payload(gap_id=str(uuid4())))
    assert response.status_code == 404


# --- two-person review -------------------------------------------------------------


def test_a_second_administrator_must_approve_and_the_gap_moves_to_reviewed(api_client) -> None:
    client, session = api_client
    proposer, _ = _admin(client, session)
    reviewer, reviewer_user = _admin(client, session)
    gap = _gap(session)

    created = client.post("/api/v1/admin/knowledge-sources", headers=proposer, json=_payload(gap_id=str(gap.id)))
    assert created.status_code == 201
    proposal_id = created.json()["data"]["id"]
    assert created.json()["data"]["status"] == "PENDING"

    own = client.patch(f"/api/v1/admin/knowledge-sources/{proposal_id}/review", headers=proposer, json={"decision": "APPROVED"})
    assert own.status_code == 403
    assert own.json()["error"]["code"] == "SECOND_REVIEWER_REQUIRED"

    approved = client.patch(
        f"/api/v1/admin/knowledge-sources/{proposal_id}/review",
        headers=reviewer,
        json={"decision": "APPROVED", "review_note": "Matches the official page."},
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "APPROVED"
    assert approved.json()["data"]["reviewed_by_id"] == str(reviewer_user.id)

    session.refresh(gap)
    assert gap.status == "REVIEWED", "approval alone does not claim the gap is actioned"
    assert "awaiting publish" in (gap.resolution_note or "")

    again = client.patch(f"/api/v1/admin/knowledge-sources/{proposal_id}/review", headers=reviewer, json={"decision": "REJECTED"})
    assert again.status_code == 409


def test_a_rejected_proposal_leaves_the_gap_open(api_client) -> None:
    client, session = api_client
    proposer, _ = _admin(client, session)
    reviewer, _ = _admin(client, session)
    gap = _gap(session)
    created = client.post("/api/v1/admin/knowledge-sources", headers=proposer, json=_payload(gap_id=str(gap.id)))
    rejected = client.patch(
        f"/api/v1/admin/knowledge-sources/{created.json()['data']['id']}/review",
        headers=reviewer,
        json={"decision": "REJECTED", "review_note": "Page does not say this."},
    )
    assert rejected.json()["data"]["status"] == "REJECTED"
    session.refresh(gap)
    assert gap.status == "OPEN"

    listed = client.get("/api/v1/admin/knowledge-sources?status=REJECTED", headers=reviewer)
    assert created.json()["data"]["id"] in [row["id"] for row in listed.json()["data"]]


# --- publish -------------------------------------------------------------------------


@pytest.fixture
def temp_corpus(tmp_path, monkeypatch):
    """A private copy of the source pack and a lexical index, so publishing in a test
    can never touch the committed files."""
    pack = tmp_path / "sources.json"
    index = tmp_path / "knowledge_index.json"
    shutil.copy2(REAL_PACK, pack)
    monkeypatch.setattr(knowledge_module, "SOURCE_PACK_PATH", pack)
    monkeypatch.setattr(knowledge_module, "INDEX_PATH", index)
    knowledge_module.rebuild_index(index, semantic_embeddings=False, reuse_existing=False)
    knowledge_module.KnowledgeService.clear_cache()
    yield pack, index
    knowledge_module.KnowledgeService.clear_cache()


def _approved(client, session) -> tuple[KnowledgeSourceProposal, KnowledgeGapSignal]:
    proposer, _ = _admin(client, session)
    reviewer, _ = _admin(client, session)
    gap = _gap(session)
    created = client.post("/api/v1/admin/knowledge-sources", headers=proposer, json=_payload(gap_id=str(gap.id)))
    client.patch(f"/api/v1/admin/knowledge-sources/{created.json()['data']['id']}/review", headers=reviewer, json={"decision": "APPROVED"})
    proposal = session.get(KnowledgeSourceProposal, created.json()["data"]["id"])
    session.refresh(proposal)
    return proposal, gap


def test_publishing_adds_the_source_to_the_pack_and_the_served_index(api_client, temp_corpus) -> None:
    client, session = api_client
    pack_path, _ = temp_corpus
    before = json.loads(pack_path.read_text(encoding="utf-8"))
    proposal, gap = _approved(client, session)

    result = KnowledgeSourceService.publish(session)
    source_id = KnowledgeSourceService.source_id_for(proposal)
    assert result["status"] == "published" and result["published"] == [source_id]

    after = json.loads(pack_path.read_text(encoding="utf-8"))
    assert len(after["sources"]) == len(before["sources"]) + 1
    assert after["sources"][:-1] == before["sources"], "existing sources are untouched"
    assert after["sources"][-1]["source_url"] == "https://sancharsaathi.gov.in/sfc/"

    # The rebuilt index is the one Cyber Saathi serves, and it passes the load-time checks.
    knowledge_module.KnowledgeService.clear_cache()
    served = knowledge_module.KnowledgeService._load_index()
    assert any(chunk["source"]["source_id"] == source_id for chunk in served["chunks"])
    found = knowledge_module.KnowledgeService.search(
        KnowledgeSearchRequest(query="my mobile network stopped working and I got OTP alerts, duplicate SIM", domain=KnowledgeDomain.ACCOUNT_COMPROMISE, top_k=5)
    )
    assert source_id in [match.source_id for match in found.matches]

    session.refresh(proposal)
    session.refresh(gap)
    assert proposal.status == "PUBLISHED" and proposal.published_source_id == source_id
    assert gap.status == "ACTIONED"

    assert KnowledgeSourceService.publish(session)["status"] == "nothing_to_publish"


def test_a_dry_run_writes_nothing(api_client, temp_corpus) -> None:
    client, session = api_client
    pack_path, index_path = temp_corpus
    pack_before, index_before = pack_path.read_bytes(), index_path.read_bytes()
    proposal, _ = _approved(client, session)

    result = KnowledgeSourceService.publish(session, dry_run=True)
    assert result["status"] == "dry_run"
    assert result["would_publish"] == [KnowledgeSourceService.source_id_for(proposal)]
    assert pack_path.read_bytes() == pack_before and index_path.read_bytes() == index_before
    session.refresh(proposal)
    assert proposal.status == "APPROVED"


def test_publishing_never_silently_drops_semantic_embeddings(api_client, tmp_path, monkeypatch) -> None:
    client, session = api_client
    pack, index = tmp_path / "sources.json", tmp_path / "knowledge_index.json"
    shutil.copy2(REAL_PACK, pack)
    shutil.copy2(REAL_INDEX, index)  # the committed index carries semantic embeddings
    monkeypatch.setattr(knowledge_module, "SOURCE_PACK_PATH", pack)
    monkeypatch.setattr(knowledge_module, "INDEX_PATH", index)
    pack_before = pack.read_bytes()
    _approved(client, session)

    with pytest.raises(ValueError, match="--semantic"):
        KnowledgeSourceService.publish(session, semantic_embeddings=False)
    assert pack.read_bytes() == pack_before

    # A dry run still works - it writes nothing - and says --semantic will be needed.
    preview = KnowledgeSourceService.publish(session, dry_run=True)
    assert preview["status"] == "dry_run" and preview["requires_semantic"] is True
    assert pack.read_bytes() == pack_before


def test_a_failed_rebuild_restores_the_pack_and_index(api_client, temp_corpus, monkeypatch) -> None:
    client, session = api_client
    pack_path, index_path = temp_corpus
    pack_before, index_before = pack_path.read_bytes(), index_path.read_bytes()
    proposal, gap = _approved(client, session)

    def explode(*args, **kwargs):
        raise RuntimeError("index rebuild failed")

    monkeypatch.setattr(knowledge_module, "rebuild_index", explode)
    with pytest.raises(RuntimeError):
        KnowledgeSourceService.publish(session)
    assert pack_path.read_bytes() == pack_before and index_path.read_bytes() == index_before
    session.refresh(proposal)
    session.refresh(gap)
    assert proposal.status == "APPROVED" and gap.status == "REVIEWED"


def test_the_committed_corpus_files_were_not_touched_by_these_tests() -> None:
    assert knowledge_module.SOURCE_PACK_PATH == REAL_PACK
    assert Path(REAL_PACK).exists() and Path(REAL_INDEX).exists()
