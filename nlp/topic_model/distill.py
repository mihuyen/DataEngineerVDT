"""
topic_model/distill.py — Train multi-label topic classifier từ LLM silver labels.

Dùng knowledge distillation: PhoBERT student học từ soft labels của GPT-4o-mini.
Input:  data/splits/train.json, val.json (có cột topic_distribution)
Output: checkpoints/topic/best_model/

Mục tiêu: alignment với LLM silver labels >= 85%
"""

import json
import logging
import os
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import f1_score, hamming_loss
from torch.utils.data import DataLoader
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

from nlp.topic_model.dataset import (
    PHOBERT_BASE,
    NUM_TOPICS,
    TOPICS,
    FintaTopicDataset,
)

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = "./checkpoints/topic"
BEST_MODEL_DIR = f"{CHECKPOINT_DIR}/best_model"

# Ngưỡng để xác định nhãn dương (prob > THRESHOLD → thuộc chủ đề)
TOPIC_THRESHOLD = 0.3

# Hyperparameters
EPOCHS = 5
BATCH_SIZE = 16
LR = 2e-5
WARMUP_RATIO = 0.1


def _load_records(json_path: str) -> list:
    with open(json_path, encoding="utf-8") as f:
        rows = json.load(f)
    return [
        {
            "text": f"Tiêu đề: {r.get('title', '')}\n\n{r.get('raw_content', '')}",
            "topic_distribution": r.get("topic_distribution", {}),
        }
        for r in rows
    ]


def _compute_metrics(y_true: np.ndarray, y_pred_prob: np.ndarray) -> dict:
    """Tính micro F1, macro F1, hamming loss với ngưỡng TOPIC_THRESHOLD."""
    y_true_bin = (y_true >= TOPIC_THRESHOLD).astype(int)
    y_pred = (y_pred_prob >= TOPIC_THRESHOLD).astype(int)

    micro_f1 = f1_score(y_true_bin, y_pred, average="micro", zero_division=0)
    macro_f1 = f1_score(y_true_bin, y_pred, average="macro", zero_division=0)
    h_loss = hamming_loss(y_true_bin, y_pred)

    return {
        "micro_f1": round(float(micro_f1), 4),
        "macro_f1": round(float(macro_f1), 4),
        "hamming_loss": round(float(h_loss), 4),
    }


def distill(
    train_path: str = "data/splits/train.json",
    val_path: str = "data/splits/val.json",
) -> None:
    """
    Train multi-label topic classifier bằng soft labels từ LLM.

    Args:
        train_path: Đường dẫn train.json.
        val_path:   Đường dẫn val.json.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Thiết bị: %s", device)

    tokenizer = AutoTokenizer.from_pretrained(PHOBERT_BASE)
    train_records = _load_records(train_path)
    val_records = _load_records(val_path)

    train_dataset = FintaTopicDataset(train_records, tokenizer)
    val_dataset = FintaTopicDataset(val_records, tokenizer)
    logger.info("Train: %d | Val: %d", len(train_dataset), len(val_dataset))

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

    # PhoBERT với output layer 6 topics thay vì Softmax
    model = AutoModelForSequenceClassification.from_pretrained(
        PHOBERT_BASE,
        num_labels=NUM_TOPICS,
        problem_type="multi_label_classification",
    )
    model.to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    total_steps = len(train_loader) * EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)

    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )

    # BCEWithLogitsLoss cho multi-label (không dùng CrossEntropy)
    loss_fn = nn.BCEWithLogitsLoss()

    best_macro_f1 = 0.0
    Path(CHECKPOINT_DIR).mkdir(parents=True, exist_ok=True)

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0

        for batch in train_loader:
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
            loss = loss_fn(logits, labels)
            loss.backward()

            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)

        # Validation
        model.eval()
        all_probs, all_targets = [], []
        with torch.no_grad():
            for batch in val_loader:
                logits = model(
                    input_ids=batch["input_ids"].to(device),
                    attention_mask=batch["attention_mask"].to(device),
                ).logits
                probs = torch.sigmoid(logits).cpu().numpy()
                all_probs.extend(probs)
                all_targets.extend(batch["labels"].numpy())

        metrics = _compute_metrics(np.array(all_targets), np.array(all_probs))
        logger.info(
            "Epoch %d/%d | loss=%.4f | micro_f1=%.4f | macro_f1=%.4f | hamming=%.4f",
            epoch, EPOCHS, avg_loss,
            metrics["micro_f1"], metrics["macro_f1"], metrics["hamming_loss"],
        )

        if metrics["macro_f1"] > best_macro_f1:
            best_macro_f1 = metrics["macro_f1"]
            model.save_pretrained(BEST_MODEL_DIR)
            tokenizer.save_pretrained(BEST_MODEL_DIR)
            logger.info("  → Best model saved (macro_f1=%.4f)", best_macro_f1)

    # Lưu model card ghi rõ threshold
    card_path = Path(BEST_MODEL_DIR) / "MODEL_CARD.md"
    card_path.write_text(
        f"# FiNTA Topic Model\n\n"
        f"Multi-label topic classifier for Vietnamese financial news.\n\n"
        f"**Threshold:** {TOPIC_THRESHOLD}\n\n"
        f"**Topics:** {', '.join(TOPICS)}\n\n"
        f"**Best val macro_f1:** {best_macro_f1:.4f}\n",
        encoding="utf-8",
    )
    logger.info("Distillation hoàn tất. Best macro_f1=%.4f", best_macro_f1)


def push_to_hub(checkpoint_dir: str = BEST_MODEL_DIR, repo_id: str = None) -> None:
    """Upload topic model lên HuggingFace Hub."""
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    repo_id = repo_id or os.getenv("HF_TOPIC_MODEL_REPO", "finta-team/finta-topic-phobert")
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise EnvironmentError("HF_TOKEN không được đặt.")

    tokenizer = AutoTokenizer.from_pretrained(checkpoint_dir)
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint_dir)
    model.push_to_hub(repo_id, token=hf_token)
    tokenizer.push_to_hub(repo_id, token=hf_token)
    print(f"Topic model URL: https://huggingface.co/{repo_id}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    distill()
