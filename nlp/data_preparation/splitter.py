"""
splitter.py — Tạo train/val/test splits chuẩn cho training PhoBERT.

Input:  DataFrame đã gán nhãn (có cột 'sentiment_label').
Output: train.json, val.json, test.json, metadata.json trong output_dir.

QUAN TRỌNG — Quy tắc test set:
  - Test set phải được "lock" hoàn toàn sau khi tạo.
  - KHÔNG dùng test set để quyết định hyperparameter.
  - KHÔNG xem test set cho đến khi training hoàn toàn xong.
  - Chỉ chạy evaluate.py trên test set 1 lần duy nhất cuối cùng.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple

import pandas as pd
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

DEFAULT_RATIOS = (0.70, 0.15, 0.15)
RANDOM_STATE = 42


def create_splits(
    df: pd.DataFrame,
    output_dir: str,
    ratios: Tuple[float, float, float] = DEFAULT_RATIOS,
) -> None:
    """
    Tạo train/val/test splits với stratified sampling theo nhãn sentiment.

    Args:
        df:         DataFrame có cột 'sentiment_label' và 'text' (hoặc title+content).
        output_dir: Thư mục lưu các file JSON split.
        ratios:     Tuple (train, val, test), phải cộng bằng 1.0.
    """
    train_ratio, val_ratio, test_ratio = ratios
    assert abs(sum(ratios) - 1.0) < 1e-6, "Tổng ratios phải bằng 1.0"

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    label_col = "sentiment_label"
    if label_col not in df.columns:
        raise ValueError(f"DataFrame thiếu cột '{label_col}'.")

    # Tách test set trước, sau đó tách val từ phần còn lại
    relative_val = val_ratio / (train_ratio + val_ratio)

    train_val_df, test_df = train_test_split(
        df,
        test_size=test_ratio,
        stratify=df[label_col],
        random_state=RANDOM_STATE,
    )

    train_df, val_df = train_test_split(
        train_val_df,
        test_size=relative_val,
        stratify=train_val_df[label_col],
        random_state=RANDOM_STATE,
    )

    # Lưu các split
    for split_name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        file_path = out_path / f"{split_name}.json"
        split_df.to_json(file_path, orient="records", force_ascii=False, indent=2)
        logger.info("Đã lưu %s: %d bài → %s", split_name, len(split_df), file_path)

    # Tạo metadata
    label_dist = df[label_col].value_counts().to_dict()
    source_dist = df["publisher"].value_counts().to_dict() if "publisher" in df.columns else {}

    metadata = {
        "version": "v1.0",
        "created_date": datetime.utcnow().isoformat() + "Z",
        "total_size": len(df),
        "train_size": len(train_df),
        "val_size": len(val_df),
        "test_size": len(test_df),
        "ratios": {"train": train_ratio, "val": val_ratio, "test": test_ratio},
        "label_distribution": label_dist,
        "source_distribution": source_dist,
        "random_state": RANDOM_STATE,
        "note": (
            "Test set đã được lock. "
            "KHÔNG dùng để chọn hyperparameter. "
            "Chỉ chạy evaluate.py 1 lần cuối cùng."
        ),
    }

    meta_path = out_path / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logger.info(
        "Splits hoàn tất:\n"
        "  Train: %d | Val: %d | Test: %d\n"
        "  Metadata: %s",
        len(train_df), len(val_df), len(test_df), meta_path,
    )
