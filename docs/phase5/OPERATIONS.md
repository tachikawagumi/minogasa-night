# 第5次 自動公開運用

対象は tachikawagumi/minogasa-night のみ。Android v0.2.0のJSON形式は変更しない。

## 連携経路
月曜・木曜09:00 JSTの既存ChatGPTタスクが公式情報を調査し、GitHub連携でdata/ai-candidates.jsonへ書き込む。そのpushをGitHub Actionsが受け、自動判定→アニメAPI取得→差分・形式・大量消失チェック→コミット→Pages→公開JSON照合を行う。毎回の人手承認は要求しない。

Actions単体も月曜・木曜09:00 JSTに実行する。二つの時計は同期機構ではない。AI候補の更新が明示的な接続点になる。ChatGPT側の定期実行には既存契約の利用枠、稼働中のアプリと接続環境が必要。GitHubの予定実行も定刻保証ではない。

## 自動採用の条件
config/source-policy.jsonで、metadata/cache/redistribute/automated_accessの全権限が確認済み・有効な情報源だけを自動採用する。AIの自己申告だけで許諾を有効化しない。
- syobocal：公開の自動取得・コピー許可を確認済み。実際にAPIへ照会したPID・局・日時・作品名に一致するものだけ。API由来の自動分類はアニメのみ。
- official_unreviewed：公式の日付確認ができていても、自動取得・再配信条件が未確認なので保留。現時点で全公式サイトを許諾済みと扱わない。
- 将来、公式情報の自動利用条件が確保できた場合は、情報源単位で一度ポリシーを登録する。以後その情報源の番組ごとの承認は不要。

明確な番組名だけで放送日を推定しない。watchlistは候補発見用。何だコレは当該回の根拠不足なら保留。ほん怖も利用条件を満たした取得元から日時を確認できた場合に自動採用する。

## 差分と保護
id・seriesIdを維持して時刻や局を更新する。ジャンル修正は指定された根拠付きの配列へ置換し、旧誤分類を無条件に合算しない。中止は明示的な公式確認または提供元Deleted PIDだけで判定する。

取得失敗、局の対応不一致、公開形式不正、将来枠の全件消失、35%超かつ10件以上の想定外消失、局別50%超の大量消失では公開を止める。アニメ提供元だけの大量消失も独立して調べる。正常に期限切れになった過去枠は異常消失に数えない。

失敗時は正常な公開JSON・APIキャッシュをGitHubへ更新せず、エラーログだけを残す。Pagesの公開後は生成時刻と全レコードを含むJSONの意味的SHA-256を照合する。公開または照合に失敗した場合は、data/last-published.jsonの前回検証済み版を再配信する。GitHub自体が停止中の場合はロールバックもできないため、成功を装わず失敗を報告する。

## ログ
- data/update-result.json：今回の状態、追加・時刻変更・ジャンル変更・削除・期限切れ件数。
- data/update-history.json：直近50件の履歴。
- data/ai-state.json：条件を通過したAI由来の状態。
- data/ai-held.json：条件不足・矛盾等の保留理由。
- data/publication.json：Pages実取得・SHA-256・時刻。
- data/last-published.json：最後に公開確認できた完全なJSON。

通常成功はログだけ。失敗はGitHub Actionsの失敗記録・短期アーティファクトに残す。GitHub側の通知受信設定にも依存する。AIタスク自体の書込み失敗はChatGPTで報告する。

## 費用
Python標準ライブラリー、GitHub公開リポジトリ、標準Ubuntuランナー、GitHub Pagesを使用。有料OpenAI API、Cloudflare、独自ドメイン、クラウドDBを導入しない。既存ChatGPTの利用枠を超えて無制限にAIを実行できるという意味ではない。

## 検証
python -m unittest discover -s tests -v
python scripts/autopublish.py
python scripts/verify_deployment.py --ack

公開：https://tachikawagumi.github.io/minogasa-night/v1/programs.json
