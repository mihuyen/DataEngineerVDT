"""
sampler.py — Stratified sampling cân bằng theo nguồn tin.

Input:  DataFrame từ BronzeDataLoader (có cột 'publisher').
Output: DataFrame với phân phối đều nhau giữa các nguồn tin.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Tỷ lệ mục tiêu cho mỗi nguồn (xấp xỉ 1/3)
PUBLISHERS = ["CafeF", "VietStock", "VNExpress"]
RANDOM_STATE = 42


def stratified_sample(df: pd.DataFrame, target: int = 5000) -> pd.DataFrame:
    """
    Lấy mẫu cân bằng từ DataFrame theo cột 'publisher'.

    Args:
        df:     DataFrame đầu vào với cột 'publisher'.
        target: Tổng số bài cần lấy mẫu.

    Returns:
        DataFrame đã sampling, ~target/3 bài mỗi nguồn.
    """
    per_source = target // len(PUBLISHERS)
    sampled_parts = []

    for publisher in PUBLISHERS:
        subset = df[df["publisher"] == publisher]
        available = len(subset)

        if available == 0:
            logger.warning("Nguồn '%s' không có bài nào trong DataFrame.", publisher)
            continue

        if available < per_source:
            logger.warning(
                "Nguồn '%s' chỉ có %d bài (cần %d). Lấy toàn bộ.",
                publisher, available, per_source,
            )
            sampled_parts.append(subset)
        else:
            sampled_parts.append(
                subset.sample(n=per_source, random_state=RANDOM_STATE)
            )

    if not sampled_parts:
        logger.error("Không có nguồn nào hợp lệ để sampling.")
        return pd.DataFrame()

    result = pd.concat(sampled_parts, ignore_index=True).sample(
        frac=1, random_state=RANDOM_STATE
    )

    logger.info("Phân phối sau sampling:")
    for publisher, count in result["publisher"].value_counts().items():
        pct = count / len(result) * 100
        logger.info("  %-15s %d bài (%.1f%%)", publisher, count, pct)

    logger.info("Tổng cộng: %d bài.", len(result))
    return result
