"""
dataset.py -- Dataset for social Vietnamese sentiment fine-tuning.

The social model keeps the ViSoBERT 3-class social sentiment head:
  0: negative | 1: positive | 2: neutral

Serving maps these classes back to FiNTA market labels:
  negative -> Bearish, neutral -> Uncertainty, positive -> Bullish.
"""

from __future__ import annotations

from typing import Dict, List

import torch
from torch.utils.data import Dataset
from transformers import AutoTokenizer


VISOBERT_BASE = "5CD-AI/Vietnamese-Sentiment-visobert"
MAX_LENGTH = 256

LABEL2ID: Dict[str, int] = {
    "negative": 0,
    "positive": 1,
    "neutral": 2,
}
ID2LABEL: Dict[int, str] = {v: k for k, v in LABEL2ID.items()}
NUM_LABELS = len(LABEL2ID)

FINTA_TO_SOCIAL_LABEL = {
    "Bearish": "negative",
    "Panic": "negative",
    "Uncertainty": "neutral",
    "Contrarian": "neutral",
    "Bullish": "positive",
    "Hype/FOMO": "positive",
}


def normalize_social_label(label: str) -> str:
    normalized = str(label or "").strip()
    lowered = normalized.lower()
    if lowered in LABEL2ID:
        return lowered
    if normalized in FINTA_TO_SOCIAL_LABEL:
        return FINTA_TO_SOCIAL_LABEL[normalized]
    raise ValueError(f"Unsupported social sentiment label: {label}")


class SocialSentimentDataset(Dataset):
    def __init__(self, records: List[Dict], tokenizer: AutoTokenizer = None) -> None:
        self.records = records
        self.tokenizer = tokenizer or AutoTokenizer.from_pretrained(VISOBERT_BASE)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        record = self.records[idx]
        text = record.get("text") or record.get("cleaned_content") or record.get("raw_content") or record.get("content") or ""
        label = normalize_social_label(record.get("sentiment_label") or record.get("label"))

        encoding = self.tokenizer(
            text,
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(LABEL2ID[label], dtype=torch.long),
        }
