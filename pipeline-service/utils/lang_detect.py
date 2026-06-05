"""
Language detection utility — identifies the primary language of a text.

Used to set the screenplay meta.language field and to select
appropriate chapter-splitting regex patterns.
"""


def detect_language(text: str) -> str:
    """
    Detect the primary language of the given text.

    Args:
        text: input text (first 1000 chars are usually sufficient)

    Returns:
        Language code: "zh" for Chinese, "en" for English.
        Defaults to "zh" if uncertain.
    """
    # TODO: use chardet or a lightweight detection library
    # Simple heuristic: count CJK characters vs ASCII letters
    if not text:
        return "zh"
    cjk_count = sum(1 for ch in text[:1000] if '\u4e00' <= ch <= '\u9fff')
    latin_count = sum(1 for ch in text[:1000] if ch.isascii() and ch.isalpha())
    return "zh" if cjk_count >= latin_count else "en"
