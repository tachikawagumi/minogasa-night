# チャッピー主担当：番組調査 → GitHub登録 → 公開運用

開始：2026-11-05。既存のAndroid v0.3.0、20ジャンル、番組/シリーズID、お気に入り、しょぼいカレンダーのアニメ連携は変更しない。

## 役割

- ChatGPT定期タスク（月・木 9:00 JST）：地上波（東京・千葉）と無料BSの7日間、全20ジャンルを放送回単位で探索し、放送局公式の個別情報で事実確認。**確認できた最小放送事実を `data/manual-approved.json` に追記**する。Workは原則として保守・コード改修時だけ使う。
- 既存 GitHub Actions `scripts/autopublish.py`：同ファイルとAI承認済み台帳、アニメAPIを統合し、既存の時間窓・重複・ID・公開整合性の検証を通して `public/v1/programs.json` へ反映する。
- ChatGPTは `public/v1/programs.json` を**直接編集しない**。AIが情報源ポリシーを包括許可に書き換えたり、未確認候補を `official_confirmed` と偽装しない。

## 公式確認済み1枠の追記項目

`id`, `seriesId`, `title`, `stationId`, `start`, `end`（未確認は `null`）, `genreIds`, `sourceUrl`, `checkedAt`, `updatedAt`, `status: "official_confirmed"`, `publicationApproved: true`, `origin: "chatgpt_individual_official_facts"`, `genreBasis`。

- `sourceUrl` は、その回の放送局等の公式ページ。URL・日時・対象地域・回の内容を実際に個別照合する。ジャンル名から日時を推測しない。
- 放送開始は `Asia/Tokyo` の時差付きISO 8601。終了が不明なら `null`。
- `genreIds` は当該回の内容による独自分類。複数指定可。車は自動車・バイク・トラック・大型車両を含むが、ただ乗っているだけなら車扱いしない。
- 過去の `id`/`seriesId` を検索して再利用する。重複・矛盾は保留し、既存行を書き換えない。対象外局、契約の必要なBS/CSは入れない。
- 公式の個別放送予定が確認できないものは調査報告で「保留」にして、`manual-approved` へ**登録しない**。
- 本文・画像・出演者一覧・番組表配列を転載せず、必要な日時・局・作品名と独自の短いジャンル根拠に限る。サイトの一括収集・利用条件の回避を行わない。

## GitHubへの書込み順

1. `main` の `data/manual-approved.json` と最新 `public/v1/programs.json` を読み、既存ID・対象期間・重複を確認する。
2. 新規確認済み放送枠のみ追記して、GitHubの最新 blob SHA を付けて更新する。失敗時は最新のファイルを再取得し、競合を確認してから再試行。古いファイル全体で上書きしない。
3. 既存Actionsが公開したら、公開JSONの `generatedAt`、`windowStart`/`windowEnd` と追加枠を再照合する。**調査完了・GitHub登録完了・公開完了を区別して報告**する。
4. GitHubに書き込めない、公式未確認、Actions失敗の場合は、件数を成功扱いせず理由と保留候補を報告する。

## 2026-11-05 検証

当日の最新公開JSONは116枠すべてアニメで、AI側の候補の新規採用は0件だった。原因は調査タスクの GitHub 書込禁止設定と候補ファイルの更新停滞であり、非アニメの事実が消失したというより、過去枠の期限切れ後の補充がない状態だった。

今回、放送局公式ページで個別確認した12枠（うち11/12の1枠は11/5時点の7日窓外）を `data/manual-approved.json` に追記した。今後はChatGPT主担当が同経路で追加する。**本方式の定刻無人 GitHub 書込は次回の実行で検証する**。
