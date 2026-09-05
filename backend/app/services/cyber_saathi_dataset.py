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


class ControlledVariant(BaseModel):
    variant_text: str = Field(min_length=1)
    language: LanguageCode
    script: Literal["LATIN", "DEVANAGARI", "DEVANAGARI_MIXED"]
    transformation_method: Literal[
        "original_manual",
        "controlled_english_variant",
        "controlled_hindi_adaptation",
        "controlled_hinglish_adaptation",
    ]
    quality_status: Literal["reviewed", "rejected"]


class LanguageSource(BaseModel):
    source_example_id: str = Field(min_length=1)
    original_text: str = Field(min_length=1)
    source_dataset: str = Field(min_length=1)
    split: Literal["support", "evaluation"]
    intent: Intent
    crime_domain: CrimeDomain
    urgency: Urgency
    sentiment: Sentiment
    selected_for: list[str] = Field(min_length=1)
    variants: list[ControlledVariant] = Field(min_length=1)


def load_registry() -> dict[str, object]:
    return json.loads((DATA_DIR / "dataset_registry.json").read_text(encoding="utf-8"))


def load_inspection() -> dict[str, object]:
    return json.loads((DATA_DIR / "dataset_inspection.json").read_text(encoding="utf-8"))


def load_sources() -> list[LanguageSource]:
    rows = json.loads((DATA_DIR / "language_sources.json").read_text(encoding="utf-8"))
    return [LanguageSource.model_validate(row) for row in rows]


def generate_controlled_variants(
    sources: list[LanguageSource] | None = None,
) -> list[NormalizedExample]:
    generated: list[NormalizedExample] = []
    for source in sources or load_sources():
        languages = {variant.language for variant in source.variants if variant.quality_status == "reviewed"}
        if languages != {LanguageCode.EN, LanguageCode.HI, LanguageCode.HINGLISH}:
            raise ValueError(
                f"Source {source.source_example_id} must have reviewed EN, HI, and HINGLISH variants"
            )
        for variant in source.variants:
            if variant.quality_status != "reviewed":
                continue
            generated.append(
                NormalizedExample(
                    source_example_id=source.source_example_id,
                    original_text=source.original_text,
                    variant_text=" ".join(variant.variant_text.split()),
                    language=variant.language,
                    script=variant.script,
                    transformation_method=variant.transformation_method,
                    source_dataset=source.source_dataset,
                    quality_status=variant.quality_status,
                    split=source.split,
                    intent=source.intent,
                    crime_domain=source.crime_domain,
                    urgency=source.urgency,
                    sentiment=source.sentiment,
                )
            )
    return generated


def prepare_examples() -> dict[str, list[NormalizedExample]]:
    examples = generate_controlled_variants()
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
    inspection = load_inspection()
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
    if not by_name["Bitext 27K customer-support dataset"]["availability"].endswith("excluded"):
        raise ValueError("Bitext 27K must remain excluded")
    if by_name["cybermetric 10K validation"]["training_allowed"]:
        raise ValueError("cybermetric validation must remain held out")
    if not by_name["Authoritative citizen knowledge corpus"]["rag_allowed"]:
        raise ValueError("The separate authoritative corpus must own future RAG usage")
    inspected = inspection.get("datasets", [])
    if len(inspected) != 9:
        raise ValueError("All nine discovered external datasets must remain inspected")
    for dataset in inspected:
        if dataset.get("rows", 0) <= 0 or len(dataset.get("sha256", "")) != 64:
            raise ValueError(f"Incomplete inspection evidence for {dataset.get('id', 'unknown')}")
        if not dataset.get("schema") or not dataset.get("decision"):
            raise ValueError(f"Missing schema or decision for {dataset.get('id', 'unknown')}")


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
