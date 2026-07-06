"""
llm_labeler.py — Gán nhãn tự động bằng LLM.

Input:  DataFrame với cột 'article_id', 'title', 'raw_content'.
Output: DataFrame bổ sung các cột nhãn sentiment, topic và impact từ LLM.

Chọn provider qua biến môi trường:
  LLM_PROVIDER=gemini  → dùng Gemini 1.5 Flash (miễn phí, cần GEMINI_API_KEY)
  LLM_PROVIDER=openai  → dùng GPT-4o-mini (trả phí, cần OPENAI_API_KEY)
  LLM_PROVIDER=deepseek → dùng DeepSeek OpenAI-compatible API (cần DEEPSEEK_API_KEY)
  Mặc định: deepseek nếu có DEEPSEEK_API_KEY, sau đó gemini nếu có GEMINI_API_KEY,
            ngược lại dùng openai.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Nhãn sentiment hợp lệ
VALID_SENTIMENT_LABELS = {"positive", "negative", "neutral"}

# Chủ đề hợp lệ
VALID_TOPICS = {
    "Chính sách tiền tệ",
    "Kết quả kinh doanh",
    "M&A",
    "Biến động vĩ mô",
    "Tin đồn thị trường",
    "Khác",
}

VALID_IMPACT_LABELS = {"High", "Medium", "Low", "None"}

SYSTEM_PROMPT = (
    "Bạn là chuyên gia phân tích thị trường chứng khoán Việt Nam "
    "với 10 năm kinh nghiệm. Hãy đánh giá tác động kỳ vọng của thông tin "
    "đối với doanh nghiệp niêm yết hoặc thị trường, không đánh giá giọng văn. "
    "Chỉ dùng positive khi thông tin có tác động tài chính thuận lợi rõ ràng, "
    "negative khi có tác động bất lợi rõ ràng; dùng neutral cho thông báo, "
    "tin hành chính, nội dung hai chiều hoặc không có tác động định hướng rõ. "
    "Nhiệm vụ là gán nhãn cảm xúc, chủ đề và mức độ tác động một cách "
    "chính xác, nhất quán."
)

USER_PROMPT_TEMPLATE = """Phân tích bài báo tài chính sau:
{text}

Trả về JSON với format CHÍNH XÁC (không thêm gì khác):
{{
  "article_id": "{article_id}",
  "sentiment_label": "<positive|negative|neutral>",
  "sentiment_score": <float -1.0 đến 1.0>,
  "confidence": <float 0.0 đến 1.0>,
  "impact_label": "<High|Medium|Low|None>",
  "impact_score": <float 0.0 đến 1.0>,
  "topics": ["<chỉ chọn trong: Chính sách tiền tệ|Kết quả kinh doanh|M&A|Biến động vĩ mô|Tin đồn thị trường|Khác>"],
  "topic_distribution": {{
    "Chính sách tiền tệ": 0.0,
    "Kết quả kinh doanh": 0.0,
    "M&A": 0.0,
    "Biến động vĩ mô": 0.0,
    "Tin đồn thị trường": 0.0,
    "Khác": 0.0
  }},
  "reasoning": "<giải thích ngắn 1-2 câu>"
}}"""

MAX_RETRIES = 3
CHECKPOINT_EVERY = int(os.getenv("LABEL_CHECKPOINT_EVERY", "10"))


def _validate_label(result: dict) -> bool:
    """Kiểm tra kết quả từ LLM có hợp lệ không."""
    if result.get("sentiment_label") not in VALID_SENTIMENT_LABELS:
        return False

    score = result.get("sentiment_score")
    if not isinstance(score, (int, float)) or not (-1.0 <= score <= 1.0):
        return False

    confidence = result.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        return False

    if result.get("impact_label") not in VALID_IMPACT_LABELS:
        return False

    impact_score = result.get("impact_score")
    if not isinstance(impact_score, (int, float)) or not (0.0 <= impact_score <= 1.0):
        return False

    topics = result.get("topics")
    if (
        not isinstance(topics, list)
        or not topics
        or any(topic not in VALID_TOPICS for topic in topics)
    ):
        return False

    dist = result.get("topic_distribution", {})
    if not isinstance(dist, dict) or set(dist) != VALID_TOPICS:
        return False
    if any(not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0 for value in dist.values()):
        return False
    total = sum(dist.values())
    if not (0.85 <= total <= 1.15):  # cho phép sai số nhỏ
        return False

    return True


def _call_openai(user_prompt: str) -> str:
    """Gọi OpenAI Chat Completions, trả về chuỗi JSON thô."""
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def _call_deepseek(user_prompt: str) -> str:
    """Gọi DeepSeek qua OpenAI-compatible Chat Completions API."""
    import openai

    client = openai.OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    response = client.chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def _call_gemini(user_prompt: str) -> str:
    """Gọi Gemini Flash (dùng google-genai SDK mới), trả về chuỗi JSON thô."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    # Thứ tự ưu tiên — dùng tên chính xác từ list_models() của API key này
    candidate_models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-3.1-flash-lite-preview",
        "gemini-3-flash-preview",
        "gemini-2.0-flash-lite",
    ]

    last_exc = None
    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            logger.debug("Dùng model Gemini: %s", model_name)
            return response.text
        except Exception as exc:
            exc_str = str(exc)
            if "404" in exc_str or "not found" in exc_str.lower():
                # Model không tồn tại → thử model tiếp theo
                last_exc = exc
                continue
            if "503" in exc_str or "unavailable" in exc_str.lower() or "overloaded" in exc_str.lower():
                # Model quá tải → chờ rồi thử model tiếp theo
                logger.warning("Model '%s' quá tải, thử model tiếp theo...", model_name)
                time.sleep(3)
                last_exc = exc
                continue
            raise

    raise RuntimeError(
        f"Không có model Gemini nào khả dụng. Thử cuối: {last_exc}"
    )


