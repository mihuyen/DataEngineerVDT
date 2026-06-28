"""
text_cleaner.py — Làm sạch nhẹ text để LLM đọc được.

Input:  HTML thô từ Bronze Layer.
Output: Chuỗi văn bản sạch, giữ nguyên chữ hoa/thường và dấu câu tiếng Việt.

LƯU Ý: Đây là light cleaning cho LLM labeling, KHÔNG phải Silver Layer
processing — không dùng underthesea, không tokenize tiếng Việt.
"""

import re

# Regex một lần dùng lại để tránh compile lại nhiều lần
_RE_HTML_TAGS = re.compile(r"<[^>]+>")
_RE_SPECIAL_CHARS = re.compile(r"[^\w\s\.,;:!?\-–—()\[\]\"\'""''àáâãèéêìíòóôõùúýăđơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐƠƯẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼẾỀỂỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỬỮỰỲỴỶỸ]", re.UNICODE)
_RE_WHITESPACE = re.compile(r"\s+")


def clean_for_labeling(raw_html: str) -> str:
    """
    Làm sạch nhẹ HTML để LLM có thể đọc.

    Args:
        raw_html: Chuỗi HTML hoặc text thô từ crawler.

    Returns:
        Văn bản đã làm sạch, giữ dấu câu tiếng Việt.
    """
    # Xóa HTML tags
    text = _RE_HTML_TAGS.sub(" ", raw_html)

    # Xóa ký tự đặc biệt không cần thiết, giữ dấu câu và ký tự tiếng Việt
    text = _RE_SPECIAL_CHARS.sub(" ", text)

    # Chuẩn hóa whitespace
    text = _RE_WHITESPACE.sub(" ", text).strip()

    return text


def extract_labeling_input(title: str, content: str, max_chars: int = 800) -> str:
    """
    Tạo chuỗi đầu vào cho LLM labeling từ tiêu đề và nội dung.

    Giới hạn 800 ký tự vì: (1) tiết kiệm token LLM, (2) sentiment
    thường nằm ở đầu bài báo tài chính.

    Args:
        title:     Tiêu đề bài báo (đã làm sạch).
        content:   Nội dung bài báo (đã làm sạch).
        max_chars: Số ký tự tối đa lấy từ content.

    Returns:
        Chuỗi định dạng "Tiêu đề: ...\n\nNội dung: ..." để gửi LLM.
    """
    clean_title = clean_for_labeling(title)
    clean_content = clean_for_labeling(content)
    truncated_content = clean_content[:max_chars]

    return f"Tiêu đề: {clean_title}\n\nNội dung: {truncated_content}"
