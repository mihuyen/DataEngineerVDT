"""
predictor.py — Logic inference chính cho sentiment và topic prediction.

Hỗ trợ:
  - PhoBERT model (khi đã load từ HuggingFace Hub)
  - Rule-based fallback (khi model chưa có, confidence cố định = 0.3)
  - Semantic chunking cho bài dài > 256 tokens
"""

import logging
import re
from typing import Dict, List

import torch

try:
    from nlp.serving.model_loader import ModelLoader, canonical_sentiment_label
except ImportError:
    from model_loader import ModelLoader, canonical_sentiment_label

logger = logging.getLogger(__name__)

# Label mapping cố định — phải khớp với sentiment_model/dataset.py
SENTIMENT_ID2LABEL = {0: "positive", 1: "negative", 2: "neutral"}

# Chủ đề — phải khớp với topic_model/dataset.py
TOPICS = [
    "Chính sách tiền tệ",
    "Kết quả kinh doanh",
    "M&A",
    "Biến động vĩ mô",
    "Tin đồn thị trường",
    "Khác",
]

TOPIC_THRESHOLD = 0.3
FALLBACK_CONFIDENCE = 0.3
LOW_CONFIDENCE_THRESHOLD = 0.5
MAX_TOKENS = 256
OVERLAP_TOKENS = 30

# Từ điển từ khóa cho rule-based fallback
_FALLBACK_KEYWORDS = {
    "positive": ["tăng", "khởi sắc", "tích cực", "lạc quan", "phục hồi", "bứt phá", "tăng trưởng"],
    "negative": [
        "giảm", "lao dốc", "tiêu cực", "bi quan", "sụt", "giảm sâu", "suy yếu",
        "hoảng loạn", "bán tháo", "sụp đổ", "khủng hoảng", "hoảng sợ",
    ],
}


