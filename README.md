# chanriva-content

ちゃんりば Standard（ガチャ／リバーシ図鑑）向けの公開コンテンツ配信リポジトリです。

- `index.json`: アプリが最初に取得する pack 一覧
- `packs/<pack-id>/`: 編集用の `manifest.json` / `cards.json` / `assets/`
- `dist/`: アプリ配信用の ZIP pack
- `schema/`: JSON Schema

カードの `imagePath` は任意です。画像がないカードはアプリ内のカテゴリ別デフォルトアイコンを使います。

公開後のカード `id` は変更・再利用しません。pack の `version` は更新ごとに単調増加させます。
