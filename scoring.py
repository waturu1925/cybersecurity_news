# 基本スコアは収集時に保存し、新しさと複数ソース報道は時間とともに変わるため表示時に加味する
import re
from collections import defaultdict

import config

CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)
CVSS_RE = re.compile(r"CVSS[^0-9]{0,25}(\d{1,2}(?:\.\d)?)", re.IGNORECASE)
_POPULAR_RE = re.compile(rf"\b(?:{config.POPULAR_PRODUCTS})\b", re.IGNORECASE)

_RULES = {
    name: {
        "keywords": [(re.compile(p, re.IGNORECASE), pts, label) for p, pts, label in ch["keyword_rules"]],
        "categories": [(label, re.compile(p, re.IGNORECASE)) for label, p in ch["categories"]],
    }
    for name, ch in config.CHANNELS.items()
}


def extract_cves(text):
    return sorted({c.upper() for c in CVE_RE.findall(text)})


def categorize(text, channel):
    for name, pattern in _RULES[channel]["categories"]:
        if pattern.search(text):
            return name
    return "その他"


def base_score(text, channel, source_name="", source_bonus=0, kev=None):
    ch = config.CHANNELS[channel]
    reasons = []

    if kev:
        reasons.append({"label": "CISA KEV に登録（米政府が実際の悪用を確認した脆弱性）", "points": 45})
        if kev.get("ransomware") == "Known":
            reasons.append({"label": "ランサムウェア攻撃での悪用が判明", "points": 15})

    keyword_total = 0
    for pattern, points, label in _RULES[channel]["keywords"]:
        if pattern.search(text):
            points = min(points, ch["keyword_cap"] - keyword_total)
            if points <= 0:
                break
            keyword_total += points
            reasons.append({"label": label, "points": points})

    if ch["product_bonus"]:
        product = _POPULAR_RE.search(text)
        if product:
            reasons.append({"label": f"広く使われている製品・サービス（{product.group(0)}）", "points": config.POPULAR_PRODUCTS_POINTS})

    if ch["cvss_bonus"]:
        cvss = [float(v) for v in CVSS_RE.findall(text) if float(v) <= 10]
        if cvss:
            top = max(cvss)
            if top >= 9:
                reasons.append({"label": f"CVSS スコア {top}（最も深刻なレベル）", "points": 15})
            elif top >= 7:
                reasons.append({"label": f"CVSS スコア {top}（深刻度 高）", "points": 8})

    if source_bonus:
        reasons.append({"label": ch["bonus_label"].format(source=source_name), "points": source_bonus})

    return min(100, sum(r["points"] for r in reasons)), reasons


def cve_source_counts(items):
    sources = defaultdict(set)
    for item in items:
        for cve in item["cves"]:
            sources[cve].add(item["source"])
    return {cve: len(s) for cve, s in sources.items()}


def _recency(item, now):
    hours = (now - item["published"]).total_seconds() / 3600
    if hours <= 24:
        return 1.0, "24時間以内"
    if hours <= 72:
        return 0.95, "3日以内"
    if hours <= 168:
        return 0.85, "1週間以内"
    if hours <= 720:
        return 0.7, "30日以内"
    return 0.6, "30日より前"


def level_of(score, channel):
    levels = config.CHANNELS[channel]["levels"]
    for threshold, label, css in levels:
        if score >= threshold:
            return label, css
    return levels[-1][1], levels[-1][2]


def evaluate(item, cve_counts, now):
    factor, recency_label = _recency(item, now)
    coverage = max((cve_counts.get(c, 1) for c in item["cves"]), default=1)
    coverage_bonus = min(15, 5 * (coverage - 1))

    score = min(100, round(item["base_score"] * factor + coverage_bonus))
    item["score"] = score
    item["level"], item["level_class"] = level_of(score, item["channel"])
    item["recency_factor"] = factor
    item["recency_label"] = recency_label
    item["coverage"] = coverage
    item["coverage_bonus"] = coverage_bonus
    return item
