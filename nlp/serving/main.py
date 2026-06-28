"""
main.py — FastAPI app cho NLP serving trên Oracle VM.

Endpoints:
  GET  /health            — trạng thái service và model
  GET  /model/info        — thông tin chi tiết về model
  POST /predict/sentiment — phân loại cảm xúc đơn lẻ
  POST /predict/topic     — gán nhãn chủ đề đơn lẻ
  POST /predict/full      — sentiment + topic cùng lúc
  POST /predict/batch     — batch inference (tối đa 32 bài)

SLA: < 500ms/bài với CPU inference.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

try:
    from nlp.serving.model_loader import ModelLoader
    from nlp.serving.predictor import SentimentPredictor, SocialSentimentPredictor, TopicPredictor
    from nlp.serving.schemas import (
        ArticleRequest,
        BatchRequest,
        FullPredictionResponse,
        SentimentResponse,
        TopicResponse,
    )
except ImportError:
    # Chạy standalone: cd nlp/serving && uvicorn main:app
    from model_loader import ModelLoader
    from predictor import SentimentPredictor, SocialSentimentPredictor, TopicPredictor
    from schemas import (
        ArticleRequest,
        BatchRequest,
        FullPredictionResponse,
        SentimentResponse,
        TopicResponse,
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Singleton model loader, khởi tạo 1 lần khi startup
_model_loader: ModelLoader = None
_sentiment_predictor: SentimentPredictor = None
_social_sentiment_predictor: SocialSentimentPredictor = None
_topic_predictor: TopicPredictor = None


def _is_social_article(article: ArticleRequest) -> bool:
    source_type = (article.source_type or "").lower()
    platform = (article.platform or "").lower()
    return source_type in {"comment", "post", "social"} or platform in {"youtube", "tiktok", "facebook", "fireant"}


def _select_sentiment_predictor(article: ArticleRequest):
    return _social_sentiment_predictor if _is_social_article(article) else _sentiment_predictor


def _selected_model_version(article: ArticleRequest) -> str:
    if _is_social_article(article):
        return _model_loader.social_model_version
    return _model_loader.model_version


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model khi startup, không raise exception nếu model chưa có."""
    global _model_loader, _sentiment_predictor, _social_sentiment_predictor, _topic_predictor

    logger.info("Khởi động NLP serving...")
    _model_loader = ModelLoader()
    _sentiment_predictor = SentimentPredictor(_model_loader)
    _social_sentiment_predictor = SocialSentimentPredictor(_model_loader)
    _topic_predictor = TopicPredictor(_model_loader)

    if _model_loader.is_using_fallback:
        logger.warning(
            "PhoBERT model chưa load được. Đang dùng rule-based fallback. "
            "Upload model lên HuggingFace Hub và restart để kích hoạt PhoBERT."
        )
    else:
        logger.info("PhoBERT models loaded, version=%s", _model_loader.model_version)

    yield

    logger.info("Shutdown NLP serving.")


