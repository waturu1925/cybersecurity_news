# CyberSecurity_collecting_Data

個人用の情報収集・ランキングサイト「SEC//INTEL」。コンテンツ表示はすべて日本語（装飾的な英字 UI は可）。

## 構成

- 静的サイト方式: `build.py` が収集→翻訳→`site/` に HTML を生成。GitHub Actions（`.github/workflows/update.yml`）が3時間ごとに実行し GitHub Pages へデプロイ
- DB（`data/news.db`）は Actions のキャッシュで実行間を引き継ぐ。記事 ID はキャッシュが消えると振り直しになる
- チャンネル: `news` / `tech` / `gadget`。情報源・採点ルール・レベル名・期間は `config.py` の `CHANNELS` に集約
- イベント: `curated_events.py`（手動管理の主要イベント）＋ `events.py`（Doorkeeper 自動取得、`CONNPASS_API_KEY` があれば connpass も）
- LINE 通知: `notify_line.py`（Messaging API の push。毎朝 8:00 JST = cron `0 23 * * *`）。シークレット未設定時は内容を表示するだけ
- 翻訳: Google 翻訳の非公式エンドポイント `clients5.google.com`（`translate.google.com/m` は CAPTCHA でブロックされる）
- 本文翻訳は静的サイトのため事前に行う（各ランキング上位 `BODY_PREFETCH` 件）。`body_ja` は NULL=未取得、空文字=取得失敗

## デザイン

- `static/style.css`: ハッカー風（黒地＋ネオン）。見出し・装飾は等幅（JetBrains Mono / M PLUS 1 Code）、記事タイトル・要約・本文は読みやすさ優先で BIZ UDPGothic（`--font-read`）
- テーマ色: news=グリーン / tech=シアン / gadget=ピンク / events=アンバー
- リンクは GitHub Pages のサブパス対策ですべて相対パス（テンプレートの `root` 変数）

## 実行

- ローカル確認: `start.bat`（収集→生成→ http://127.0.0.1:8000 ）、生成のみは `.venv\Scripts\python.exe build.py --no-collect`
- `start.bat` は ASCII のみで書くこと（日本語を入れると cmd の解釈が崩れる）
