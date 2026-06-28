"""
evaluate.py — Đánh giá PhoBERT trên test set (chạy 1 lần duy nhất).

Input:  Model checkpoint hoặc HuggingFace Hub, data/splits/test.json
Output: evaluation_report.json, in kết quả ra console.

CẢNH BÁO: Chỉ chạy file này 1 lần sau khi training hoàn toàn xong.
Không được dùng kết quả để điều chỉnh hyperparameter.
"""

import json
import logging
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from torch.utils.data import DataLoader

from nlp.sentiment_model.dataset import (
    ID2LABEL,
    LABEL2ID,
    NUM_LABELS,
    FintaSentimentDataset,
)

logger = logging.getLogger(__name__)

SLA_ACCURACY = 0.80
SLA_MACRO_F1 = 0.78

DEFAULT_TEST_PATH = "data/splits/test.json"
DEFAULT_CHECKPOINT = "./checkpoints/sentiment/best_model"
DEFAULT_REPORT_PATH = "evaluation_report.json"


def _load_records(json_path: str) -> list:
    with open(json_path, encoding="utf-8") as f:
        rows = json.load(f)
    return [
        {
            "text": f"Tiêu đề: {r.get('title', '')}\n\n{r.get('raw_content', '')}",
            "label": r["sentiment_label"],
        }
        for r in rows
    ]


def _print_confusion_matrix(cm: np.ndarray, label_names: list) -> None:
    """In confusion matrix dạng text, không cần matplotlib."""
    header = f"{'':>14}" + "".join(f"{n:>14}" for n in label_names)
    print(header)
    for i, row_label in enumerate(label_names):
        row_str = f"{row_label:>14}" + "".join(f"{cm[i][j]:>14}" for j in range(len(label_names)))
        print(row_str)


def evaluate(
    model_path: str = None,
    test_path: str = DEFAULT_TEST_PATH,
    report_path: str = DEFAULT_REPORT_PATH,
) -> dict:
    """
    Đánh giá model trên test set và lưu báo cáo.

    Args:
        model_path:  Đường dẫn checkpoint local hoặc HF repo ID. None → dùng default.
        test_path:   Đường dẫn test.json.
        report_path: Đường dẫn lưu evaluation_report.json.

    Returns:
        Dict kết quả metrics.
    """
    model_source = model_path or os.getenv(
        "HF_MODEL_REPO",
        os.getenv("SENTIMENT_MODEL_PATH", DEFAULT_CHECKPOINT),
    )

    logger.info("Tải model từ: %s", model_source)
    tokenizer = AutoTokenizer.from_pretrained(model_source)
    model = AutoModelForSequenceClassification.from_pretrained(model_source)
    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    logger.info("Tải test set: %s", test_path)
    test_records = _load_records(test_path)
    test_dataset = FintaSentimentDataset(test_records, tokenizer)
    loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"]

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = torch.argmax(outputs.logits, dim=-1).cpu().numpy()

            all_preds.extend(preds)
            all_labels.extend(labels.numpy())

    y_true = np.array(all_labels)
    y_pred = np.array(all_preds)

    label_names = [ID2LABEL[i] for i in range(NUM_LABELS)]

    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    per_class_f1 = f1_score(y_true, y_pred, average=None, zero_division=0)

    cm = confusion_matrix(y_true, y_pred)

    print("\n" + "=" * 70)
    print("EVALUATION REPORT — TEST SET (chạy 1 lần duy nhất)")
    print("=" * 70)
    print(f"\nModel: {model_source}")
    print(f"Test samples: {len(y_true)}\n")

    print("OVERALL METRICS:")
    print(f"  Accuracy   : {acc:.4f}")
    print(f"  Macro F1   : {macro_f1:.4f}")
    print(f"  Weighted F1: {weighted_f1:.4f}")

    print("\nCLASSIFICATION REPORT:")
    print(classification_report(y_true, y_pred, target_names=label_names, digits=4))

    print("CONFUSION MATRIX:")
    _print_confusion_matrix(cm, label_names)

    print("\nSLA CHECK:")
    acc_pass = acc >= SLA_ACCURACY
    f1_pass = macro_f1 >= SLA_MACRO_F1
    print(f"  Accuracy >= {SLA_ACCURACY}: {acc:.4f} → {'PASS ✓' if acc_pass else 'FAIL ✗'}")
    print(f"  Macro F1 >= {SLA_MACRO_F1}: {macro_f1:.4f} → {'PASS ✓' if f1_pass else 'FAIL ✗'}")
    overall = "PASS" if (acc_pass and f1_pass) else "FAIL"
    print(f"\n  OVERALL: {overall}")
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
        "sla": {
            "accuracy_target": SLA_ACCURACY,
            "macro_f1_target": SLA_MACRO_F1,
            "accuracy_pass": acc_pass,
            "macro_f1_pass": f1_pass,
            "overall": overall,
        },
    }

    out = Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info("Báo cáo đã lưu tại: %s", report_path)

    return report


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Evaluate FiNTA PhoBERT sentiment model.")
    parser.add_argument(
        "--model-path",
        default=os.getenv("HF_MODEL_REPO", os.getenv("SENTIMENT_MODEL_PATH", DEFAULT_CHECKPOINT)),
        help="Local checkpoint directory or HuggingFace repo ID.",
    )
    parser.add_argument("--test-path", default=DEFAULT_TEST_PATH)
    parser.add_argument("--report-path", default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()
    evaluate(model_path=args.model_path, test_path=args.test_path, report_path=args.report_path)
