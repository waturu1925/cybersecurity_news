from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "news.db"

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

MAX_ITEMS_PER_FEED = 40
RANKING_LIMIT = 50
BODY_MAX_CHARS = 9000
TRANSLATE_WORKERS = 6
# 静的サイトでは本文翻訳をその場で行えないため、各ランキング上位のこの件数だけ事前に翻訳しておく
BODY_PREFETCH = 15
LINE_TOP_N = 3
UPDATE_INTERVAL_TEXT = "3時間ごと"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

POPULAR_PRODUCTS = (
    r"Microsoft|Windows|Exchange|Office|Azure|Google|Chrome|Android|Apple|iOS|macOS|"
    r"Cisco|Fortinet|FortiGate|Ivanti|Palo Alto|VMware|Citrix|Linux|Oracle|SAP|"
    r"WordPress|Atlassian|Confluence|Jenkins|SonicWall|Juniper|F5"
)
POPULAR_PRODUCTS_POINTS = 8

# 各ページ（チャンネル）の設定。feeds の bonus は情報源そのものの信頼度による加点
CHANNELS = {
    "news": {
        "title": "重要ニュース",
        "code": "THREAT_INTEL",
        "description": "世界のサイバー攻撃・脆弱性・情報漏えいを重要度順にランキング",
        "score_label": "重要度",
        "keep_days": 30,
        "periods": {1: "24時間", 3: "3日間", 7: "1週間", 30: "30日間"},
        "default_period": 7,
        "include_kev": True,
        "product_bonus": True,
        "cvss_bonus": True,
        "bonus_label": "公的機関（{source}）からの情報",
        "feeds": [
            {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews", "bonus": 0},
            {"name": "BleepingComputer", "url": "https://www.bleepingcomputer.com/feed/", "bonus": 0},
            {"name": "SecurityWeek", "url": "https://www.securityweek.com/feed/", "bonus": 0},
            {"name": "Dark Reading", "url": "https://www.darkreading.com/rss.xml", "bonus": 0},
            {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/", "bonus": 0},
            {"name": "The Record", "url": "https://therecord.media/feed", "bonus": 0},
            {"name": "JPCERT/CC", "url": "https://www.jpcert.or.jp/rss/jpcert.rdf", "bonus": 10},
            {"name": "IPA", "url": "https://www.ipa.go.jp/security/alert-rss.rdf", "bonus": 10},
            {"name": "Security NEXT", "url": "https://www.security-next.com/feed", "bonus": 0},
        ],
        # (正規表現, 加点, 日本語の理由)。英語・日本語どちらの記事にも当たるようにしている
        "keyword_rules": [
            (r"zero[- ]?day|0-day|ゼロデイ", 25, "ゼロデイ脆弱性（修正前に悪用される脆弱性）"),
            (r"actively exploited|exploited in the wild|in-the-wild|under active exploitation|exploitation attempts|悪用", 20, "実際の攻撃での悪用を確認"),
            (r"ransomware|ランサムウェア", 15, "ランサムウェア関連"),
            (r"emergency directive|緊急指令|注意喚起", 15, "公的機関による注意喚起・緊急指令"),
            (r"remote code execution|\bRCE\b|リモートコード実行|任意のコード", 12, "リモートコード実行（遠隔から乗っ取り可能）"),
            (r"data breach|breach|leaked|data leak|情報漏えい|情報漏洩|流出|不正アクセス", 12, "情報漏えい・侵害事案"),
            (r"supply[- ]chain|サプライチェーン", 10, "サプライチェーン攻撃"),
            (r"nation[- ]state|\bAPT\s?\d*\b|state-sponsored|espionage|(?:China|Russia|Iran|North Korea)[- ](?:linked|nexus|backed)|国家支援|諜報|中国系|ロシア系|北朝鮮", 10, "国家支援型の攻撃者"),
            (r"critical|max(?:imum)? severity|緊急|深刻|重大", 10, "深刻度が高い"),
            (r"authentication bypass|auth bypass|privilege escalation|認証回避|認証バイパス|権限昇格", 8, "認証回避・権限昇格"),
            (r"botnet|DDoS|ボットネット", 6, "ボットネット・DDoS"),
            (r"phishing|フィッシング", 5, "フィッシング"),
            (r"patch|security update|修正|アップデート", 3, "修正パッチ・更新情報"),
        ],
        "keyword_cap": 60,
        "categories": [
            ("ランサムウェア", r"ransomware|ランサムウェア"),
            ("脆弱性", r"vulnerab|CVE-\d|zero[- ]?day|flaw|patch|脆弱性|ゼロデイ"),
            ("情報漏えい", r"breach|leak|exposed|情報漏|流出|不正アクセス"),
            ("APT・国家支援", r"nation[- ]state|\bAPT\s?\d*\b|state-sponsored|espionage|国家|諜報"),
            ("マルウェア", r"malware|trojan|botnet|stealer|backdoor|spyware|RAT\b|マルウェア|ボットネット"),
            ("フィッシング・詐欺", r"phishing|scam|fraud|フィッシング|詐欺"),
            ("政策・摘発", r"\blaw\b|regulation|sanction|arrest|indict|sentenced|法律|法案|規制|逮捕|制裁"),
        ],
        "levels": [(65, "緊急", "critical"), (45, "高", "high"), (25, "中", "medium"), (0, "低", "low")],
    },
    "tech": {
        "title": "技術ニュース",
        "code": "TECH_RADAR",
        "description": "攻撃手法の研究・防御技術・ツール・解析レポートを注目度順にランキング",
        "score_label": "注目度",
        "keep_days": 90,
        "periods": {7: "1週間", 30: "30日間", 90: "90日間"},
        "default_period": 30,
        "include_kev": False,
        "product_bonus": False,
        "cvss_bonus": False,
        "bonus_label": "定評ある技術研究チーム（{source}）の発信",
        "feeds": [
            {"name": "Google Project Zero", "url": "https://googleprojectzero.blogspot.com/feeds/posts/default", "bonus": 15},
            {"name": "PortSwigger Research", "url": "https://portswigger.net/research/rss", "bonus": 15},
            {"name": "Trail of Bits", "url": "https://blog.trailofbits.com/feed/", "bonus": 15},
            {"name": "JPCERT/CC Eyes", "url": "https://blogs.jpcert.or.jp/ja/atom.xml", "bonus": 10},
            {"name": "Google Security Blog", "url": "https://security.googleblog.com/feeds/posts/default", "bonus": 5},
            {"name": "Unit 42", "url": "https://unit42.paloaltonetworks.com/feed/", "bonus": 5},
            {"name": "Cisco Talos", "url": "https://blog.talosintelligence.com/rss/", "bonus": 5},
            {"name": "Securelist", "url": "https://securelist.com/feed/", "bonus": 5},
            {"name": "Check Point Research", "url": "https://research.checkpoint.com/feed/", "bonus": 5},
            {"name": "ESET WeLiveSecurity", "url": "https://www.welivesecurity.com/en/rss/feed/", "bonus": 0},
            {"name": "Microsoft Security Blog", "url": "https://www.microsoft.com/en-us/security/blog/feed/", "bonus": 0},
            {"name": "Cloudflare Blog", "url": "https://blog.cloudflare.com/tag/security/rss/", "bonus": 0},
            {"name": "SANS ISC", "url": "https://isc.sans.edu/rssfeed_full.xml", "bonus": 0},
            {"name": "Help Net Security", "url": "https://www.helpnetsecurity.com/feed/", "bonus": 0},
            {"name": "Schneier on Security", "url": "https://www.schneier.com/feed/atom/", "bonus": 0},
            {"name": "Kali Linux", "url": "https://www.kali.org/rss.xml", "bonus": 0},
            {"name": "LAC WATCH", "url": "https://www.lac.co.jp/lacwatch/feed.xml", "bonus": 0},
        ],
        "keyword_rules": [
            (r"new (?:technique|attack|method|class|variant)|novel|新たな手法|新手法|新しい攻撃手法", 15, "新しい攻撃手法・技術"),
            (r"proof[- ]of[- ]concept|\bPoC\b|exploit(?:ation)? (?:technique|chain|primitive)|exploit development|エクスプロイト", 12, "PoC・エクスプロイト技術の解説"),
            (r"deep dive|technical analysis|in-depth|walkthrough|under the hood|how (?:it|we) work|詳細解説|技術解説|仕組み|徹底解説", 10, "技術的な深掘り解説"),
            (r"bypass|evasion|evade|sandbox escape|回避|バイパス", 10, "防御回避・バイパス技術"),
            (r"fuzz|reverse engineer|decompil|binary analysis|symbolic execution|ファジング|リバースエンジニアリング|逆アセンブル", 10, "解析・ファジング技術"),
            (r"\bAI\b|\bLLM|machine learning|agentic|prompt injection|生成AI|人工知能|機械学習", 10, "AI とセキュリティ"),
            (r"open[- ]source|GitHub|\btool(?:kit|s)?\b|framework|released?\b|オープンソース|ツール", 8, "ツール・OSS の公開"),
            (r"research|researchers|whitepaper|\bpaper\b|study|研究|論文|調査", 8, "研究・調査結果"),
            (r"post[- ]quantum|cryptograph|encryption|\bTLS\b|passkey|FIDO|WebAuthn|暗号|パスキー", 8, "暗号・認証技術"),
            (r"detection|threat hunting|YARA|\bSigma\b|SIEM|\bEDR\b|\bXDR\b|\bSOC\b|検知|ハンティング", 8, "検知・防御技術"),
            (r"kernel|memory safety|\bRust\b|hypervisor|firmware|UEFI|race condition|カーネル|メモリ安全|ファームウェア", 8, "低レイヤー・システムセキュリティ"),
            (r"malware|ransomware|backdoor|loader|rootkit|implant|stealer|\bC2\b|command-and-control|BYOVD|マルウェア|ランサムウェア|バックドア", 8, "マルウェアの技術解析"),
            (r"threat actor|campaign|\bAPT\s?\d*\b|\bUAT-\d+|state-sponsored|攻撃グループ|攻撃者グループ|キャンペーン", 8, "攻撃グループ・キャンペーンの分析"),
            (r"cloud|Kubernetes|container|\bAWS\b|Azure|\bGCP\b|クラウド|コンテナ", 6, "クラウド・コンテナ"),
            (r"zero[- ]?day|0-day|CVE-\d|vulnerabilit|ゼロデイ|脆弱性", 6, "脆弱性の研究・分析"),
        ],
        "keyword_cap": 60,
        "categories": [
            ("AIセキュリティ", r"\bAI\b|\bLLM|machine learning|agentic|prompt injection|生成AI|機械学習"),
            ("マルウェア解析", r"malware|backdoor|loader|trojan|\bC2\b|ransomware|マルウェア|バックドア|ランサムウェア"),
            ("攻撃手法・研究", r"exploit|technique|bypass|PoC|fuzz|race condition|vulnerab|攻撃手法|エクスプロイト|脆弱性"),
            ("暗号・認証", r"cryptograph|encryption|post[- ]quantum|passkey|FIDO|authentication|暗号|認証|パスキー"),
            ("検知・防御", r"detection|hunting|YARA|\bSigma\b|SIEM|\bEDR\b|\bSOC\b|defen[cs]e|検知|防御"),
            ("クラウド・インフラ", r"cloud|Kubernetes|container|\bAWS\b|Azure|network|DNS|クラウド|ネットワーク"),
            ("ツール・OSS", r"open[- ]source|GitHub|\btools?\b|toolkit|framework|release|オープンソース|ツール"),
        ],
        "levels": [(40, "必読", "critical"), (26, "注目", "high"), (14, "標準", "medium"), (0, "参考", "low")],
    },
    "gadget": {
        "title": "ガジェットニュース",
        "code": "GADGET_SCAN",
        "description": "スマホ・PC・オーディオ・ウェアラブルなど最新ガジェット情報を注目度順にランキング",
        "score_label": "注目度",
        "keep_days": 14,
        "periods": {1: "24時間", 3: "3日間", 7: "1週間", 14: "2週間"},
        "default_period": 3,
        "include_kev": False,
        "product_bonus": False,
        "cvss_bonus": False,
        "bonus_label": "{source} の独自取材",
        "feeds": [
            {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "bonus": 0},
            {"name": "Engadget", "url": "https://www.engadget.com/rss.xml", "bonus": 0},
            {"name": "Gizmodo", "url": "https://gizmodo.com/feed", "bonus": 0},
            {"name": "9to5Mac", "url": "https://9to5mac.com/feed/", "bonus": 0, "max": 25},
            {"name": "9to5Google", "url": "https://9to5google.com/feed/", "bonus": 0, "max": 25},
            {"name": "Android Authority", "url": "https://www.androidauthority.com/feed/", "bonus": 0, "max": 25},
            {"name": "Ars Technica", "url": "https://arstechnica.com/gadgets/feed/", "bonus": 0},
            {"name": "ギズモード・ジャパン", "url": "https://www.gizmodo.jp/index.xml", "bonus": 0},
            {"name": "ITmedia Mobile", "url": "https://rss.itmedia.co.jp/rss/2.0/mobile.xml", "bonus": 0},
            {"name": "ITmedia PC USER", "url": "https://rss.itmedia.co.jp/rss/2.0/pcuser.xml", "bonus": 0},
            {"name": "ケータイ Watch", "url": "https://k-tai.watch.impress.co.jp/data/rss/1.0/ktw/feed.rdf", "bonus": 0, "max": 30},
            {"name": "PC Watch", "url": "https://pc.watch.impress.co.jp/data/rss/1.0/pcw/feed.rdf", "bonus": 0},
            {"name": "AV Watch", "url": "https://av.watch.impress.co.jp/data/rss/1.0/avw/feed.rdf", "bonus": 0},
            {"name": "PHILE WEB", "url": "https://gadget.phileweb.com/rss/", "bonus": 0},
        ],
        "keyword_rules": [
            (r"announce|launch|unveil|introduc|debut|発表|発売|登場|予約開始|投入", 12, "新製品の発表・発売"),
            (r"keynote|WWDC|\bCES\b|\bIFA\b|\bMWC\b|Unpacked|Made by Google|基調講演|発表会", 10, "大型発表イベント"),
            (r"\bApple\b|iPhone|iPad|\bMac\b|MacBook|AirPods|Apple Watch|Vision Pro|Pixel|Samsung|Galaxy|Sony|Xperia|PlayStation|Nintendo|Switch|Surface|Xbox|Meta Quest|Nothing|Anker|\bDJI\b|GoPro|アップル|ソニー|任天堂", 10, "注目ブランドの製品"),
            (r"review|hands[- ]on|tested|benchmark|レビュー|実機|使ってみた|試した|ベンチマーク", 8, "レビュー・実機レポート"),
            (r"foldable|折りたたみ|OLED|有機EL|Snapdragon|Tensor|\bM\d\b|chip|processor|\bNPU\b|チップ|プロセッサ", 6, "注目の新技術（チップ・ディスプレイ等）"),
            (r"\bAI\b|Gemini|Siri|Copilot|生成AI", 6, "AI 機能"),
            (r"日本|国内|Japan|価格|円|price|pricing", 6, "価格・国内展開の情報"),
            (r"security|vulnerab|privacy|セキュリティ|脆弱性|プライバシー", 6, "セキュリティ・プライバシー"),
            (r"leak|rumou?r|reportedly|リーク|噂|うわさ", 5, "リーク・噂"),
            (r"iOS \d+|Android \d+|macOS|One UI|update|アップデート", 4, "OS・ソフトの更新"),
            (r"deal|sale|discount|セール|値下げ|割引|最安", 3, "セール・お買い得情報"),
        ],
        "keyword_cap": 55,
        "categories": [
            ("スマートフォン", r"iPhone|Pixel|Galaxy [SZA]|Xperia|smartphone|phone|スマホ|スマートフォン|携帯"),
            ("PC・タブレット", r"iPad|\bMac\b|MacBook|laptop|\bPC\b|tablet|Surface|Chromebook|GPU|CPU|ノートPC|タブレット|パソコン"),
            ("オーディオ・映像", r"AirPods|headphone|earbud|speaker|\bTV\b|audio|イヤホン|ヘッドホン|スピーカー|テレビ|オーディオ"),
            ("ウェアラブル", r"Watch|wearable|ring|glasses|Vision Pro|Quest|スマートウォッチ|ウェアラブル|スマートグラス"),
            ("ゲーム", r"PlayStation|Xbox|Nintendo|Switch|Steam|game|gaming|ゲーム"),
            ("カメラ・ドローン", r"camera|\bDJI\b|GoPro|drone|カメラ|ドローン"),
            ("スマートホーム", r"smart home|Alexa|Google Home|Nest|HomeKit|robot vacuum|スマートホーム|ロボット掃除機"),
            ("AI・ソフトウェア", r"\bAI\b|Gemini|Siri|Copilot|iOS|Android|macOS|Windows|app|アプリ|生成AI"),
            ("周辺機器・充電", r"charger|power bank|portable power|cable|keyboard|mouse|monitor|SSD|充電|ポータブル電源|モバイルバッテリー|ケーブル|キーボード|マウス|モニター"),
            ("セール情報", r"deal|sale|discount|セール|割引|値下げ"),
        ],
        "levels": [(36, "必見", "critical"), (26, "注目", "high"), (14, "標準", "medium"), (0, "参考", "low")],
    },
}

# イベントページ: 自宅（愛知）から近いとみなす地域
NEARBY_AREA_PATTERN = r"愛知|名古屋|豊田|豊橋|岡崎|一宮|春日井|刈谷|安城|岐阜|三重|四日市|津市|静岡|浜松"
EVENT_TITLE_PATTERN = (
    r"セキュリティ|CTF|脆弱性|OWASP|SECCON|[Ss]ecurity|ハッキング|サイバー|ペネトレ|フォレンジック|"
    r"マルウェア|ゼロトラスト|\bSOC\b|インシデント|ランサムウェア|CSIRT|不正アクセス"
)
EVENT_SEARCH_WORDS = ["セキュリティ", "CTF", "脆弱性", "OWASP", "SECCON", "サイバー"]