def _get_provider() -> str:
    """Xác định provider: deepseek, gemini hoặc openai."""
    explicit = os.getenv("LLM_PROVIDER", "").lower()
    if explicit in ("deepseek", "gemini", "openai"):
        return explicit
    if os.getenv("DEEPSEEK_API_KEY"):
        return "deepseek"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    return "openai"


def label_article(text: str, article_id: str) -> Optional[dict]:
    """
    Gán nhãn một bài báo bằng LLM (Gemini hoặc OpenAI).

    Args:
        text:       Văn bản đã qua extract_labeling_input().
        article_id: ID bài báo để điền vào JSON.

    Returns:
        Dict kết quả nhãn, hoặc None nếu thất bại sau MAX_RETRIES lần.
    """
    provider = _get_provider()
    user_prompt = USER_PROMPT_TEMPLATE.format(text=text, article_id=article_id)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if provider == "deepseek":
                raw = _call_deepseek(user_prompt)
            elif provider == "gemini":
                raw = _call_gemini(user_prompt)
            else:
                raw = _call_openai(user_prompt)

            result = json.loads(raw)

            if not _validate_label(result):
                logger.warning(
                    "Nhãn không hợp lệ cho article_id='%s' (lần %d): %s",
                    article_id, attempt, result,
                )
                if attempt < MAX_RETRIES:
                    continue
                return None

            return result

        except Exception as exc:
            logger.warning(
                "Lỗi API [%s] article_id='%s' (lần %d/%d): %s",
                provider, article_id, attempt, MAX_RETRIES, exc,
            )
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)

    return None


def batch_label(
    df: pd.DataFrame,
    output_dir: str,
    delay: float = 0.5,
) -> pd.DataFrame:
    """
    Gán nhãn toàn bộ DataFrame và lưu checkpoint sau mỗi CHECKPOINT_EVERY bài.

    Args:
        df:         DataFrame với cột 'article_id', 'title', 'raw_content'.
        output_dir: Thư mục lưu checkpoint JSON.
        delay:      Giây nghỉ giữa các request để tránh rate limit.

    Returns:
        DataFrame bổ sung các cột nhãn. Những bài thất bại bị loại.
    """
    from nlp.data_preparation.text_cleaner import extract_labeling_input

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    checkpoint_file = out_path / "checkpoint.json"
    failed_file = out_path / "failed.json"

    # Tiếp tục từ checkpoint nếu có
    labeled: list[dict] = []
    failed: list[str] = []
    done_ids: set[str] = set()

    if checkpoint_file.exists():
        with open(checkpoint_file, encoding="utf-8") as f:
            labeled = json.load(f)
        done_ids = {r["article_id"] for r in labeled}
        logger.info("Tiếp tục từ checkpoint: %d bài đã xử lý.", len(done_ids))

    remaining = df[~df["article_id"].isin(done_ids)]
    logger.info("Còn %d bài cần gán nhãn.", len(remaining))

    for i, (_, row) in enumerate(remaining.iterrows(), start=1):
        text = extract_labeling_input(row.get("title", ""), row["raw_content"])
        result = label_article(text, row["article_id"])

        if result is not None:
            labeled.append(result)
        else:
            failed.append(row["article_id"])

        # Lưu checkpoint mỗi CHECKPOINT_EVERY bài
        if i % CHECKPOINT_EVERY == 0:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(labeled, f, ensure_ascii=False, indent=2)
            logger.info("Checkpoint: %d/%d bài hoàn tất.", len(labeled), len(df))

        time.sleep(delay)

    # Lưu checkpoint cuối
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(labeled, f, ensure_ascii=False, indent=2)

    if failed:
        with open(failed_file, "w", encoding="utf-8") as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)

    logger.info(
        "Hoàn tất gán nhãn: %d thành công, %d thất bại.",
        len(labeled), len(failed),
    )

    labeled_df = pd.DataFrame(labeled)
    return df.merge(labeled_df, on="article_id", how="inner")