app = FastAPI(
    title="FiNTA NLP Service",
    description="Sentiment analysis và topic labeling cho tin tức tài chính Việt Nam.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: cho phép tất cả origins (Spark và Streamlit gọi từ nơi khác)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log mỗi request với processing time."""
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info("%s %s → %d (%.1fms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


# ──────────────────────────────────────────────────────────────
# Health & Info
# ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": not _model_loader.is_using_fallback,
        "social_model_loaded": not _model_loader.is_social_using_fallback,
        "is_fallback": _model_loader.is_using_fallback,
        "is_social_fallback": _model_loader.is_social_using_fallback,
        "is_topic_fallback": _model_loader.is_topic_using_fallback,
        "model_version": _model_loader.model_version,
        "social_model_version": _model_loader.social_model_version,
    }


@app.get("/model/info")
def model_info():
    info = _model_loader.get_model_info()
    return info


# ──────────────────────────────────────────────────────────────
# Prediction endpoints
# ──────────────────────────────────────────────────────────────

@app.post("/predict/sentiment", response_model=SentimentResponse)
def predict_sentiment(article: ArticleRequest):
    """Phân loại cảm xúc. Mục tiêu < 500ms/bài với CPU."""
    start = time.time()
    try:
        text = f"Tiêu đề: {article.title}\n\n{article.content}" if article.title else article.content
        result = _select_sentiment_predictor(article).predict(text)
    except Exception as exc:
        logger.error("Lỗi inference sentiment article_id=%s: %s", article.article_id, exc)
        raise HTTPException(status_code=500, detail=f"Lỗi inference: {exc}")

    processing_ms = (time.time() - start) * 1000
    logger.info("sentiment article_id=%s label=%s conf=%.2f time=%.1fms",
                article.article_id, result["sentiment_label"],
                result["confidence_score"], processing_ms)

    return SentimentResponse(
        article_id=article.article_id,
        model_version=_selected_model_version(article),
        processing_time_ms=round(processing_ms, 1),
        **result,
    )


@app.post("/predict/topic", response_model=TopicResponse)
def predict_topic(article: ArticleRequest):
    """Gán nhãn chủ đề (multi-label)."""
    start = time.time()
    try:
        text = f"Tiêu đề: {article.title}\n\n{article.content}" if article.title else article.content
        result = _topic_predictor.predict(text)
    except Exception as exc:
        logger.error("Lỗi inference topic article_id=%s: %s", article.article_id, exc)
        raise HTTPException(status_code=500, detail=f"Lỗi inference: {exc}")

    processing_ms = (time.time() - start) * 1000
    logger.info("topic article_id=%s topics=%s time=%.1fms",
                article.article_id, result["topics"], processing_ms)

    return TopicResponse(
        article_id=article.article_id,
        model_version=_model_loader.model_version,
        **result,
    )


@app.post("/predict/full", response_model=FullPredictionResponse)
def predict_full(article: ArticleRequest):
    """Sentiment + topic cùng lúc."""
    start = time.time()
    try:
        text = f"Tiêu đề: {article.title}\n\n{article.content}" if article.title else article.content
        sentiment_result = _select_sentiment_predictor(article).predict(text)
        topic_result = _topic_predictor.predict(text)
    except Exception as exc:
        logger.error("Lỗi inference full article_id=%s: %s", article.article_id, exc)
        raise HTTPException(status_code=500, detail=f"Lỗi inference: {exc}")

    processing_ms = (time.time() - start) * 1000

    return FullPredictionResponse(
        article_id=article.article_id,
        sentiment=SentimentResponse(
            article_id=article.article_id,
            model_version=_selected_model_version(article),
            processing_time_ms=round(processing_ms, 1),
            **sentiment_result,
        ),
        topic=TopicResponse(
            article_id=article.article_id,
            model_version=_model_loader.model_version,
            **topic_result,
        ),
    )


@app.post("/predict/batch", response_model=List[FullPredictionResponse])
def predict_batch(batch_request: BatchRequest):
    """
    Batch inference tối đa 32 bài.
    Dùng cho Spark UDF gọi theo batch.
    """
    articles = batch_request.articles[:batch_request.max_batch_size]

    results = []
    for article in articles:
        start = time.time()
        try:
            text = f"Tiêu đề: {article.title}\n\n{article.content}" if article.title else article.content
            sentiment_result = _select_sentiment_predictor(article).predict(text)
            topic_result = _topic_predictor.predict(text)
            processing_ms = (time.time() - start) * 1000

            results.append(FullPredictionResponse(
                article_id=article.article_id,
                sentiment=SentimentResponse(
                    article_id=article.article_id,
                    model_version=_selected_model_version(article),
                    processing_time_ms=round(processing_ms, 1),
                    **sentiment_result,
                ),
                topic=TopicResponse(
                    article_id=article.article_id,
                    model_version=_model_loader.model_version,
                    **topic_result,
                ),
            ))
        except Exception as exc:
            logger.error("Lỗi batch inference article_id=%s: %s", article.article_id, exc)
            raise HTTPException(status_code=500, detail=f"Lỗi inference bài {article.article_id}: {exc}")

    logger.info("Batch inference: %d bài hoàn tất.", len(results))
    return results
