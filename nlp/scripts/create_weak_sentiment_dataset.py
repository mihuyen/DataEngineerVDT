"""Create an auditable three-class weak-label dataset from Silver news.

The output keeps model and lexicon decisions separately. Only rows where the
PhoBERT prediction is confident and agrees with the financial lexicon are put
in the training-ready subset; all other rows remain in the review queue.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from underthesea import word_tokenize


DEFAULT_MODEL = "wonrax/phobert-base-vietnamese-sentiment"
LABEL_ALIASES = {
    "neg": "negative",
    "negative": "negative",
    "neu": "neutral",
    "neutral": "neutral",
    "pos": "positive",
    "positive": "positive",
}

POSITIVE_TERMS = {
    "bứt phá", "cao kỷ lục", "cải thiện", "chia cổ tức", "đạt đỉnh",
    "đột biến", "hồi phục", "khởi sắc", "lãi", "lợi nhuận", "mở rộng",
    "phục hồi", "tăng mạnh", "tăng trưởng", "tích cực", "trúng thầu",
    "vượt kế hoạch",
}
NEGATIVE_TERMS = {
    "bắt tạm giam", "cảnh báo", "đình chỉ", "giảm mạnh", "khởi tố", "lỗ",
    "lao dốc", "nợ xấu", "phạt", "rủi ro", "sụt giảm", "tiêu cực",
    "thua lỗ", "truy tố", "bán tháo", "hủy niêm yết",
}


def lexicon_label(text: str) -> tuple[str, float]:
    normalized = text.casefold()
    positive = sum(term in normalized for term in POSITIVE_TERMS)
    negative = sum(term in normalized for term in NEGATIVE_TERMS)
    total = positive + negative
    if total == 0 or positive == negative:
        return "neutral", 0.0
    score = (positive - negative) / total
    return ("positive" if score > 0 else "negative"), score


def load_articles(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    required = {"article_id", "publisher", "title", "raw_content"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    return frame.drop_duplicates(subset=["article_id"], keep="last").reset_index(drop=True)


def predict(
    texts: list[str], model_repo: str, batch_size: int
) -> tuple[list[str], list[float]]:
    tokenizer = AutoTokenizer.from_pretrained(model_repo, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_repo, trust_remote_code=False
    ).eval()
    id2label = {
        int(label_id): LABEL_ALIASES.get(str(label).casefold(), str(label).casefold())
        for label_id, label in model.config.id2label.items()
    }

    labels: list[str] = []
    confidences: list[float] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        encoded = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )
        with torch.no_grad():
            probabilities = torch.softmax(model(**encoded).logits, dim=-1)
        prediction_ids = probabilities.argmax(dim=-1).tolist()
        labels.extend(id2label[prediction_id] for prediction_id in prediction_ids)
        confidences.extend(float(value) for value in probabilities.max(dim=-1).values)
    return labels, confidences


def create_dataset(
    input_path: Path,
    output_dir: Path,
    model_repo: str,
    confidence_threshold: float,
    batch_size: int,
) -> dict:
    frame = load_articles(input_path)
    raw_texts = [
        f"Tiêu đề: {title}\n\n{content[:800]}"
        for title, content in zip(
            frame["title"].fillna(""), frame["raw_content"].fillna("")
        )
    ]
    segmented_texts = [word_tokenize(text, format="text") for text in raw_texts]
    model_labels, model_confidences = predict(segmented_texts, model_repo, batch_size)
    lexicon_results = [lexicon_label(text) for text in raw_texts]

    frame["text"] = raw_texts
    frame["model_label"] = model_labels
    frame["model_confidence"] = model_confidences
    frame["lexicon_label"] = [result[0] for result in lexicon_results]
    frame["lexicon_score"] = [result[1] for result in lexicon_results]
    frame["label_agreement"] = frame["model_label"] == frame["lexicon_label"]
    frame["sentiment_label"] = frame["model_label"]
    frame["label_source"] = "weak_phobert_lexicon"
    frame["review_required"] = ~(
        frame["label_agreement"]
        & (frame["model_confidence"] >= confidence_threshold)
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_dir / "weak_labels_all.parquet", index=False)
    frame.to_csv(output_dir / "weak_labels_all.csv", index=False, encoding="utf-8-sig")

    accepted = frame[~frame["review_required"]].copy()
    review = frame[frame["review_required"]].copy()
    candidate_records = accepted[
        ["article_id", "publisher", "source_url", "text", "sentiment_label"]
    ].rename(columns={"sentiment_label": "label"})
    candidate_records.to_json(
        output_dir / "high_confidence_candidates.json",
        orient="records",
        force_ascii=False,
        indent=2,
    )
    review.to_csv(output_dir / "review_queue.csv", index=False, encoding="utf-8-sig")

    summary = {
        "model_repo": model_repo,
        "confidence_threshold": confidence_threshold,
        "total": len(frame),
        "high_confidence_candidates": len(accepted),
        "review_required": len(review),
        "all_label_distribution": frame["sentiment_label"].value_counts().to_dict(),
        "accepted_label_distribution": accepted["sentiment_label"].value_counts().to_dict(),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", default="data/nlp_dataset/articles_unlabeled.parquet", type=Path
    )
    parser.add_argument("--output-dir", default="data/nlp_dataset/weak_labels", type=Path)
    parser.add_argument("--model-repo", default=DEFAULT_MODEL)
    parser.add_argument("--confidence-threshold", default=0.9, type=float)
    parser.add_argument("--batch-size", default=16, type=int)
    args = parser.parse_args()
    summary = create_dataset(
        args.input,
        args.output_dir,
        args.model_repo,
        args.confidence_threshold,
        args.batch_size,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
