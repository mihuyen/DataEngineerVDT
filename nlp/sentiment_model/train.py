"""
train.py — Fine-tune PhoBERT cho phân loại cảm xúc tài chính (3 nhãn).

Thiết kế để chạy trên Google Colab với GPU T4.
Input:  data/splits/train.json, data/splits/val.json
Output: checkpoints/sentiment/best_model/

SLA mục tiêu:
  accuracy >= 0.80
  macro_f1  >= 0.78
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
from sklearn.metrics import classification_report, f1_score, accuracy_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from nlp.sentiment_model.dataset import (
    LABEL2ID,
    ID2LABEL,
    NUM_LABELS,
    PHOBERT_BASE,
    FintaSentimentDataset,
    compute_class_weights,
    normalize_label,
    oversample_rare_classes,
)

logger = logging.getLogger(__name__)

# SLA mục tiêu
SLA_ACCURACY = 0.80
SLA_MACRO_F1 = 0.78

CHECKPOINT_DIR = "./checkpoints/sentiment"
BEST_MODEL_DIR = f"{CHECKPOINT_DIR}/best_model"


def _load_records(json_path: str) -> list:
    """Đọc JSON và chuẩn bị list records {text, label}."""
    with open(json_path, encoding="utf-8") as f:
        df_records = json.load(f)

    records = []
    for row in df_records:
        text = f"Tiêu đề: {row.get('title', '')}\n\n{row.get('raw_content', '')}"
        records.append({"text": text, "label": normalize_label(row["sentiment_label"])})
    return records


def compute_metrics(eval_pred):
    """Tính accuracy, macro_f1, weighted_f1 và F1 từng nhãn."""
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)

    macro_f1 = f1_score(labels, preds, average="macro", zero_division=0)
    weighted_f1 = f1_score(labels, preds, average="weighted", zero_division=0)
    acc = accuracy_score(labels, preds)

    per_class_f1 = f1_score(labels, preds, average=None, zero_division=0)
    f1_per_class = {ID2LABEL[i]: round(float(per_class_f1[i]), 4) for i in range(NUM_LABELS)}

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        **{f"f1_{k}": v for k, v in f1_per_class.items()},
    }


def train(
    train_path: str = "data/splits/train.json",
    val_path: str = "data/splits/val.json",
    base_model: str = None,
    checkpoint_dir: str = None,
    num_train_epochs: float = None,
    learning_rate: float = None,
    warmup_ratio: float = None,
    label_smoothing: float = None,
    oversample_min_count: int = None,
    use_class_weights: bool = None,
    focal_gamma: float = None,
) -> None:
    """
    Chạy fine-tuning PhoBERT.

    Args:
        train_path: Đường dẫn file train.json.
        val_path:   Đường dẫn file val.json.
        base_model:  HF model ID hoặc local checkpoint để tiếp tục fine-tune.
        checkpoint_dir: Thư mục lưu checkpoint mới.
        num_train_epochs: Số epoch training.
    """
    enable_mlflow = os.getenv("ENABLE_MLFLOW", "false").lower() == "true"
    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "finta-sentiment")

    if enable_mlflow:
        import mlflow
        mlflow.set_tracking_uri(mlflow_uri)
        mlflow.set_experiment(experiment_name)
        use_mlflow = True
    else:
        logger.info("MLflow disabled. Set ENABLE_MLFLOW=true to enable experiment logging.")
        use_mlflow = False

    logger.info("Tải dataset...")
    train_records = _load_records(train_path)
    val_records = _load_records(val_path)

    base_model = base_model or os.getenv("SENTIMENT_BASE_MODEL", PHOBERT_BASE)
    checkpoint_dir = checkpoint_dir or os.getenv("SENTIMENT_CHECKPOINT_DIR", CHECKPOINT_DIR)
    best_model_dir = os.getenv("SENTIMENT_BEST_MODEL_DIR", f"{checkpoint_dir}/best_model")
    num_train_epochs = float(num_train_epochs or os.getenv("SENTIMENT_NUM_EPOCHS", "8"))
    learning_rate = float(learning_rate or os.getenv("SENTIMENT_LEARNING_RATE", "1e-5"))
    warmup_ratio = float(warmup_ratio or os.getenv("SENTIMENT_WARMUP_RATIO", "0.15"))
    label_smoothing = float(label_smoothing or os.getenv("SENTIMENT_LABEL_SMOOTHING", "0.05"))
    oversample_min_count = int(oversample_min_count if oversample_min_count is not None else os.getenv("SENTIMENT_OVERSAMPLE_MIN", "60"))
    focal_gamma = float(focal_gamma if focal_gamma is not None else os.getenv("SENTIMENT_FOCAL_GAMMA", "1.0"))
    if use_class_weights is None:
        use_class_weights = os.getenv("SENTIMENT_USE_CLASS_WEIGHTS", "false").lower() in {"1", "true", "yes", "y"}

    # Notebook 02 cho kết quả ổn định hơn khi chỉ dùng oversampling + focal loss gamma=1.
    # Class weights vẫn bật được qua flag, nhưng không bật mặc định để tránh over-penalize class hiếm.
    if oversample_min_count > 0:
        train_records = oversample_rare_classes(train_records, min_count=oversample_min_count)

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    train_dataset = FintaSentimentDataset(train_records, tokenizer)
    val_dataset = FintaSentimentDataset(val_records, tokenizer)

    logger.info("Train: %d | Val: %d", len(train_dataset), len(val_dataset))

    class_weights = compute_class_weights(train_dataset) if use_class_weights else None

    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    )

    training_args = TrainingArguments(
        output_dir=checkpoint_dir,
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        learning_rate=learning_rate,
        warmup_ratio=warmup_ratio,
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        label_smoothing_factor=label_smoothing,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        fp16=torch.cuda.is_available(),
        logging_steps=50,
        report_to="none",
        save_total_limit=2,
    )

    class FocalLossTrainer(Trainer):
        """Trainer dùng Focal Loss; class weight là tùy chọn."""

        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            logits = outputs.logits

            weight = class_weights.to(logits.device) if class_weights is not None else None
            ce_loss = torch.nn.functional.cross_entropy(
                logits, labels,
                weight=weight,
                reduction="none",
            )
            pt = torch.exp(-ce_loss)
            focal_loss = ((1 - pt) ** focal_gamma) * ce_loss
            loss = focal_loss.mean()
            return (loss, outputs) if return_outputs else loss

    trainer = FocalLossTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        processing_class=tokenizer,
    )

    logger.info("Bắt đầu training...")
    if use_mlflow:
        with mlflow.start_run():
            mlflow.log_params({
                "base_model": PHOBERT_BASE,
                "start_model": base_model,
                "num_labels": NUM_LABELS,
                "epochs": num_train_epochs,
                "batch_size": 16,
                "lr": learning_rate,
                "max_length": 256,
                "loss": f"focal_loss_gamma{focal_gamma}",
                "use_class_weights": use_class_weights,
                "oversample_min": oversample_min_count,
                "lr_scheduler": "cosine",
                "label_smoothing": label_smoothing,
            })
            trainer.train()
            final_metrics = trainer.evaluate()
            mlflow.log_metrics(final_metrics)
            mlflow.pytorch.log_model(model, "model")
    else:
        trainer.train()
        final_metrics = trainer.evaluate()

    # In classification report đầy đủ
    val_preds = trainer.predict(val_dataset)
    y_pred = np.argmax(val_preds.predictions, axis=-1)
    y_true = val_preds.label_ids

    print("\n" + "=" * 60)
    print("CLASSIFICATION REPORT (Validation Set)")
    print("=" * 60)
    print(classification_report(
        y_true, y_pred,
        target_names=list(ID2LABEL.values()),
        digits=4,
    ))

    # Kiểm tra SLA
    acc = final_metrics.get("eval_accuracy", 0)
    macro_f1 = final_metrics.get("eval_macro_f1", 0)
    print(f"\nSLA Check:")
    print(f"  Accuracy: {acc:.4f} {'✓ PASS' if acc >= SLA_ACCURACY else '✗ FAIL'} (target: {SLA_ACCURACY})")
    print(f"  Macro F1: {macro_f1:.4f} {'✓ PASS' if macro_f1 >= SLA_MACRO_F1 else '✗ FAIL'} (target: {SLA_MACRO_F1})")

    # Lưu best model
    trainer.save_model(best_model_dir)
    tokenizer.save_pretrained(best_model_dir)
    logger.info("Best model đã lưu tại: %s", best_model_dir)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Fine-tune FiNTA PhoBERT sentiment model.")
    parser.add_argument("--train-path", default=os.getenv("SENTIMENT_TRAIN_PATH", "data/splits/train.json"))
    parser.add_argument("--val-path", default=os.getenv("SENTIMENT_VAL_PATH", "data/splits/val.json"))
    parser.add_argument(
        "--base-model",
        default=os.getenv("SENTIMENT_BASE_MODEL", PHOBERT_BASE),
        help="HF model ID or local checkpoint to continue fine-tuning from.",
    )
    parser.add_argument(
        "--checkpoint-dir",
        default=os.getenv("SENTIMENT_CHECKPOINT_DIR", CHECKPOINT_DIR),
        help="Directory for checkpoints produced by this training run.",
    )
    parser.add_argument(
        "--epochs",
        type=float,
        default=float(os.getenv("SENTIMENT_NUM_EPOCHS", "8")),
        help="Number of training epochs.",
    )
    parser.add_argument("--learning-rate", type=float, default=float(os.getenv("SENTIMENT_LEARNING_RATE", "1e-5")))
    parser.add_argument("--warmup-ratio", type=float, default=float(os.getenv("SENTIMENT_WARMUP_RATIO", "0.15")))
    parser.add_argument("--label-smoothing", type=float, default=float(os.getenv("SENTIMENT_LABEL_SMOOTHING", "0.05")))
    parser.add_argument("--oversample-min", type=int, default=int(os.getenv("SENTIMENT_OVERSAMPLE_MIN", "60")))
    parser.add_argument("--focal-gamma", type=float, default=float(os.getenv("SENTIMENT_FOCAL_GAMMA", "1.0")))
    parser.add_argument(
        "--use-class-weights",
        action="store_true",
        default=os.getenv("SENTIMENT_USE_CLASS_WEIGHTS", "false").lower() in {"1", "true", "yes", "y"},
        help="Use balanced class weights inside focal loss. Off by default.",
    )
    args = parser.parse_args()
    train(
        train_path=args.train_path,
        val_path=args.val_path,
        base_model=args.base_model,
        checkpoint_dir=args.checkpoint_dir,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        warmup_ratio=args.warmup_ratio,
        label_smoothing=args.label_smoothing,
        oversample_min_count=args.oversample_min,
        use_class_weights=args.use_class_weights,
        focal_gamma=args.focal_gamma,
    )
