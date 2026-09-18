# 重要ニュースの上位を LINE に送る。トークン未設定時は送信せず内容を表示するだけ（動作確認用）
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

import build
import config

log = logging.getLogger("notify")
JST = timezone(timedelta(hours=9))
WEEKDAYS = "月火水木金土日"
PUSH_URL = "https://api.line.me/v2/bot/message/push"
BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"


def _shorten(text, limit):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def build_message(site_url):
    items = build.ranked("news", 1)
    if len(items) < config.LINE_TOP_N:
        items = build.ranked("news", 3)
    today = datetime.now(JST)
    lines = [
        "【SEC//INTEL】今日の重要ニュース TOP3",
        f"{today.month}/{today.day}（{WEEKDAYS[today.weekday()]}）のまとめ",
    ]
    for rank, item in enumerate(items[:config.LINE_TOP_N], 1):
        lines += [
            "",
            f"■ {rank}位［{item['level']}］重要度 {item['score']}",
            _shorten(item["title_ja"] or item["title_orig"], 80),
            f"要約: {_shorten(item['summary_ja'] or item['summary_orig'], 110)}",
            f"→ {site_url}items/{item['id']}.html",
        ]
    lines += ["", "▼ ランキング全体を見る", f"{site_url}news/"]
    return "\n".join(lines)


def main():
    site_url = os.environ.get("SITE_URL", "http://127.0.0.1:8000/").rstrip("/") + "/"
    message = build_message(site_url)
    token, user_id = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"), os.environ.get("LINE_USER_ID")
    if not token:
        print("LINE の設定が無いため送信しません。送信予定の内容:\n")
        print(message)
        return
    messages = [{"type": "text", "text": message}]
    # ユーザーID未設定なら公式アカウントの友だち全員へ一斉送信（友だちが自分だけなら自分にだけ届く）
    url, payload = (PUSH_URL, {"to": user_id, "messages": messages}) if user_id else (BROADCAST_URL, {"messages": messages})
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=20)
    if resp.status_code != 200:
        log.error("LINE への送信に失敗しました: %s %s", resp.status_code, resp.text)
        sys.exit(1)
    log.info("LINE に通知を送信しました")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
