"""
push_to_hub.py — Upload PhoBERT sentiment model lên HuggingFace Hub.

Input:  ./checkpoints/sentiment/best_model/ (sau khi train xong)
Output: Model đã upload tại HF_MODEL_REPO, kèm model card.
"""

import json
import logging
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

logger = logging.getLogger(__name__)

DEFAULT_CHECKPOINT = "./checkpoints/sentiment/best_model"
DEFAULT_REPO = "your-account/stock-news-sentiment-3class"


def _build_model_card(repo_id: str, metrics: dict) -> str:
    """Tạo nội dung README.md (model card) cho HuggingFace Hub."""
    acc = metrics.get("accuracy", "N/A")
    macro_f1 = metrics.get("macro_f1", "N/A")

    return f"""---
language: vi
license: mit
tags:
  - text-classification
  - sentiment-analysis
  - vietnamese
  - finance
  - phobert
base_model: vinai/phobert-base-v2
---

# FiNTA Sentiment Model

**Task:** Sentiment Analysis — Vietnamese Financial News
**Base model:** `vinai/phobert-base-v2`
**Accuracy:** {acc} | **Macro F1:** {macro_f1}

## Labels (3 lớp cảm xúc)

| ID | Label | Mô tả | Score range |
|----|-------|-------|-------------|
| 0 | positive | Tích cực | +0.05 → +1.0 |
| 1 | negative | Tiêu cực | -1.0 → -0.05 |
| 2 | neutral | Trung tính | -0.05 → +0.05 |

## Usage

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

tokenizer = AutoTokenizer.from_pretrained("{repo_id}")
model = AutoModelForSequenceClassification.from_pretrained("{repo_id}")

text = "Cổ phiếu VNM tăng mạnh, nhà đầu tư lạc quan về triển vọng quý 4"
inputs = tokenizer(text, return_tensors="pt", max_length=256,
                   truncation=True, padding="max_length")

with torch.no_grad():
    logits = model(**inputs).logits
    pred_id = logits.argmax().item()

labels = ["positive", "negative", "neutral"]
print(labels[pred_id])
```

## Training

Fine-tuned on 5,000 Vietnamese financial news articles labeled by GPT-4o-mini
and validated by domain experts. Dataset sourced from CafeF, VietStock, VNExpress.
"""


def push(
    checkpoint_dir: str = DEFAULT_CHECKPOINT,
    repo_id: str = None,
    report_path: str = None,
) -> None:
    """
    Upload model lên HuggingFace Hub kèm model card.

    Args:
        checkpoint_dir: Thư mục best_model local.
        repo_id:        HF repo ID. None → đọc từ HF_MODEL_REPO env var.
    """
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    repo_id = repo_id or os.getenv("HF_MODEL_REPO", DEFAULT_REPO)
    hf_token = os.environ.get("HF_TOKEN")

    if not hf_token:
        raise EnvironmentError("HF_TOKEN không được đặt. Chạy: export HF_TOKEN=HF_TOKEN_HERE")

    # Tải metrics nếu có
    report_path = Path(report_path) if report_path else Path(checkpoint_dir).parent.parent / "evaluation_report.json"
    metrics = {}
    if report_path.exists():
        with open(report_path, encoding="utf-8") as f:
            metrics = json.load(f)
        logger.info("Đã tải metrics từ: %s", report_path)

    logger.info("Tải model từ: %s", checkpoint_dir)
    tokenizer = AutoTokenizer.from_pretrained(checkpoint_dir)
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint_dir)

    logger.info("Đang upload lên: %s ...", repo_id)
    model.push_to_hub(repo_id, token=hf_token)
    tokenizer.push_to_hub(repo_id, token=hf_token)

    # Upload model card
    from huggingface_hub import HfApi
    api = HfApi()
    card_content = _build_model_card(repo_id, metrics)
    api.upload_file(
        path_or_fileobj=card_content.encode("utf-8"),
        path_in_repo="README.md",
        repo_id=repo_id,
        token=hf_token,
    )

    model_url = f"https://huggingface.co/{repo_id}"
    logger.info("Upload hoàn tất!")
    print(f"\nModel URL: {model_url}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Push FiNTA sentiment model to HuggingFace Hub.")
    parser.add_argument(
        "--checkpoint-dir",
        default=os.getenv("SENTIMENT_MODEL_PATH", DEFAULT_CHECKPOINT),
        help="Local best_model directory to upload.",
    )
    parser.add_argument(
        "--repo-id",
        default=os.getenv("HF_MODEL_REPO", DEFAULT_REPO),
        help="Target HuggingFace repo ID.",
    )
    parser.add_argument(
        "--report-path",
        default=os.getenv("SENTIMENT_EVAL_REPORT", ""),
        help="Optional evaluation_report JSON path for the model card.",
    )
    args = parser.parse_args()
    push(
        checkpoint_dir=args.checkpoint_dir,
        repo_id=args.repo_id,
        report_path=args.report_path or None,
    )
