"""Work out which crime this is when the keyword lexicon cannot.

The lexicon in ``UnderstandingEngine.classify_domain`` is nearly blind: across
twenty realistic phrasings it answered five and returned ``unknown`` for fifteen.
It is mostly precise, but not always - on held-out wording its money keywords
hijack the domain, so "he recorded me on video call and now demands money" comes
back as financial fraud rather than sextortion. An unknown domain has no question flow and no retrieval filter, so
the citizen is told "मुझे स्पष्ट नहीं है कि क्या हुआ" and the conversation loops
without ever starting. "एक आदमी मुझे WhatsApp पर गंदे मैसेज भेज रहा है" is a
perfectly clear harassment report; it simply avoids the word परेशान.

So this adds recall without spending that precision:

* the lexicon still decides first, instantly and offline;
* only when it says unknown is a hosted embedding consulted;
* the answer is kept for the incident, so it costs about one call per
  conversation rather than one per turn;
* with no provider configured it returns None and nothing changes.

Domains are matched against *centroids of citizen phrasings* rather than the
domain name, because "someone keeps sending me filthy messages" is close to how
people write and nowhere near the words "online harassment".
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.cyber_saathi import CrimeDomain
from app.services.cyber_saathi_semantic_embeddings import (
    GeminiSemanticEmbeddingProvider,
    SemanticEmbeddingError,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "cyber_saathi"
EXEMPLARS_PATH = DATA_DIR / "domain_exemplars.json"
CENTROIDS_PATH = DATA_DIR / "domain_centroids.json"

# Thresholds are measured, not chosen. Across off-topic messages ("banana bread
# recipe", "मुझे नौकरी चाहिए") the best domain never scored above 0.695, while real
# reports ran 0.727 to 0.915.
#
# Below this, the message is not about any of these crimes.
MIN_SIMILARITY = 0.70
# Above this the reading is strong enough to correct the lexicon. That matters
# because the lexicon's failures are confident ones: "he recorded me on video
# call and now demands money" is sextortion, but the money words route it to
# financial fraud. Where the lexicon was right, the embedding agreed with it on
# every case measured, so overriding costs nothing there.
OVERRIDE_SIMILARITY = 0.75
# Deliberately small. The remaining near-ties are between adjacent domains -
# phishing against malware, harassment against cyberstalking - where either
# answer gives usable guidance, and "unknown" gives none and loops forever.
MIN_MARGIN = 0.004


def _cosine(left: list[float], right: list[float]) -> float:
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right))))


def _normalise(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        raise SemanticEmbeddingError("zero vector")
    return [value / magnitude for value in vector]


def build_centroids(provider: GeminiSemanticEmbeddingProvider | None = None) -> dict[str, Any]:
    """Embed every exemplar and average per domain. Build-time only."""
    provider = provider or GeminiSemanticEmbeddingProvider()
    payload = json.loads(EXEMPLARS_PATH.read_text(encoding="utf-8"))
    centroids: dict[str, list[float]] = {}
    for domain, phrases in payload["exemplars"].items():
        vectors = [
            provider.embed(phrase, task_type="RETRIEVAL_QUERY", timeout_seconds=20.0)
            for phrase in phrases
        ]
        summed = [sum(values) / len(values) for values in zip(*vectors)]
        centroids[domain] = [round(value, 8) for value in _normalise(summed)]
    return {
        "version": payload["version"],
        "provider": provider.provider,
        "model": provider.model,
        "dimension": provider.dimensions,
        "centroids": centroids,
    }


@lru_cache(maxsize=1)
def _load_centroids() -> dict[str, Any] | None:
    if not CENTROIDS_PATH.exists():
        return None
    try:
        return json.loads(CENTROIDS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def clear_cache() -> None:
    _load_centroids.cache_clear()


def classify_semantically(
    message: str, *, lexicon_confident: bool = False
) -> CrimeDomain | None:
    """Best-matching crime domain, or None when it cannot be decided safely.

    ``lexicon_confident`` says the keyword pass already produced a domain. The
    embedding then has to clear a higher bar before it is allowed to disagree.
    """
    index = _load_centroids()
    if not index or not message.strip():
        return None
    provider = GeminiSemanticEmbeddingProvider()
    if not provider.configured or provider.model != index.get("model"):
        return None
    try:
        query = provider.query_embedding(message)
    except SemanticEmbeddingError:
        return None
    if len(query) != index.get("dimension"):
        return None

    scored: list[tuple[float, str]] = []
    for domain, centroid in index["centroids"].items():
        if len(centroid) == len(query):
            scored.append((_cosine(query, centroid), domain))
    if not scored:
        return None
    scored.sort(reverse=True)
    best_score, best_domain = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    if best_score < MIN_SIMILARITY or (best_score - runner_up) < MIN_MARGIN:
        return None
    if lexicon_confident and best_score < OVERRIDE_SIMILARITY:
        return None
    try:
        return CrimeDomain(best_domain)
    except ValueError:
        return None


def main() -> None:
    result = build_centroids()
    CENTROIDS_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    clear_cache()
    print(
        json.dumps(
            {
                "status": "passed",
                "path": str(CENTROIDS_PATH),
                "domains": len(result["centroids"]),
                "dimension": result["dimension"],
                "bytes": CENTROIDS_PATH.stat().st_size,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
