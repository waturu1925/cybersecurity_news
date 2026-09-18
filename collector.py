import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import feedparser
import requests
import trafilatura

import config
import db
import scoring
import translator

log = logging.getLogger(__name__)
HEADERS = {"User-Agent": config.USER_AGENT}


def _clean(text):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _entry_time(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime(*parsed[:6], tzinfo=timezone.utc) if parsed else None


def _entry_summary(entry):
    summary = entry.get("summary")
    if not summary and entry.get("content"):
        summary = entry["content"][0].get("value")
    return _clean(summary)[:1500]


def fetch_feed(feed, channel, cutoff, now):
    resp = requests.get(feed["url"], headers=HEADERS, timeout=20)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)
    items = []
    for entry in parsed.entries[:feed.get("max", config.MAX_ITEMS_PER_FEED)]:
        url, title = entry.get("link"), _clean(entry.get("title"))
        # リンクは画面にそのまま埋め込むため、javascript: などの不正なスキームを除外する
        if not url or not url.startswith(("http://", "https://")) or not title:
            continue
        published = min(_entry_time(entry) or now, now)
        if published < cutoff:
            continue
        items.append({
            "url": url,
            "channel": channel,
            "source": feed["name"],
            "kind": "news",
            "title_orig": title,
            "summary_orig": _entry_summary(entry),
            "published": published,
            "extra": {},
        })
    return items


def fetch_kev(cutoff):
    resp = requests.get(config.KEV_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    items = []
    for v in resp.json()["vulnerabilities"]:
        added = datetime.fromisoformat(v["dateAdded"]).replace(tzinfo=timezone.utc)
        if added < cutoff:
            continue
        items.append({
            "url": f"https://nvd.nist.gov/vuln/detail/{v['cveID']}",
            "channel": "news",
            "source": "CISA KEV",
            "kind": "kev",
            "title_orig": f"{v['vulnerabilityName']} ({v['cveID']})",
            "summary_orig": f"{v['shortDescription']}\nRequired action: {v['requiredAction']}",
            "published": added,
            "extra": {
                "cve": v["cveID"],
                "vendor": v["vendorProject"],
                "product": v["product"],
                "due_date": v.get("dueDate"),
                "ransomware": v.get("knownRansomwareCampaignUse"),
                "cwes": v.get("cwes", []),
            },
        })
    return items


_SOURCE_BONUS = {f["name"]: f.get("bonus", 0) for ch in config.CHANNELS.values() for f in ch["feeds"]}


def _score(item):
    text = f"{item['title_orig']} {item['summary_orig']}"
    kev = item["extra"] if item["kind"] == "kev" else None
    item["base_score"], item["reasons"] = scoring.base_score(
        text, item["channel"], item["source"], _SOURCE_BONUS.get(item["source"], 0), kev
    )
    if item["kind"] == "kev":
        item["category"] = "脆弱性"
    else:
        category = scoring.categorize(item["title_orig"], item["channel"])
        item["category"] = category if category != "その他" else scoring.categorize(text, item["channel"])
    item["cves"] = scoring.extract_cves(text)


def rescore_all():
    for item in db.items_since(datetime.min.replace(tzinfo=timezone.utc)):
        _score(item)
        db.update_score(item)


def _translate_pending():
    pending = db.untranslated()
    if not pending:
        return

    def work(row):
        title_ja, summary_ja = translator.translate_pair(row["title_orig"], row["summary_orig"])
        db.set_translation(row["id"], title_ja, summary_ja)

    failed = 0
    with ThreadPoolExecutor(config.TRANSLATE_WORKERS) as pool:
        for future in as_completed([pool.submit(work, row) for row in pending]):
            if future.exception():
                failed += 1
    log.info("翻訳: %d 件（失敗 %d 件は次回再試行）", len(pending), failed)


def collect():
    now = datetime.now(timezone.utc)
    cutoffs = {name: now - timedelta(days=ch["keep_days"]) for name, ch in config.CHANNELS.items()}
    collected = []

    with ThreadPoolExecutor(8) as pool:
        futures = {}
        for name, ch in config.CHANNELS.items():
            for feed in ch["feeds"]:
                futures[pool.submit(fetch_feed, feed, name, cutoffs[name], now)] = feed["name"]
            if ch["include_kev"]:
                futures[pool.submit(fetch_kev, cutoffs[name])] = "CISA KEV"
        for future in as_completed(futures):
            try:
                collected += future.result()
            except Exception as exc:
                log.warning("%s の取得に失敗しました: %s", futures[future], exc)

    known = db.existing_urls([i["url"] for i in collected])
    added = 0
    for item in collected:
        if item["url"] in known:
            continue
        known.add(item["url"])
        _score(item)
        db.insert(item)
        added += 1
    log.info("収集: %d 件取得、うち新規 %d 件", len(collected), added)

    _translate_pending()
    for name, cutoff in cutoffs.items():
        db.purge_before(cutoff, name)
    db.set_meta("last_collected", now.isoformat())


def fetch_body_ja(item):
    resp = requests.get(item["url"], headers=HEADERS, timeout=20)
    resp.raise_for_status()
    text = trafilatura.extract(resp.text, include_comments=False, include_tables=False) or ""
    return translator.to_japanese(text[:config.BODY_MAX_CHARS].strip())


def prefetch_bodies(items):
    """本文未取得の記事の本文を翻訳して保存する。失敗した記事は空文字を保存して再試行しない。"""
    targets = [i for i in items if i["kind"] != "kev" and i["body_ja"] is None]

    def work(item):
        try:
            body = fetch_body_ja(item)
        except Exception as exc:
            log.warning("本文の取得に失敗しました（%s）: %s", item["url"], exc)
            body = ""
        db.set_body(item["id"], body)
        item["body_ja"] = body

    with ThreadPoolExecutor(4) as pool:
        list(pool.map(work, targets))
    log.info("本文翻訳: %d 件", len(targets))
