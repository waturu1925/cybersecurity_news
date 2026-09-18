import logging
import os
import re
from datetime import date, datetime, timedelta, timezone

import requests

import config
from curated_events import CURATED_EVENTS

log = logging.getLogger(__name__)
JST = timezone(timedelta(hours=9))
HEADERS = {"User-Agent": config.USER_AGENT}
WEEKDAYS = "月火水木金土日"

_TITLE_RE = re.compile(config.EVENT_TITLE_PATTERN, re.IGNORECASE)
_NEARBY_RE = re.compile(config.NEARBY_AREA_PATTERN)
_ONLINE_RE = re.compile(r"オンライン|online|zoom|youtube|teams|ウェビナー|webinar|配信|Web ?セミナー", re.IGNORECASE)


def _classify(title, venue, address):
    place = f"{venue} {address}"
    if _NEARBY_RE.search(place):
        return "nearby"
    if _ONLINE_RE.search(place) or not place.strip() or _ONLINE_RE.search(title):
        return "online"
    return "other"


def _doorkeeper(today):
    found = {}
    for word in config.EVENT_SEARCH_WORDS:
        resp = requests.get(
            "https://api.doorkeeper.jp/events",
            params={"q": word, "sort": "starts_at", "since": today.isoformat()},
            headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        for row in resp.json():
            e = row["event"]
            if not _TITLE_RE.search(e["title"]) or not e.get("public_url", "").startswith("https://"):
                continue
            venue, address = e.get("venue_name") or "", e.get("address") or ""
            found[e["public_url"]] = {
                "name": e["title"].strip(),
                "start": datetime.fromisoformat(e["starts_at"].replace("Z", "+00:00")).astimezone(JST),
                "venue": " ".join(p for p in (venue, address) if p) or "オンライン",
                "area": _classify(e["title"], venue, address),
                "url": e["public_url"],
                "source": "Doorkeeper",
                "participants": e.get("participants"),
                "limit": e.get("ticket_limit"),
            }
    return list(found.values())


def _connpass(today, api_key):
    # connpass API v2 は API キー（無料申請）が必要。キーが無ければ呼ばない
    resp = requests.get(
        "https://connpass.com/api/v2/events/",
        params={"keyword_or": config.EVENT_SEARCH_WORDS, "order": 2, "count": 100,
                "ym": [today.strftime("%Y%m"), (today.replace(day=1) + timedelta(days=32)).strftime("%Y%m")]},
        headers={**HEADERS, "X-API-Key": api_key}, timeout=20,
    )
    resp.raise_for_status()
    events = []
    for e in resp.json().get("events", []):
        url = e.get("url") or ""
        if not url.startswith("https://") or not _TITLE_RE.search(e.get("title", "")):
            continue
        start = datetime.fromisoformat(e["started_at"]).astimezone(JST)
        if start.date() < today:
            continue
        venue, address = e.get("place") or "", e.get("address") or ""
        events.append({
            "name": e["title"].strip(),
            "start": start,
            "venue": " ".join(p for p in (venue, address) if p) or "オンライン",
            "area": _classify(e["title"], venue, address),
            "url": url,
            "source": "connpass",
            "participants": e.get("accepted"),
            "limit": e.get("limit"),
        })
    return events


def _with_labels(event, start, end, today):
    event["date_label"] = f"{start.month}/{start.day}（{WEEKDAYS[start.weekday()]}）"
    if end and end != start:
        event["date_label"] += f" 〜 {end.month}/{end.day}（{WEEKDAYS[end.weekday()]}）"
    event["days_left"] = (start - today).days
    return event


def _curated(today):
    upcoming, undecided = [], []
    for raw in CURATED_EVENTS:
        event = dict(raw)
        if not event["start"]:
            undecided.append(event)
            continue
        start = date.fromisoformat(event["start"])
        end = date.fromisoformat(event["end"] or event["start"])
        if end < today:
            continue
        event["ongoing"] = start <= today <= end
        upcoming.append(_with_labels(event, start, end, today))
    upcoming.sort(key=lambda e: e["start"])
    return upcoming, undecided


def load_events():
    today = datetime.now(JST).date()
    fetched = []
    try:
        fetched += _doorkeeper(today)
    except Exception as exc:
        log.warning("Doorkeeper からのイベント取得に失敗しました: %s", exc)
    api_key = os.environ.get("CONNPASS_API_KEY")
    if api_key:
        try:
            fetched += _connpass(today, api_key)
        except Exception as exc:
            log.warning("connpass からのイベント取得に失敗しました: %s", exc)

    seen, community = set(), []
    for e in sorted(fetched, key=lambda e: e["start"]):
        key = (e["name"], e["start"].date())
        if key in seen:
            continue
        seen.add(key)
        community.append(_with_labels(e, e["start"].date(), None, today))
    for e in community:
        e["time_label"] = e["start"].strftime("%H:%M")

    curated, undecided = _curated(today)
    return {
        "nearby": [e for e in curated if e["area"] == "nearby"],
        "nearby_undecided": [e for e in undecided if e["area"] == "nearby"],
        "major": [e for e in curated if e["area"] == "major"],
        "major_undecided": [e for e in undecided if e["area"] == "major"],
        "community_nearby": [e for e in community if e["area"] == "nearby"],
        "community_online": [e for e in community if e["area"] == "online"][:20],
        "community_other": [e for e in community if e["area"] == "other"][:15],
        "connpass_enabled": bool(api_key),
    }
