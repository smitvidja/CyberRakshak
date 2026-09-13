"""Cyber Saathi's paid endpoints refuse a flood.

Every endpoint covered here is unauthenticated, publicly reachable, and spends
money per call - the LLM gateway for a message, Sarvam for speech, hosted
embeddings for a knowledge search. Before this they had no limit at all, so one
script could run up the bill or exhaust the day's quota and take Cyber Saathi
down for every citizen using it.

These tests exist because a limiter nobody tests is a limiter that quietly stops
working the next time a handler signature changes.
"""
from fastapi.testclient import TestClient

from app.core.public_rate_limit import (
    saathi_analysis_burst_rate_limiter,
    saathi_message_burst_rate_limiter,
    saathi_start_rate_limiter,
)
from app.main import app


def _start_conversation(client: TestClient) -> dict:
    started = client.post("/api/v1/cyber-saathi/conversations", json={"language": "EN"})
    assert started.status_code == 201
    return started.json()["data"]["state"]


def test_starting_conversations_in_a_flood_is_refused() -> None:
    client = TestClient(app)
    limit = saathi_start_rate_limiter.limit

    for attempt in range(limit):
        response = client.post("/api/v1/cyber-saathi/conversations", json={"language": "EN"})
        assert response.status_code == 201, f"call {attempt + 1} of {limit} should be allowed"

    refused = client.post("/api/v1/cyber-saathi/conversations", json={"language": "EN"})
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "RATE_LIMITED"


def test_a_flood_of_messages_is_refused_before_it_reaches_the_model() -> None:
    """The expensive path: every one of these would otherwise be a paid call."""
    client = TestClient(app)
    state = _start_conversation(client)
    limit = saathi_message_burst_rate_limiter.limit

    for attempt in range(limit):
        response = client.post(
            f"/api/v1/cyber-saathi/conversations/{state['id']}/messages",
            json={"message": "I received a suspicious message", "state": state},
        )
        assert response.status_code == 200, f"message {attempt + 1} of {limit} should be allowed"
        state = response.json()["data"]["state"]

    refused = client.post(
        f"/api/v1/cyber-saathi/conversations/{state['id']}/messages",
        json={"message": "I received a suspicious message", "state": state},
    )
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "RATE_LIMITED"


def test_knowledge_search_is_metered_too() -> None:
    """Each search embeds the query with a hosted model, so it is not free either."""
    client = TestClient(app)
    limit = saathi_analysis_burst_rate_limiter.limit

    for attempt in range(limit):
        response = client.post(
            "/api/v1/cyber-saathi/knowledge/search",
            json={"query": "upi fraud", "top_k": 3},
        )
        assert response.status_code == 200, f"search {attempt + 1} of {limit} should be allowed"

    refused = client.post(
        "/api/v1/cyber-saathi/knowledge/search",
        json={"query": "upi fraud", "top_k": 3},
    )
    assert refused.status_code == 429


def test_a_citizen_having_a_real_conversation_is_never_refused() -> None:
    """The limit has to be invisible to the person this service exists for.

    A distressed citizen sends several messages in quick succession; that must
    never be mistaken for abuse. This pins the budget as comfortably above a real
    exchange, so anyone tightening it later has to break this test on purpose.
    """
    assert saathi_message_burst_rate_limiter.limit >= 10
    assert saathi_start_rate_limiter.limit >= 3

    client = TestClient(app)
    state = _start_conversation(client)
    for _ in range(6):
        response = client.post(
            f"/api/v1/cyber-saathi/conversations/{state['id']}/messages",
            json={"message": "Someone is threatening me online", "state": state},
        )
        assert response.status_code == 200
        state = response.json()["data"]["state"]