class SentimentPredictor:
    """Dự đoán cảm xúc (sentiment) cho văn bản tài chính tiếng Việt."""

    def __init__(self, model_loader: ModelLoader) -> None:
        self._loader = model_loader

    def _preprocess(self, text: str) -> str:
        """
        Tiền xử lý text: word segmentation tiếng Việt + chuẩn hóa.
        Nếu underthesea không có, bỏ qua segmentation.
        """
        text = re.sub(r"\s+", " ", text).strip()
        try:
            from underthesea import word_tokenize
            text = word_tokenize(text, format="text")
        except ImportError:
            pass  # underthesea chưa cài, dùng text gốc
        return text

    def _semantic_chunking(self, text: str, tokenizer) -> List[str]:
        """
        Tách text thành các chunks khi bài dài > MAX_TOKENS.
        Dùng sliding window với overlap để giữ ngữ cảnh.

        Args:
            text:      Text đã tiền xử lý.
            tokenizer: Tokenizer PhoBERT.

        Returns:
            List các chunk text.
        """
        tokens = tokenizer.encode(text, add_special_tokens=False)

        if len(tokens) <= MAX_TOKENS - 2:  # -2 cho [CLS] và [SEP]
            return [text]

        stride = MAX_TOKENS - 2 - OVERLAP_TOKENS
        chunks = []
        start = 0

        while start < len(tokens):
            end = min(start + MAX_TOKENS - 2, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
            chunks.append(chunk_text)
            if end == len(tokens):
                break
            start += stride

        return chunks

    def _predict_phobert(self, text: str) -> dict:
        """Inference bằng PhoBERT model thực sự."""
        tokenizer = self._loader.sentiment_tokenizer
        model = self._loader.sentiment_model
        device = next(model.parameters()).device

        processed_text = self._preprocess(text)
        chunks = self._semantic_chunking(processed_text, tokenizer)

        all_probs = []
        for chunk in chunks:
            encoding = tokenizer(
                chunk,
                max_length=MAX_TOKENS,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            )
            with torch.no_grad():
                logits = model(
                    input_ids=encoding["input_ids"].to(device),
                    attention_mask=encoding["attention_mask"].to(device),
                ).logits
                probs = torch.softmax(logits, dim=-1).cpu().squeeze(0)
            # Weight = độ dài chunk (số token)
            chunk_len = encoding["attention_mask"].sum().item()
            all_probs.append((probs, chunk_len))

        # Weighted average theo độ dài chunk
        total_weight = sum(w for _, w in all_probs)
        avg_probs = sum(p * w for p, w in all_probs) / total_weight

        pred_id = int(avg_probs.argmax().item())
        confidence = float(avg_probs[pred_id].item())
        configured_labels = getattr(model.config, "id2label", {}) or SENTIMENT_ID2LABEL
        labels_by_id = {
            int(label_id): canonical_sentiment_label(label)
            for label_id, label in configured_labels.items()
        }
        label = labels_by_id[pred_id]
        positive_id = next(label_id for label_id, value in labels_by_id.items() if value == "positive")
        negative_id = next(label_id for label_id, value in labels_by_id.items() if value == "negative")
        positive_probability = float(avg_probs[positive_id].item())
        negative_probability = float(avg_probs[negative_id].item())
        score = positive_probability - negative_probability

        return {
            "sentiment_label": label,
            "sentiment_score": round(score, 4),
            "confidence_score": round(confidence, 4),
            "is_low_confidence": confidence < LOW_CONFIDENCE_THRESHOLD,
        }

    def _rule_based_fallback(self, text: str) -> dict:
        """
        Fallback đơn giản dùng từ điển từ khóa.
        confidence cố định = 0.3 để báo hiệu đây là fallback.
        """
        text_lower = text.lower()
        counts = {label: 0 for label in _FALLBACK_KEYWORDS}

        for label, keywords in _FALLBACK_KEYWORDS.items():
            for kw in keywords:
                counts[label] += text_lower.count(kw)

        best_label = max(counts, key=counts.get)
        # Nếu không có từ khóa nào → neutral
        if counts[best_label] == 0:
            best_label = "neutral"

        score_map = {
            "positive": 0.5,
            "negative": -0.5,
            "neutral": 0.0,
        }

        return {
            "sentiment_label": best_label,
            "sentiment_score": score_map.get(best_label, 0.0),
            "confidence_score": FALLBACK_CONFIDENCE,
            "is_low_confidence": True,
        }

    def predict(self, text: str) -> dict:
        """
        Dự đoán sentiment cho một đoạn text.

        Args:
            text: Văn bản tiếng Việt.

        Returns:
            Dict với sentiment_label, sentiment_score, confidence_score, is_low_confidence.
        """
        if self._loader.is_using_fallback:
            return self._rule_based_fallback(text)
        return self._predict_phobert(text)

    def predict_batch(self, texts: List[str]) -> List[dict]:
        """Dự đoán batch, xử lý tuần tự (workers=1 để tránh OOM)."""
        return [self.predict(t) for t in texts]


class SocialSentimentPredictor:
    """Dự đoán sentiment cho comment/social tiếng Việt bằng ViSoBERT."""

    POSITIVE_LABEL_HINTS = {"positive", "pos", "label_1", "1", "tích cực", "tich cuc"}
    NEGATIVE_LABEL_HINTS = {"negative", "neg", "label_0", "0", "tiêu cực", "tieu cuc"}
    NEUTRAL_LABEL_HINTS = {"neutral", "neu", "label_2", "2", "trung tính", "trung tinh"}

    def __init__(self, model_loader: ModelLoader) -> None:
        self._loader = model_loader
        self._fallback = SentimentPredictor(model_loader)

    def _map_label(self, raw_label: str, confidence: float) -> tuple[str, float]:
        normalized = str(raw_label).strip()
        lowered = normalized.lower()

        if lowered in self.POSITIVE_LABEL_HINTS:
            return "positive", 0.65
        if lowered in self.NEGATIVE_LABEL_HINTS:
            return "negative", -0.65
        if lowered in self.NEUTRAL_LABEL_HINTS:
            return "neutral", 0.0

        # Conservative fallback for unexpected label names.
        if confidence < LOW_CONFIDENCE_THRESHOLD:
            return "neutral", 0.0
        return "neutral", 0.0

    def _predict_visobert(self, text: str) -> dict:
        tokenizer = self._loader.social_sentiment_tokenizer
        model = self._loader.social_sentiment_model
        device = next(model.parameters()).device

        text = re.sub(r"\s+", " ", text).strip()
        encoding = tokenizer(
            text,
            max_length=MAX_TOKENS,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        with torch.no_grad():
            logits = model(
                input_ids=encoding["input_ids"].to(device),
                attention_mask=encoding["attention_mask"].to(device),
            ).logits
            probs = torch.softmax(logits, dim=-1).cpu().squeeze(0)

        pred_id = int(probs.argmax().item())
        confidence = float(probs[pred_id].item())
        id2label = getattr(model.config, "id2label", {}) or {}
        raw_label = id2label.get(pred_id, f"LABEL_{pred_id}")
        label, score = self._map_label(raw_label, confidence)

        return {
            "sentiment_label": label,
            "sentiment_score": round(score, 4),
            "confidence_score": round(confidence, 4),
            "is_low_confidence": confidence < LOW_CONFIDENCE_THRESHOLD,
        }

    def predict(self, text: str) -> dict:
        if self._loader.is_social_using_fallback or self._loader.social_sentiment_model is None:
            return self._fallback._rule_based_fallback(text)
        return self._predict_visobert(text)


class TopicPredictor:
    """Dự đoán chủ đề (multi-label) cho văn bản tài chính tiếng Việt."""

    def __init__(self, model_loader: ModelLoader) -> None:
        self._loader = model_loader

    def predict(self, text: str) -> dict:
        """
        Dự đoán phân phối chủ đề cho một đoạn text.

        Args:
            text: Văn bản tiếng Việt.

        Returns:
            Dict với 'topics' (list nhãn vượt ngưỡng) và 'topic_distribution'.
        """
        if self._loader.is_topic_using_fallback or self._loader.topic_model is None:
            return self._fallback_topic(text)

        tokenizer = self._loader.topic_tokenizer
        model = self._loader.topic_model
        device = next(model.parameters()).device

        encoding = tokenizer(
            text,
            max_length=MAX_TOKENS,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        with torch.no_grad():
            logits = model(
                input_ids=encoding["input_ids"].to(device),
                attention_mask=encoding["attention_mask"].to(device),
            ).logits
            probs = torch.sigmoid(logits).cpu().squeeze(0).tolist()

        distribution = {topic: round(probs[i], 4) for i, topic in enumerate(TOPICS)}
        active_topics = [t for t, p in distribution.items() if p >= TOPIC_THRESHOLD]

        return {
            "topics": active_topics or ["Khác"],
            "topic_distribution": distribution,
        }

    def _fallback_topic(self, text: str) -> dict:
        """Fallback topic khi chưa có model: trả về 'Khác' với prob 1.0."""
        distribution = {topic: 0.0 for topic in TOPICS}
        distribution["Khác"] = 1.0
        return {
            "topics": ["Khác"],
            "topic_distribution": distribution,
        }
