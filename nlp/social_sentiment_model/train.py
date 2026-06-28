"""
train.py -- Fine-tune ViSoBERT for Vietnamese social sentiment.

Input JSON records may use either:
  - text/label with label in negative|neutral|positive
  - raw_content|cleaned_content/sentiment_label with FiNTA labels

Output defaults to checkpoints/social_sentiment/best_model.
"""

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
from sklearn.metrics import accuracy_score, f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments

from nlp.social_sentiment_model.dataset import (
    ID2LABEL,
    LABEL2ID,
    NUM_LABELS,
    VISOBERT_BASE,
    SocialSentimentDataset,
)


logger = logging.getLogger(__name__)
DEFAULT_CHECKPOINT_DIR = "./checkpoints/social_sentiment"


def load_records(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": round(accuracy_score(labels, preds), 4),
        "macro_f1": round(f1_score(labels, preds, average="macro", zero_division=0), 4),
        "weighted_f1": round(f1_score(labels, preds, average="weighted", zero_division=0), 4),
    }


def train(
    train_path: str,
    val_path: str,
    base_model: str,
    checkpoint_dir: str,
    epochs: float,
) -> None:
    logger.info("Loading social train=%s val=%s", train_path, val_path)
    train_records = load_records(train_path)
    val_records = load_records(val_path)

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    train_dataset = SocialSentimentDataset(train_records, tokenizer)
    val_dataset = SocialSentimentDataset(val_records, tokenizer)

    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    )

    training_args = TrainingArguments(
        output_dir=checkpoint_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        learning_rate=2e-5,
        warmup_ratio=0.1,
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        fp16=torch.cuda.is_available(),
        report_to="none",
        save_total_limit=2,
        logging_steps=50,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        processing_class=tokenizer,
    )
    trainer.train()

    best_model_dir = f"{checkpoint_dir.rstrip('/')}/best_model"
    trainer.save_model(best_model_dir)
    tokenizer.save_pretrained(best_model_dir)
    logger.info("Best social sentiment model saved at %s", best_model_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune ViSoBERT for social sentiment.")
    parser.add_argument("--train-path", required=True)
    parser.add_argument("--val-path", required=True)
    parser.add_argument("--base-model", default=os.getenv("HF_SOCIAL_SENTIMENT_MODEL_REPO", VISOBERT_BASE))
    parser.add_argument("--checkpoint-dir", default=os.getenv("SOCIAL_SENTIMENT_CHECKPOINT_DIR", DEFAULT_CHECKPOINT_DIR))
    parser.add_argument("--epochs", type=float, default=float(os.getenv("SOCIAL_SENTIMENT_EPOCHS", "3")))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    train(
        train_path=args.train_path,
        val_path=args.val_path,
        base_model=args.base_model,
        checkpoint_dir=args.checkpoint_dir,
        epochs=args.epochs,
    )


if __name__ == "__main__":
    main()
