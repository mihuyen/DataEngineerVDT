"""
model_loader.py — Singleton loader cho PhoBERT models từ HuggingFace Hub.

Thứ tự load:
  1. Thử load từ HuggingFace Hub (HF_MODEL_REPO env var).
  2. Nếu thất bại: đặt is_using_fallback=True, serving vẫn start được.
"""

import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

NEWS_REQUIRED_LABELS = {"positive", "negative", "neutral"}
SOCIAL_EXPECTED_NUM_LABELS = 3

LABEL_ALIASES = {
    "positive": "positive",
    "pos": "positive",
    "bullish": "positive",
    "negative": "negative",
    "neg": "negative",
    "bearish": "negative",
    "neutral": "neutral",
    "neu": "neutral",
    "uncertainty": "neutral",
}


def canonical_sentiment_label(label: str) -> str:
    return LABEL_ALIASES.get(str(label).strip().lower(), str(label).strip().lower())


def _id2label_values(model) -> set[str]:
    id2label = getattr(model.config, "id2label", {}) or {}
    return {canonical_sentiment_label(label) for label in id2label.values()}


def _validate_news_sentiment_model(model, repo: str) -> None:
    labels = _id2label_values(model)
    missing = NEWS_REQUIRED_LABELS - labels
    if getattr(model.config, "num_labels", 0) != len(NEWS_REQUIRED_LABELS) or missing:
        raise ValueError(
            "News sentiment model label space is incompatible: "
            f"repo={repo}, num_labels={getattr(model.config, 'num_labels', None)}, "
            f"labels={sorted(labels)}, missing={sorted(missing)}. "
            "Expected the FiNTA 3-class positive/negative/neutral head."
        )


def _validate_social_sentiment_model(model, repo: str) -> None:
    if getattr(model.config, "num_labels", 0) != SOCIAL_EXPECTED_NUM_LABELS:
        raise ValueError(
            "Social sentiment model label space is incompatible: "
            f"repo={repo}, num_labels={getattr(model.config, 'num_labels', None)}. "
            "Expected a 3-class positive/negative/neutral social sentiment head."
        )


