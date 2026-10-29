# 第12次：月木09:00のAI調査・配信検証
Asia/Tokyo。東京・千葉の地上波・無料BS。実行当日を含む7暦日。追加の有料サービスなし。

## 起動の証跡
- ローカルシェルや作業フォルダーを必須にせず、GitHub接続で本書とdocs/phase10/OPERATIONS.md、最新の候補・出典・公開JSONを読む。
- 最初に時計で実際の開始日時を確認し、data/ai-research-runs.jsonのrunsへ開始記録を追記する。既存履歴を保持する。runIdは実時刻から一意にする。
- executionContextはheartbeatならscheduled_heartbeat、対話の依頼ならinteractive_preflight、手動Run nowならmanual_scheduled_test。9時の予定を実際の開始時刻として記録しない。
- scheduledFor、triggerReceivedAt（観測できた値だけ）、onTime、platformExecutionId（不明はnull）、検索・候補・GitHub・Actions・Pagesの各状態を別記。遅延原因を推測しない。
- GitHub ActionsはAIの代わりにWeb検索しない。Actions成功だけでAI起動成功と判定しない。

## 実検索と候補
全20ジャンルで2種類以上、ホラー映画・ディズニー・USJは3種類以上の実際のWeb検索。番組名・ジャンル・週間表・各回予告を組み合わせる。日付の新しい末尾2日も重点検索する。検索できない場合は失敗であり検索済みとしない。
アニメAPIは既存Actions担当で重複照会しない。候補の局・日時・内容根拠を個別確認し、公式と第三者確認を区別。既存ID/シリーズIDを保ち、同じ放送枠は追加しない。
紹介文・画像・出演者・番組表全体は保存しない。未確認日時はclaimedStart/End、終了不明はnull。未知のホストや禁止された取得方法を勝手に許可しない。過去枠を未来へ動かさない。

## 条件付き公開とログ
既存ledger.projectとautopublishへai-candidates.jsonのdiscoveriesを渡す。publicationApprovedを直接trueにしない。source-checks.jsonへ実検索・照合・失敗を保存。
既存有効2ポリシー・既存hostsの範囲に限り、利用条件を実際に確認した個別URLとindividualFactReviewsを追加できる。enabled/mode/hosts/permissionsは変更しない。規約ページ取得失敗を許諾確認済みとして扱わず、既存の個別最小事実参照の範囲を超える場合は保留。
mainの最新SHA/treeを読み、create_tree→create_commit→update_ref(expected_sha、force=false)で入力をまとめて反映。競合は再読込みして統合。manual-approved.json、公開JSON、Android本体、処理コードはこの定期調査では変更しない。
正常時もrunsへ最終結果を追記・更新する。新規候補・重複・保留理由・新規公開・更新・期限切れ・コミット・Actions run・Pages HTTP/ハッシュを記録。公開失敗時は既存の正常JSONを維持し、成功を偽らない。

## 内部の更新状況
data/operations-status.jsonは既存ActionsのPages検証成功後にscripts/operations_status.pyが生成する。AI検索日時・対象期間・実検索数、最新予定枠のheartbeat観測、アニメ取得、公開検証と全20ジャンルの件数/最終開始日時を分離する。
lastActions.observedAtは観測日時で、実行開始時刻ではない。正確なActions開始時刻は記載runIdのGitHub履歴で確認する。
Android v0.3.0の「最終更新」はJSON generatedAt（配信データ生成時刻）を保存した値。AIの検索時刻でも、端末のダウンロード時刻でもない。UIを増やさず、説明は内部レポートに残す。

## 次回検証
2026年11月2日(月)09:00 JST。実際の開始ログ・検索・候補の更新・GitHub書込・Actions・Pagesを順に確認する。未来の実行を成功扱いしない。
PC・アプリ・接続・権限の利用可能性が必要で、プロンプト変更は正確な時刻起動を保証しない。10/29はActionsが09:40:17、AI heartbeatが13:04:47に観測され、9時のAI起動は未確認。遅延原因は未特定。
通常成功はログのみ。開始欠落/遅延、取得・公開失敗、大量消失・重大矛盾・必要な管理者操作は報告する。
