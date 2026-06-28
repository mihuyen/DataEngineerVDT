"""
validator.py — Kiểm tra chất lượng nhãn và tách human review queue.

Input:  DataFrame có cột 'confidence', 'sentiment_label'.
Output: (auto_accept_df, review_df) và file JSON cho Label Studio.
"""

import json
import logging
import os
from pathlib import Path
from typing import Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# Ngưỡng mặc định, có thể override qua env var CONFIDENCE_THRESHOLD
_DEFAULT_CONFIDENCE_THRESHOLD = 0.75

VALID_LABELS = ["positive", "negative", "neutral"]

# Cảnh báo khi tỷ lệ nhãn dưới mức này
LABEL_MIN_PCT = 0.05
# Cảnh báo khi tỷ lệ nhãn vượt mức này
LABEL_MAX_PCT = 0.50


def split_review_queue(
    labeled_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Tách DataFrame thành auto_accept và human_review dựa trên confidence.

    Args:
        labeled_df: DataFrame có cột 'confidence'.

    Returns:
        (auto_accept_df, review_df) — bộ tự chấp nhận và bộ cần review.
    """
    threshold = float(os.getenv("CONFIDENCE_THRESHOLD", str(_DEFAULT_CONFIDENCE_THRESHOLD)))

    auto_accept = labeled_df[labeled_df["confidence"] >= threshold].copy()
    review = labeled_df[labeled_df["confidence"] < threshold].copy()

    total = len(labeled_df)
    auto_pct = len(auto_accept) / total * 100 if total else 0
    review_pct = len(review) / total * 100 if total else 0

    logger.info(
        "Phân loại confidence (ngưỡng=%.2f):\n"
        "  Auto-accept: %d bài (%.1f%%)\n"
        "  Human review: %d bài (%.1f%%)",
        threshold, len(auto_accept), auto_pct, len(review), review_pct,
    )

    return auto_accept, review


def check_label_distribution(df: pd.DataFrame) -> None:
    """
    Kiểm tra và in phân phối nhãn sentiment, cảnh báo nếu mất cân bằng.

    Args:
        df: DataFrame có cột 'sentiment_label'.
    """
    total = len(df)
    if total == 0:
        logger.warning("DataFrame rỗng, không thể kiểm tra phân phối.")
        return

    dist = df["sentiment_label"].value_counts()
    logger.info("Phân phối nhãn sentiment:")

    for label in VALID_LABELS:
        count = dist.get(label, 0)
        pct = count / total

        flag = ""
        if pct < LABEL_MIN_PCT:
            needed = int(LABEL_MIN_PCT * total) - count
            flag = f"  ⚠ WARNING: quá ít! Cần thêm ~{needed} bài"
        elif pct > LABEL_MAX_PCT:
            flag = "  ⚠ WARNING: mất cân bằng nghiêm trọng!"

        logger.info("  %-22s %4d bài (%5.1f%%)%s", label, count, pct * 100, flag)


def export_for_label_studio(review_df: pd.DataFrame, output_path: str) -> None:
    """
    Export DataFrame thành file JSON theo format Label Studio.

    Args:
        review_df:   DataFrame các bài cần human review.
        output_path: Đường dẫn file JSON đầu ra.
    """
    tasks = []
    for _, row in review_df.iterrows():
        task = {
            "id": row.get("article_id", ""),
            "data": {
                "text": f"Tiêu đề: {row.get('title', '')}\n\n{row.get('raw_content', '')[:800]}",
                "article_id": row.get("article_id", ""),
                "publisher": row.get("publisher", ""),
                "llm_suggestion": row.get("sentiment_label", ""),
                "llm_confidence": row.get("confidence", 0.0),
                "llm_reasoning": row.get("reasoning", ""),
            },
            "annotations": [],
            "predictions": [
                {
                    "model_version": "gpt-4o-mini",
                    "score": row.get("confidence", 0.0),
                    "result": [
                        {
                            "from_name": "sentiment",
                            "to_name": "text",
                            "type": "choices",
                            "value": {"choices": [row.get("sentiment_label", "")]},
                        }
                    ],
                }
            ],
        }
        tasks.append(task)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    logger.info("Đã export %d tasks cho Label Studio tại: %s", len(tasks), output_path)
