import re
import time

import requests

# 非公式の Google 翻訳窓口（Chrome 拡張機能用）。translate.google.com/m は CAPTCHA でブロックされるためこちらを使う
ENDPOINT = "https://clients5.google.com/translate_a/t"
MAX_CHARS = 4500
JA_RE = re.compile(r"[぀-ヿ]")


def is_japanese(text):
    return bool(JA_RE.search(text or ""))


def _request(text):
    for attempt in range(3):
        try:
            resp = requests.post(
                ENDPOINT,
                params={"client": "dict-chrome-ex", "sl": "auto", "tl": "ja"},
                data={"q": text},
                timeout=30,
            )
            resp.raise_for_status()
            resp.encoding = "utf-8"
            first = resp.json()[0]
            return first[0] if isinstance(first, list) else first
        except (requests.RequestException, ValueError, IndexError):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def _split_long(paragraph):
    while len(paragraph) > MAX_CHARS:
        cut = paragraph.rfind(". ", 0, MAX_CHARS)
        cut = cut + 1 if cut > 0 else MAX_CHARS
        yield paragraph[:cut]
        paragraph = paragraph[cut:].lstrip()
    if paragraph:
        yield paragraph


def _chunks(text):
    chunk = ""
    for para in text.split("\n"):
        for piece in _split_long(para):
            if chunk and len(chunk) + len(piece) + 1 > MAX_CHARS:
                yield chunk
                chunk = piece
            else:
                chunk = f"{chunk}\n{piece}" if chunk else piece
    if chunk:
        yield chunk


def to_japanese(text):
    if not text or not text.strip() or is_japanese(text):
        return text or ""
    return "\n".join(_request(c) for c in _chunks(text))


def translate_pair(title, summary):
    """タイトルと要約を1回のリクエストでまとめて翻訳する（空行区切りが保たれることを利用）。"""
    if not summary:
        return to_japanese(title), ""
    if is_japanese(title) or is_japanese(summary):
        return to_japanese(title), to_japanese(summary)
    combined = to_japanese(f"{title}\n\n{summary}")
    if "\n\n" in combined:
        title_ja, summary_ja = combined.split("\n\n", 1)
        return title_ja.strip(), summary_ja.strip()
    return to_japanese(title), to_japanese(summary)
