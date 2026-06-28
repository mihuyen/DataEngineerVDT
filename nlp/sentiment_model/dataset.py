"""
dataset.py — HuggingFace Dataset class cho sentiment training.

Input:  List of dicts {text: str, label: str}.
Output: PyTorch Dataset trả về (input_ids, attention_mask, labels).

Label mapping cố định (không thay đổi giữa train và serving):
  0: positive | 1: negative | 2: neutral
"""

import logging
from typing import Dict, List

import torch
from torch.utils.data import Dataset
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)

PHOBERT_BASE = "vinai/phobert-base-v2"
MAX_LENGTH = 256  # PhoBERT hoạt động tốt nhất ở 256, không cần 512

# Label mapping cố định — KHÔNG thay đổi thứ tự này
LABEL2ID: Dict[str, int] = {"positive": 0, "negative": 1, "neutral": 2}
ID2LABEL: Dict[int, str] = {v: k for k, v in LABEL2ID.items()}
NUM_LABELS = len(LABEL2ID)

LEGACY_LABEL_MAP = {
    "bullish": "positive",
    "hype/fomo": "positive",
    "bearish": "negative",
    "panic": "negative",
    "uncertainty": "neutral",
    "contrarian": "neutral",
    "positive": "positive",
    "negative": "negative",
    "neutral": "neutral",
}


def normalize_label(label: str) -> str:
    normalized = LEGACY_LABEL_MAP.get(str(label).strip().lower())
    if normalized is None:
        raise ValueError(f"Nhãn không hợp lệ: {label!r}. Chỉ chấp nhận: {list(LABEL2ID)}")
    return normalized


class FintaSentimentDataset(Dataset):
    """Dataset PyTorch cho fine-tuning PhoBERT phân loại cảm xúc ba nhãn."""

    def __init__(self, records: List[Dict], tokenizer: AutoTokenizer = None) -> None:
        """
        Args:
            records:   List dicts với key 'text' và 'label'.
            tokenizer: AutoTokenizer đã load sẵn (None → tự load).
        """
        self.records = [{**record, "label": normalize_label(record["label"])} for record in records]
        self.tokenizer = tokenizer or AutoTokenizer.from_pretrained(PHOBERT_BASE)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        record = self.records[idx]
        encoding = self.tokenizer(
            record["text"],
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(LABEL2ID[record["label"]], dtype=torch.long),
        }


def oversample_rare_classes(records: List[Dict], min_count: int = 60) -> List[Dict]:
    """
    Oversample các class có ít hơn min_count mẫu bằng cách lặp lại ngẫu nhiên.

    Args:
        records:   List dicts với key 'text' và 'label'.
        min_count: Số mẫu tối thiểu mỗi class sau khi oversample.

    Returns:
        List records đã được augment, shuffle ngẫu nhiên.
    """
    import random
    from collections import Counter

    label_counts = Counter(r["label"] for r in records)
    augmented = list(records)

    for label, count in label_counts.items():
        if count < min_count:
            rare = [r for r in records if r["label"] == label]
            needed = min_count - count
            augmented.extend(random.choices(rare, k=needed))
            logger.info("Oversample '%s': %d → %d mẫu", label, count, count + needed)

    random.shuffle(augmented)
    logger.info("Tổng sau oversample: %d mẫu (trước: %d)", len(augmented), len(records))
    return augmented


def compute_class_weights(dataset: FintaSentimentDataset) -> torch.Tensor:
    """
    Tính class weights để xử lý class imbalance.

    Args:
        dataset: FintaSentimentDataset đã khởi tạo.

    Returns:
        Tensor shape (NUM_LABELS,) với trọng số nghịch đảo tần suất.
    """
    from sklearn.utils.class_weight import compute_class_weight
    import numpy as np

    labels = [LABEL2ID[r["label"]] for r in dataset.records]
    classes = list(range(NUM_LABELS))

    weights = compute_class_weight(
        class_weight="balanced",
        classes=np.array(classes),
        y=np.array(labels),
    )
    weight_tensor = torch.tensor(weights, dtype=torch.float)
    logger.info("Class weights: %s", dict(zip(ID2LABEL.values(), weights.round(3))))
    return weight_tensor
