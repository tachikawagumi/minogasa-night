# 第10次：AI Web検索から条件付き自動公開
VICTORY K / 月曜・木曜09:00 Asia/Tokyo / 追加の有料APIなし。

## 毎回の実行
1. 専用リポジトリtachikawagumi/minogasa-nightの最新版から本書、config/discovery.json、config/stations.json、config/source-policy.json、data/ai-candidates.json、公開JSON、台帳を読む。既存ID/シリーズIDを保つ。
2. 実行日の日本時間を含む7暦日が対象。全20ジャンルを実際に2検索以上（不足ジャンルは3検索以上）実行する。週間表、番組名、各回の予告、関連語、専門サイト、前回の保留を組み合わせ、検索語を切り替える。計画だけで調査済みにしない。アニメAPIはActionsに任せる。
3. 番組名・局・開始/確認できた終了・当該回の分類根拠を個別参照で確認。未確認日時はclaimedStart/End、終了不明はnull、既存公開と同じ枠は重複作成しない。放送日表記の深夜と暦日を区別する。過去枠を未来へ動かさない。
4. 公式確認はofficialVerification、信頼できる第三者表での確認はscheduleVerificationへ記録し、混同しない。個別の利用条件を確認し最小事実だけ独自記録。紹介文・出演者・画像・番組表の配列を保存しない。明示的な再提供禁止、403/robots拒否を回避しない。
5. eligibleかつclearの台帳候補をdata/ai-candidates.jsonのdiscoveriesへ保存する。公式はreviewed_independent_facts、第三者はreviewed_schedule_factsを使用。publicationApprovedを直接trueにせず、ledger.project→autopublishの検証に渡す。検証不合格は理由付き保留。
6. factUseReviewは実際に確認した最小事実のスナップショット、URL、確認時刻、方式、非転載・非大量取得・非会員サービス利用を記録する。既存の有効な2ポリシーの条件を満たす新しい個別参照については、同じ取得/利用条件を確認した上でallowedUrlsとindividualFactReviewsだけを追記してよい。既存hosts内に限る。enabled/mode/hosts/permissionsを変更せず、禁止・未確認の取得条件を勝手に有効化しない。未知のhostは候補として保留する。包括ライセンスを取得したとは記録しない。
7. 実行した検索ログ（genreId/route/query/tool/status/checkedAt/windowStart/End）、出典照合と失敗をdata/source-checks.jsonへ記録。executionContextは対話の手動実証ならinteractive_preflight、手動Run nowならmanual_scheduled_test、実際のheartbeat起動時だけscheduled_heartbeat。予定時刻が近いだけで無人成功と認定しない。
8. GitHub接続が利用できる場合、data/ai-candidates.json、data/source-checks.json、上記範囲のconfig/source-policy.json、data/ai-research-runs.jsonだけを1コミットで更新してよい。手動承認ファイル・公開JSON・アプリやコードは変更しない。書込できなければ未完了と報告し、架空の送信成功を残さない。
9. Actionsが形式・局・期間・分類・出典・差分・大量消失を検証し公開する。失敗時は前回正常JSONを保護する。Actions/Pagesの結果と公開JSONを実際に照合する。
10. 通常成功は実行時刻・検索数・追加/更新/保留件数・コミットと公開確認をログへ残し静かにする。取得/公開失敗、重大な矛盾、大量消失、注目番組の取りこぼし、必要な管理者操作のみ通知する。

## 接続ツールだけで反映する方法
通常のWeb検索はこのチャットで利用できるWeb検索ツールを使う。ローカルファイルの読書きやローカルコマンドを必須にしない。
GitHubのgithub_fetchは承認済みGETとして https://api.github.com/repos/tachikawagumi/minogasa-night/commits/main を読める。返却structuredContent.contentのJSONからshaとcommit.tree.shaを取得できることを第10次の対話テストで確認した。
最新headを取得してからgithub_create_tree（base_tree_shaは実際のtree SHA）→github_create_commit→github_update_ref(expected_sha、force=false)で一括反映する。競合したら最新版を読み直し、他の変更を保持して再統合する。古いJSONで上書きしない。
APIのGET失敗・接続権限不足・ツール不在なら成功扱いにしない。セキュリティ確認を別手段で回避しない。

## 無人実行の検証
次回予定2026-10-29 09:00 JST。現時点で未到来のため定刻実行は未検証。
実際の起動時は実行元・観測時刻・分かる実行ID（不明ならnull）・Web検索・候補・GitHub書込・Actions・Pagesを記録する。ログの自己申告だけでなくScheduledの実行履歴と照合する。
GitHub Actionsの成功とAIの無人Web検索成功を区別する。局や対象ジャンルで結果0件のときは未発見/情報不足と、全局確認済みの該当放送なしを区別する。
公式ドキュメント https://learn.chatgpt.com/docs/automations?surface=app は、ローカル実行ではPCとデスクトップアプリが起動し、プロジェクトが利用可能であること、通常の権限設定が無人実行にも関係することを説明している。接続が対話で動いたことだけで無人の権限を保証しない。

## NHK BSプレミアム4K
サイコの当該枠を確認し対象局へ追加。NHK自身の視聴案内は https://prtimes.jp/main/html/rd/p/000000065.000160617.html 。
既存のNHK BSと同じく受信契約の条件を別途確認し、4K対応受信設備が必要。追加の有料専門チャンネル契約とは区別。
アニメAPIのチャンネルIDは推測せずNoneとして除外し、従来APIの照会対象は変更していない。
