# 使い方: python build.py（収集→site/ に生成） / python build.py --no-collect（手元のデータで生成のみ）
import logging
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

from jinja2 import Environment, FileSystemLoader, select_autoescape

import collector
import config
import db
import events
import scoring

log = logging.getLogger("build")
JST = timezone(timedelta(hours=9))
SITE_DIR = config.BASE_DIR / "site"
NOW = datetime.now(timezone.utc)


def _jst(dt):
    return dt.astimezone(JST).strftime("%Y/%m/%d %H:%M")


def _hhmm(dt):
    return dt.astimezone(JST).strftime("%m/%d %H:%M")


def _ago(dt):
    minutes = int((NOW - dt).total_seconds() // 60)
    if minutes < 60:
        return f"{max(minutes, 1)}分前"
    if minutes < 60 * 24:
        return f"{minutes // 60}時間前"
    return f"{minutes // (60 * 24)}日前"


def _env():
    env = Environment(
        loader=FileSystemLoader(config.BASE_DIR / "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(jst=_jst, hhmm=_hhmm, ago=_ago)
    return env


def evaluated(channel, days):
    items = db.items_since(NOW - timedelta(days=days), channel)
    counts = scoring.cve_source_counts(items)
    return [scoring.evaluate(item, counts, NOW) for item in items]


def ranked(channel, days):
    return sorted(evaluated(channel, days), key=lambda i: (i["score"], i["published"]), reverse=True)


def level_counts(channel, items):
    counts = {css: 0 for _, _, css in config.CHANNELS[channel]["levels"]}
    for item in items:
        counts[item["level_class"]] += 1
    return counts


class Site:
    def __init__(self, common):
        self.env = _env()
        self.common = common

    def render(self, template, path, **ctx):
        # GitHub Pages ではサイトがサブフォルダに置かれるため、リンクはすべて相対パスで書く
        root = "../" * path.count("/")
        html = self.env.get_template(template).render(root=root, **self.common, **ctx)
        out = SITE_DIR / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")


def build(do_collect):
    db.init()
    if do_collect:
        collector.collect()
    collector.rescore_all()

    rankings = {name: ranked(name, ch["default_period"]) for name, ch in config.CHANNELS.items()}
    if do_collect:
        for name, items in rankings.items():
            collector.prefetch_bodies(items[:config.BODY_PREFETCH])

    last = db.get_meta("last_collected")
    repo = os.environ.get("GITHUB_REPOSITORY")
    common = {
        "channels": config.CHANNELS,
        "last_collected": datetime.fromisoformat(last) if last else None,
        "built_at": NOW,
        "update_interval": config.UPDATE_INTERVAL_TEXT,
        "update_url": f"https://github.com/{repo}/actions/workflows/update.yml" if repo else None,
    }

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    shutil.copytree(config.BASE_DIR / "static", SITE_DIR / "static")
    (SITE_DIR / ".nojekyll").write_text("")
    site = Site(common)

    event_data = events.load_events()

    summaries = {}
    for name, items in rankings.items():
        summaries[name] = {"top": items[:3], "counts": level_counts(name, items), "total": len(items)}
    latest = sorted(db.items_since(NOW - timedelta(days=2)), key=lambda i: i["published"], reverse=True)[:14]
    stats = {
        "tracked": sum(db.count(name) for name in config.CHANNELS),
        "sources": sum(len(ch["feeds"]) + ch["include_kev"] for ch in config.CHANNELS.values()),
        "critical": summaries["news"]["counts"]["critical"],
        "kev_week": sum(1 for i in db.items_since(NOW - timedelta(days=7), "news") if i["kind"] == "kev"),
    }
    site.render("home.html", "index.html", summaries=summaries, latest=latest, stats=stats,
                events=event_data, theme="home", active="home")

    for name, ch in config.CHANNELS.items():
        for days in ch["periods"]:
            items = ranked(name, days)
            ctx = dict(channel=name, ch=ch, items=items[:config.RANKING_LIMIT], total=len(items),
                       counts=level_counts(name, items), days=days, theme=name, active=name)
            site.render("ranking.html", f"{name}/{days}d.html", **ctx)
            if days == ch["default_period"]:
                site.render("ranking.html", f"{name}/index.html", **ctx)

        for item in evaluated(name, ch["keep_days"] + 1):
            paragraphs = [p.strip() for p in (item["body_ja"] or "").split("\n") if p.strip()]
            site.render("detail.html", f"items/{item['id']}.html", item=item, ch=ch, channel=name,
                        paragraphs=paragraphs, theme=name, active=name)

    site.render("events.html", "events/index.html", ev=event_data, theme="events", active="events")
    log.info("サイトを生成しました: %s", SITE_DIR)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    build(do_collect="--no-collect" not in sys.argv)
