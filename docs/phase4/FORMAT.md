# 共通番組形式 v1

内部データは data/current-db.json の records。公開用は public/v1/programs.json の programs。紹介文・出演者・画像・認証情報を含めない。

| フィールド | 役割 |
|---|---|
| id | 放送枠の識別子。アニメは元のPIDを使い、時刻変更でも保持 |
| seriesId | シリーズ共通の識別子。アニメはTID。手動登録は管理者が同じシリーズIDを維持 |
| title | 番組名・作品名 |
| stationId | 許可リストの局ID。局名はstations表に保持 |
| start / end | タイムゾーン付きISO 8601。JST。endは不明ならnull |
| genreIds | 定義済み20ジャンルのID配列。複数可、根拠のない分類は不可 |
| sourceUrl | 内部のみ。公式の確認元／許可されたAPIの出典URL |
| checkedAt | 実際に内容を確認した時刻。失敗時に更新しない |
| updatedAt | そのレコードを最後に取り込んだ時刻 |
| status | official_confirmed：公式情報で局と日時を照合。provider_confirmed：許可されたデータ提供元で確認 |
| publicationApproved | 内部のみ。管理者の公開採用状態。放送局と契約済みという意味ではない |
| genreBasis | 内部のみ。独自の短い分類根拠。予告本文は転載しない |

公開エンベロープはschemaVersion=1、sourceMode=real、timeZone=Asia/Tokyo、generatedAt、windowStart、windowEnd、updateStatus、notice、genres、stations、coverage、programs。coverageのcompleteはfalseで、アニメ取得状況と他ジャンルの選択的確認を区別する。生成時刻はデータ源の最終確認時刻とは異なる。

重複は局・正規化した開始時刻・NFKC正規化タイトルで判定。日時と局が同じで、一方のタイトルがもう一方の副題付き表記を包含する場合も統合し、提供元PIDを優先する。別局・別日時・無関係なタイトルは統合しない。作品名の表記差が大きく一致しない場合は管理者確認が必要。

生成時点の過去枠、7暦日の期間外、確認不十分・公開承認なしの行は公開しない。取得失敗時は正常なAPIキャッシュを保存したままpartial状態で供給し、Androidも保存済みデータを保持する。
