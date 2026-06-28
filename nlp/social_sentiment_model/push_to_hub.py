"""Push the fine-tuned social sentiment model to HuggingFace Hub."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def _build_model_card(repo_id: str, metrics: dict) -> str:
    acc = metrics.get("accuracy", "N/A")
    macro_f1 = metrics.get("macro_f1", "N/A")
    return f"""---
language: vi
license: mit
tags:
  - text-classification
  - sentiment-analysis
  - vietnamese
  - social-media
base_model: 5CD-AI/Vietnamese-Sentiment-visobert
---

# FiNTA Social Sentiment Model

**Task:** Vietnamese social/comment sentiment for market discussion.
**Base model:** `5CD-AI/Vietnamese-Sentiment-visobert`
**Accuracy:** {acc} | **Macro F1:** {macro_f1}

## Labels

| ID | Label | FiNTA mapping |
|----|-------|---------------|
| 0 | negative | Bearish |
| 1 | positive | Bullish |
| 2 | neutral | Uncertainty |

## Usage

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification

tokenizer = AutoTokenizer.from_pretrained("{repo_id}")
model = AutoModelForSequenceClassification.from_pretrained("{repo_id}")
```
"""


def push(checkpoint_dir: str, repo_id: str, report_path: str | None = None) -> None:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise EnvironmentError("HF_TOKEN không được đặt. Chạy: export HF_TOKEN=HF_TOKEN_HERE")

    metrics = {}
    if report_path and Path(report_path).exists():
        with open(report_path, encoding="utf-8") as f:
            metrics = json.load(f)

    tokenizer = AutoTokenizer.from_pretrained(checkpoint_dir)
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint_dir)
    model.push_to_hub(repo_id, token=hf_token)
    tokenizer.push_to_hub(repo_id, token=hf_token)

    from huggingface_hub import HfApi
    HfApi().upload_file(
        path_or_fileobj=_build_model_card(repo_id, metrics).encode("utf-8"),
        path_in_repo="README.md",
        repo_id=repo_id,
        token=hf_token,
    )
    print(f"Model URL: https://huggingface.co/{repo_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Push social sentiment model to HuggingFace Hub.")
    parser.add_argument("--checkpoint-dir", default="./checkpoints/social_sentiment/best_model")
    parser.add_argument("--repo-id", default=os.getenv("HF_SOCIAL_SENTIMENT_MODEL_REPO", "finta-team/finta-social-sentiment-visobert"))
    parser.add_argument("--report-path", default=os.getenv("SOCIAL_SENTIMENT_EVAL_REPORT", ""))
    args = parser.parse_args()
    push(args.checkpoint_dir, args.repo_id, args.report_path or None)


if __name__ == "__main__":
    main()
