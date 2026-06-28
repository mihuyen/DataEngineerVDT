"""
prepare_vietsentiwordnet.py -- Prepare external Vietnamese sentiment resources.

This script keeps the three-class sentiment contract unchanged:

  positive -> positive
  negative -> negative
  neutral  -> neutral

It also parses the VietSentiWordnet lexicon into JSON for later weak-labeling or
feature work, but does not mix single-word lexicon entries into the supervised
training set by default.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


DEFAULT_EXTERNAL_DIR = Path("data/external/vietnamese_sentiment_analysis")
DEFAULT_FINTA_TRAIN = Path("data/splits/train.json")
DEFAULT_OUTPUT_TRAIN = Path("data/splits/train_augmented_vietsenti.json")
DEFAULT_METADATA = Path("data/splits/train_augmented_vietsenti.metadata.json")
RANDOM_STATE = 42


CORPUS_FILES = {
    "positive": ("train_positive_tokenized.txt", "positive", 0.65),
    "negative": ("train_negative_tokenized.txt", "negative", -0.65),
    "neutral": ("train_neutral_tokenized.txt", "neutral", 0.0),
}


def _read_json(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _iter_non_empty_lines(path: Path) -> Iterable[str]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            text = " ".join(line.replace("\ufeff", "").split())
            if text:
                yield text


def parse_vietsentiwordnet(lexicon_path: Path) -> list[dict]:
    """Parse the tab-separated VietSentiWordnet file into structured records."""
    entries: list[dict] = []
    if not lexicon_path.exists():
        return entries

    for line_no, line in enumerate(lexicon_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 6:
            continue

        pos, synset_id, pos_score, neg_score, terms, gloss = parts[:6]
        try:
            pos_value = float(pos_score)
            neg_value = float(neg_score)
        except ValueError:
            continue

        clean_terms = [term.split("#", 1)[0] for term in terms.split() if term]
        polarity = pos_value - neg_value
        entries.append(
            {
                "line_no": line_no,
                "pos": pos,
                "synset_id": synset_id,
                "pos_score": pos_value,
                "neg_score": neg_value,
                "polarity": round(polarity, 4),
                "terms": clean_terms,
                "gloss": gloss,
            }
        )

    return entries


def build_external_records(
    external_dir: Path,
    max_per_label: int,
    seed: int,
) -> list[dict]:
    """Convert the 3-class external corpus to FiNTA-shaped records."""
    rng = random.Random(seed)
    records: list[dict] = []

    for source_label, (filename, finta_label, sentiment_score) in CORPUS_FILES.items():
        source_path = external_dir / filename
        if not source_path.exists():
            raise FileNotFoundError(f"Missing external corpus file: {source_path}")

        lines = list(_iter_non_empty_lines(source_path))
        rng.shuffle(lines)
        if max_per_label > 0:
            lines = lines[:max_per_label]

        for idx, text in enumerate(lines, start=1):
            records.append(
                {
                    "article_id": f"vietsenti-{source_label}-{idx:05d}",
                    "source_url": "https://github.com/NLP-Projects/Vietnamese-Sentiment-Analysis",
                    "publisher": "Vietnamese-Sentiment-Analysis",
                    "title": "",
                    "raw_content": text,
                    "sentiment_label": finta_label,
                    "sentiment_score": sentiment_score,
                    "confidence": 0.85,
                    "impact_label": "None",
                    "impact_score": 0.0,
                    "topics": ["Khác"],
                    "topic_distribution": {
                        "Chính sách tiền tệ": 0.0,
                        "Kết quả kinh doanh": 0.0,
                        "M&A": 0.0,
                        "Biến động vĩ mô": 0.0,
                        "Tin đồn thị trường": 0.0,
                        "Khác": 1.0,
                    },
                    "reasoning": (
                        "Mapped from external 3-class Vietnamese sentiment corpus; "
                        f"source_label={source_label}."
                    ),
                    "is_external": True,
                    "external_source": "NLP-Projects/Vietnamese-Sentiment-Analysis",
                    "external_original_label": source_label,
                }
            )

    rng.shuffle(records)
    return records


def prepare(
    external_dir: Path,
    finta_train_path: Path,
    output_train_path: Path,
    metadata_path: Path,
    max_per_label: int,
    seed: int,
) -> dict:
    """Create the augmented train split and parsed lexicon sidecar."""
    finta_records = _read_json(finta_train_path)
    external_records = build_external_records(external_dir, max_per_label=max_per_label, seed=seed)

    augmented = list(finta_records) + external_records
    random.Random(seed).shuffle(augmented)
    _write_json(output_train_path, augmented)

    lexicon_path = external_dir / "VietSentiWordnet"
    lexicon_entries = parse_vietsentiwordnet(lexicon_path)
    parsed_lexicon_path = external_dir / "VietSentiWordnet.parsed.json"
    if lexicon_entries:
        _write_json(parsed_lexicon_path, lexicon_entries)

    label_counts = Counter(row.get("sentiment_label", "UNKNOWN") for row in augmented)
    metadata = {
        "created_date": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "base_train_path": str(finta_train_path),
        "output_train_path": str(output_train_path),
        "external_source": "https://github.com/NLP-Projects/Vietnamese-Sentiment-Analysis",
        "external_records": len(external_records),
        "base_records": len(finta_records),
        "total_records": len(augmented),
        "max_per_external_label": max_per_label,
        "random_state": seed,
        "label_mapping": {
            "positive": "positive",
            "negative": "negative",
            "neutral": "neutral",
        },
        "label_distribution": dict(label_counts),
        "lexicon_path": str(lexicon_path),
        "parsed_lexicon_path": str(parsed_lexicon_path) if lexicon_entries else None,
        "note": (
            "Validation and test splits are intentionally unchanged. "
            "Use this train split for additional fine-tuning, then evaluate on the locked FiNTA test set."
        ),
    }
    _write_json(metadata_path, metadata)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare VietSentiWordnet resources for FiNTA fine-tuning.")
    parser.add_argument("--external-dir", type=Path, default=DEFAULT_EXTERNAL_DIR)
    parser.add_argument("--finta-train", type=Path, default=DEFAULT_FINTA_TRAIN)
    parser.add_argument("--output-train", type=Path, default=DEFAULT_OUTPUT_TRAIN)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument(
        "--max-per-label",
        type=int,
        default=800,
        help="Maximum external examples per positive/negative/neutral label. Use 0 for all.",
    )
    parser.add_argument("--seed", type=int, default=RANDOM_STATE)
    args = parser.parse_args()

    metadata = prepare(
        external_dir=args.external_dir,
        finta_train_path=args.finta_train,
        output_train_path=args.output_train,
        metadata_path=args.metadata,
        max_per_label=args.max_per_label,
        seed=args.seed,
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
