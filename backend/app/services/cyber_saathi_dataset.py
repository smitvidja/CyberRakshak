import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.cyber_saathi import CrimeDomain, Intent, LanguageCode, Sentiment, Urgency
from app.services.cyber_saathi_understanding import DATA_DIR


class NormalizedExample(BaseModel):
    source_example_id: str = Field(min_length=1)
    original_text: str = Field(min_length=1)
    variant_text: str = Field(min_length=1)
    language: LanguageCode
    script: Literal["LATIN", "DEVANAGARI", "DEVANAGARI_MIXED"]
    transformation_method: Literal[
        "original_manual",
        "controlled_english_variant",
        "controlled_hindi_adaptation",
        "controlled_hinglish_adaptation",
    ]
    source_dataset: str = Field(min_length=1)
    quality_status: Literal["reviewed", "rejected"]
    split: Literal["support", "evaluation"]
    intent: Intent
    crime_domain: CrimeDomain
    urgency: Urgency
    sentiment: Sentiment


def load_registry() -> dict[str, object]:
    return json.loads((DATA_DIR / "dataset_registry.json").read_text(encoding="utf-8"))


def load_examples() -> list[NormalizedExample]:
    rows = json.loads((DATA_DIR / "source_examples.json").read_text(encoding="utf-8"))
    return [NormalizedExample.model_validate(row) for row in rows]


def prepare_examples() -> dict[str, list[NormalizedExample]]:
    examples = load_examples()
    deduplicated: dict[str, NormalizedExample] = {}
    source_splits: dict[str, str] = {}
    for example in examples:
        normalized_text = " ".join(example.variant_text.casefold().split())
        deduplicated.setdefault(normalized_text, example)
        existing_split = source_splits.setdefault(example.source_example_id, example.split)
        if existing_split != example.split:
            raise ValueError(
                f"Source example {example.source_example_id} leaks across support/evaluation splits"
            )
    return {
        "support": [row for row in deduplicated.values() if row.split == "support"],
        "evaluation": [row for row in deduplicated.values() if row.split == "evaluation"],
    }


def validate_registry() -> None:
    registry = load_registry()
    datasets = registry.get("datasets", [])
    required = {
        "name", "location", "purpose", "schema", "domain", "allowed_usage",
        "rag_allowed", "evaluation_allowed", "training_allowed", "known_limitations",
    }
    for dataset in datasets:
        missing = required.difference(dataset)
        if missing:
            raise ValueError(f"Dataset registry entry is missing {sorted(missing)}")
    by_name = {dataset["name"]: dataset for dataset in datasets}
    if by_name["Bitext 27K customer-support dataset"]["availability"] != "excluded":
        raise ValueError("Bitext 27K must remain excluded")
    if by_name["cybermetric 10K validation"]["training_allowed"]:
        raise ValueError("cybermetric validation must remain held out")
    if not by_name["Authoritative citizen knowledge corpus"]["rag_allowed"]:
        raise ValueError("The separate authoritative corpus must own future RAG usage")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and normalize Cyber Saathi fixtures")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    validate_registry()
    prepared = prepare_examples()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        rows = [row.model_dump(mode="json") for split in prepared.values() for row in split]
        args.output.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "status": "passed",
                "support_examples": len(prepared["support"]),
                "evaluation_examples": len(prepared["evaluation"]),
            }
        )
    )


if __name__ == "__main__":
    main()
