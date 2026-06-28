"""
export_dataset_to_drive.py — Export dataset từ MinIO Bronze Layer ra file zip.

Chạy script này trên Oracle VM (1 lần) để chuẩn bị data cho Google Colab training.
Sau khi chạy xong, upload file zip lên Google Drive thủ công.

Luồng dữ liệu:
  Oracle VM (MinIO Bronze) → dataset_v1.zip → Google Drive → Colab training
"""

import json
import logging
import os
import sys
import zipfile
from pathlib import Path

# Thêm thư mục gốc FINTA-BigData vào path để import nlp.* hoạt động
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("./data")
SPLITS_DIR = OUTPUT_DIR / "splits"
EXPORT_ZIP = OUTPUT_DIR / "dataset_v1.zip"


def main() -> None:
    """Đọc Bronze Layer, gán nhãn, tách splits, đóng gói zip."""
    from nlp.data_preparation.data_loader import BronzeDataLoader
    from nlp.data_preparation.sampler import stratified_sample
    from nlp.data_preparation.llm_labeler import batch_label
    from nlp.data_preparation.validator import split_review_queue, check_label_distribution
    from nlp.data_preparation.splitter import create_splits

    target_count = int(os.getenv("DATASET_TARGET_COUNT", "5000"))
    labeled_dir = str(OUTPUT_DIR / "labeled")

    # Bước 1: Load Bronze Layer
    logger.info("=== Bước 1: Load Bronze Layer ===")
    loader = BronzeDataLoader()
    df = loader.load(target_count=target_count * 2)  # lấy dư để sampling

    # Bước 2: Stratified sampling
    logger.info("=== Bước 2: Stratified Sampling ===")
    df = stratified_sample(df, target=target_count)

    # Bước 3: Gán nhãn LLM (có checkpoint)
    logger.info("=== Bước 3: LLM Labeling ===")
    df = batch_label(df, output_dir=labeled_dir)

    # Bước 4: Kiểm tra chất lượng
    logger.info("=== Bước 4: Kiểm tra chất lượng ===")
    auto_df, review_df = split_review_queue(df)
    check_label_distribution(auto_df)

    # Bước 5: Tạo splits từ auto_accept
    logger.info("=== Bước 5: Tạo train/val/test splits ===")
    create_splits(auto_df, output_dir=str(SPLITS_DIR))

    # Bước 6: Đóng gói zip
    logger.info("=== Bước 6: Đóng gói zip ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(EXPORT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for split_file in SPLITS_DIR.glob("*.json"):
            zf.write(split_file, arcname=f"dataset_v1/{split_file.name}")

    logger.info("Xuất file hoàn tất: %s (%.1f MB)", EXPORT_ZIP, EXPORT_ZIP.stat().st_size / 1e6)
    logger.info("Bước tiếp theo: Upload %s lên Google Drive tại MyDrive/finta/", EXPORT_ZIP)


if __name__ == "__main__":
    main()
