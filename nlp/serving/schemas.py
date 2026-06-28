"""
schemas.py — Pydantic schemas cho FastAPI request/response.

Định nghĩa toàn bộ kiểu dữ liệu cho NLP serving API.
"""

from typing import Dict, List

from pydantic import BaseModel, Field
from pydantic import ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class ArticleRequest(ApiModel):
    article_id: str
    content: str
    title: str = ""
    source_type: str = "article"
    platform: str = ""


class SentimentResponse(ApiModel):
    article_id: str
    sentiment_label: str
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    is_low_confidence: bool
    model_version: str
    processing_time_ms: float


class TopicResponse(ApiModel):
    article_id: str
    topics: List[str]
    topic_distribution: Dict[str, float]
    model_version: str


class FullPredictionResponse(ApiModel):
    article_id: str
    sentiment: SentimentResponse
    topic: TopicResponse


class BatchRequest(ApiModel):
    articles: List[ArticleRequest]
    max_batch_size: int = 32
