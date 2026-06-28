"""
topic_model/dataset.py — Multi-label dataset class cho topic classification.

Input:  List of dicts {text, topic_distribution} từ LLM silver labels.
Output: PyTorch Dataset trả về (input_ids, attention_mask, labels tensor float).
"""

import logging
from typing import Dict, List

import torch
from torch.utils.data import Dataset
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)

PHOBERT_BASE = "vinai/phobert-base-v2"
MAX_LENGTH = 256

# Thứ tự cố định của các chủ đề — KHÔNG thay đổi
TOPICS: List[str] = [
    "Chính sách tiền tệ",
    "Kết quả kinh doanh",
    "M&A",
    "Biến động vĩ mô",
    "Tin đồn thị trường",
    "Khác",
]
NUM_TOPICS = len(TOPICS)
TOPIC2ID: Dict[str, int] = {t: i for i, t in enumerate(TOPICS)}


class FintaTopicDataset(Dataset):
    """Multi-label dataset cho phân loại chủ đề tin tức tài chính."""

    def __init__(self, records: List[Dict], tokenizer: AutoTokenizer = None) -> None:
        """
        Args:
            records:   List dicts với key 'text' và 'topic_distribution' (dict nhãn → float).
            tokenizer: AutoTokenizer đã load sẵn (None → tự load).
        """
        self.records = records
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

        # Soft labels từ LLM topic_distribution
        dist = record.get("topic_distribution", {})
        label_vector = torch.tensor(
            [float(dist.get(topic, 0.0)) for topic in TOPICS],
            dtype=torch.float,
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": label_vector,
        }
