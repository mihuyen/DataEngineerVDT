from __future__ import annotations

from nlp.serving.model_loader import canonical_sentiment_label


def test_public_phobert_labels_are_canonicalized() -> None:
    assert canonical_sentiment_label("POS") == "positive"
    assert canonical_sentiment_label("NEG") == "negative"
    assert canonical_sentiment_label("NEU") == "neutral"


def test_project_labels_remain_unchanged() -> None:
    assert canonical_sentiment_label("positive") == "positive"
    assert canonical_sentiment_label("negative") == "negative"
    assert canonical_sentiment_label("neutral") == "neutral"