class ModelLoader:
    """Singleton quản lý lifecycle của sentiment và topic models."""

    _instance: Optional["ModelLoader"] = None

    def __new__(cls) -> "ModelLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self.sentiment_model = None
        self.sentiment_tokenizer = None
        self.social_sentiment_model = None
        self.social_sentiment_tokenizer = None
        self.topic_model = None
        self.topic_tokenizer = None
        self.is_using_fallback: bool = True
        self.is_social_using_fallback: bool = True
        self.is_topic_using_fallback: bool = True
        self.model_version: str = os.getenv("MODEL_VERSION", "v0.0-fallback")
        self.social_model_version: str = os.getenv("SOCIAL_MODEL_VERSION", "social-fallback-rule-based")
        self._loaded_at: Optional[str] = None

        self._load_models()

    def _load_models(self) -> None:
        """Cố gắng load models, không raise exception khi thất bại."""
        sentiment_repo = os.getenv(
            "HF_MODEL_REPO",
            "wonrax/phobert-base-vietnamese-sentiment",
        )
        social_sentiment_repo = os.getenv(
            "HF_SOCIAL_SENTIMENT_MODEL_REPO",
            "5CD-AI/Vietnamese-Sentiment-visobert",
        )
        topic_repo = os.getenv("HF_TOPIC_MODEL_REPO", "finta-team/finta-topic-phobert")
        hf_token = os.getenv("HF_TOKEN")

        any_loaded = False

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            logger.info("Đang load sentiment model từ: %s", sentiment_repo)
            self.sentiment_tokenizer = AutoTokenizer.from_pretrained(
                sentiment_repo, token=hf_token
            )
            self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(
                sentiment_repo, token=hf_token
            )
            _validate_news_sentiment_model(self.sentiment_model, sentiment_repo)
            self.sentiment_model.eval()
            any_loaded = True
            self.is_using_fallback = False
            self.model_version = os.getenv("MODEL_VERSION", sentiment_repo)

        except Exception as exc:
            logger.warning(
                "Không thể load PhoBERT sentiment model (%s). "
                "News sentiment sẽ dùng rule-based fallback.",
                exc,
            )
            self.is_using_fallback = True

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            if os.getenv("LOAD_SOCIAL_MODEL", "false").lower() not in {"1", "true", "yes"}:
                raise RuntimeError("social sentiment model disabled by LOAD_SOCIAL_MODEL")

            logger.info("Đang load social sentiment model từ: %s", social_sentiment_repo)
            self.social_sentiment_tokenizer = AutoTokenizer.from_pretrained(
                social_sentiment_repo, token=hf_token
            )
            self.social_sentiment_model = AutoModelForSequenceClassification.from_pretrained(
                social_sentiment_repo, token=hf_token
            )
            _validate_social_sentiment_model(self.social_sentiment_model, social_sentiment_repo)
            self.social_sentiment_model.eval()
            any_loaded = True
            self.is_social_using_fallback = False
            self.social_model_version = os.getenv(
                "SOCIAL_MODEL_VERSION",
                social_sentiment_repo,
            )

        except Exception as exc:
            logger.warning(
                "Không thể load social sentiment model (%s). "
                "Social sentiment sẽ dùng rule-based fallback.",
                exc,
            )
            self.is_social_using_fallback = True
            self.social_model_version = "social-fallback-rule-based"

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            if os.getenv("LOAD_TOPIC_MODEL", "false").lower() not in {"1", "true", "yes"}:
                raise RuntimeError("topic model disabled by LOAD_TOPIC_MODEL")

            logger.info("Đang load topic model từ: %s", topic_repo)
            self.topic_tokenizer = AutoTokenizer.from_pretrained(
                topic_repo, token=hf_token
            )
            self.topic_model = AutoModelForSequenceClassification.from_pretrained(
                topic_repo, token=hf_token
            )
            self.topic_model.eval()
            any_loaded = True
            self.is_topic_using_fallback = False

            self._loaded_at = datetime.utcnow().isoformat() + "Z"
            logger.info("Topic model loaded successfully.")

        except Exception as exc:
            logger.warning(
                "Không thể load topic model (%s). Topic sẽ dùng fallback.",
                exc,
            )
            self.is_topic_using_fallback = True

        if not any_loaded:
            self.model_version = "fallback-rule-based"

        self.is_using_fallback = self.sentiment_model is None
        self._loaded_at = datetime.utcnow().isoformat() + "Z"

    def get_model_info(self) -> dict:
        """Trả về thông tin về model đang chạy."""
        return {
            "sentiment_repo": os.getenv("HF_MODEL_REPO", "not-set"),
            "social_sentiment_repo": os.getenv(
                "HF_SOCIAL_SENTIMENT_MODEL_REPO",
                "5CD-AI/Vietnamese-Sentiment-visobert",
            ),
            "topic_repo": os.getenv("HF_TOPIC_MODEL_REPO", "not-set"),
            "version": self.model_version,
            "social_version": self.social_model_version,
            "sentiment_num_labels": (
                getattr(self.sentiment_model.config, "num_labels", None)
                if self.sentiment_model is not None else None
            ),
            "social_sentiment_num_labels": (
                getattr(self.social_sentiment_model.config, "num_labels", None)
                if self.social_sentiment_model is not None else None
            ),
            "is_fallback": self.is_using_fallback,
            "is_social_fallback": self.is_social_using_fallback,
            "is_topic_fallback": self.is_topic_using_fallback,
            "loaded_at": self._loaded_at,
        }

    def reload(self) -> None:
        """Reload models (dùng khi có model mới upload lên Hub)."""
        logger.info("Reload models...")
        self._initialized = False
        self.__init__()
