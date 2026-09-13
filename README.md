# chanriva-content

ちゃんりば Standard（ちゃんりばガチャ／リバーシ図鑑）向けの公開コンテンツ配信リポジトリです。

AI対戦企画の配信は、独立した[Opponent Packs](opponents/README.md)を参照してください。
カードとは別のindex/schema/ZIPとvalidatorを利用します。

## 配信構成

- `index.json`: アプリが最初に取得する pack 一覧
- `packs/<pack-id>/manifest.json`: 編集用 pack メタデータ
- `packs/<pack-id>/cards.json`: 編集用カードデータ
- `packs/<pack-id>/assets/`: 任意のカード画像・音声
- `dist/`: アプリが取得する ZIP pack
- `schema/`: JSON Schema
- `scripts/validate.py`: index / pack / ZIP / SHA-256 の整合性検証

アプリには最低限の bootstrap データを同梱し、ネットワーク取得に失敗した場合も図鑑・ガチャが使えるようにします。GitHub 側に同じ pack のより大きい `version` がある場合だけ更新します。

## カード画像

`imagePath` は任意です。

```json
{
  "id": "trivia.rules.001",
  "type": "trivia",
  "rarity": "common",
  "title": "先手は黒",
  "summary": "オセロでは黒が先に打つ。"
}
```

個別画像を付ける場合だけ、pack 内の `assets/` を参照します。

```json
"imagePath": "assets/trivia.rules.001.webp"
```

画像指定がない場合、アプリはカテゴリ別のデフォルトアイコンを表示します。ガチャのカプセル・ヒビ・割れる演出はアプリ本体の固定素材で、コンテンツ配信からは変更しません。

## カテゴリ仕様

図鑑カードのカテゴリは、現在以下の5種類に固定しています。

- `trivia`: 雑学・豆知識
- `book`: 書籍
- `history`: 歴史
- `person`: 人物
- `collab`: コラボレーション

`chanriva-content` 側だけで新しいカテゴリを追加することはできません。

アプリ側ではカテゴリごとに、表示名・表示順・デフォルトアイコン・図鑑フィルタ・UI上の扱いを定義しています。そのため、未知の `type` を配信データへ追加しないでください。

新しいカテゴリを追加する場合は、先にちゃんりばアプリを更新して新カテゴリへ対応し、その後に本リポジトリの schema と配信データを更新します。

原則として、既存カテゴリの意味を変更したり、公開済みカテゴリ名を別用途へ再利用したりしません。

## 更新ルール

- `schemaVersion` は現行 `1`
- card `id` は公開後に変更・再利用しない
- pack `version` は更新ごとに単調増加
- `type`: `trivia` / `book` / `history` / `person` / `collab` の5種類固定。新カテゴリはアプリ更新後に追加する
- `rarity`: `common` / `rare` / `special`
- `sourceUrl` / `externalUrl` は HTTPS のみ
- `imagePath` は `assets/` 配下の `.webp` / `.png` / `.jpg` / `.jpeg`
- `index.json` の `sizeBytes` と `sha256` は `dist/*.zip` と一致させる

PR と push では GitHub Actions が `python scripts/validate.py` を実行します。

## 初期配信データ

現在はアプリ同梱データと同じ trivia / books カタログを version 2 として配置しています。これにより既存 card id と取得済み状態を維持したまま、GitHub 配信経路を検証できます。
