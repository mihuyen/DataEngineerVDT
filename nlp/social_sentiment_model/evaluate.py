"""Evaluate a ViSoBERT social sentiment checkpoint on a locked test split."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from nlp.social_sentiment_model.dataset import ID2LABEL, NUM_LABELS, SocialSentimentDataset


logger = logging.getLogger(__name__)
DEFAULT_CHECKPOINT = "./checkpoints/social_sentiment/best_model"
DEFAULT_REPORT_PATH = "evaluation_report_social_sentiment.json"


def _print_confusion_matrix(cm: np.ndarray, label_names: list[str]) -> None:
    header = f"{'':>12}" + "".join(f"{name:>12}" for name in label_names)
    print(header)
    for i, row_label in enumerate(label_names):
        print(f"{row_label:>12}" + "".join(f"{cm[i][j]:>12}" for j in range(len(label_names))))


def evaluate(
    model_path: str,
    test_path: str,
    report_path: str = DEFAULT_REPORT_PATH,
) -> dict:
    model_source = model_path or os.getenv(
        "HF_SOCIAL_SENTIMENT_MODEL_REPO",
        os.getenv("SOCIAL_SENTIMENT_MODEL_PATH", DEFAULT_CHECKPOINT),
    )
    logger.info("Loading social sentiment model from %s", model_source)
    tokenizer = AutoTokenizer.from_pretrained(model_source)
    model = AutoModelForSequenceClassification.from_pretrained(model_source)
    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    with open(test_path, encoding="utf-8") as f:
        test_records = json.load(f)
    test_dataset = SocialSentimentDataset(test_records, tokenizer)
    loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

    all_preds: list[int] = []
    all_labels: list[int] = []
    with torch.no_grad():
        for batch in loader:
            outputs = model(
                input_ids=batch["input_ids"].to(device),
                attention_mask=batch["attention_mask"].to(device),
            )
            preds = torch.argmax(outputs.logits, dim=-1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(batch["labels"].numpy())

    y_true = np.array(all_labels)
    y_pred = np.array(all_preds)
    label_names = [ID2LABEL[i] for i in range(NUM_LABELS)]
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    per_class_f1 = f1_score(y_true, y_pred, average=None, zero_division=0)
    cm = confusion_matrix(y_true, y_pred)

    print("\n" + "=" * 70)
    print("SOCIAL SENTIMENT EVALUATION REPORT")
    print("=" * 70)
    print(f"Model: {model_source}")
    print(f"Test samples: {len(y_true)}")
    print(f"Accuracy   : {acc:.4f}")
    print(f"Macro F1   : {macro_f1:.4f}")
    print(f"Weighted F1: {weighted_f1:.4f}")
    print("\nCLASSIFICATION REPORT:")
    print(classification_report(y_true, y_pred, target_names=label_names, digits=4))
    print("CONFUSION MATRIX:")
    _print_confusion_matrix(cm, label_names)
    print("=" * 70)

    report = {
        "model_source": model_source,
        "test_path": test_path,
        "num_samples": len(y_true),
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
        "per_class_f1": {
            label_names[i]: round(float(per_class_f1[i]), 4)
            for i in range(NUM_LABELS)
        },
    }
    out = Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info("Saved report to %s", report_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate social sentiment model.")
    parser.add_argument("--model-path", default=os.getenv("SOCIAL_SENTIMENT_MODEL_PATH", DEFAULT_CHECKPOINT))
    parser.add_argument("--test-path", required=True)
    parser.add_argument("--report-path", default=os.getenv("SOCIAL_SENTIMENT_EVAL_REPORT", DEFAULT_REPORT_PATH))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    evaluate(args.model_path, args.test_path, args.report_path)


if __name__ == "__main__":
    main()
