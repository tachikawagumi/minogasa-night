# 第8次：専門情報源と個別事実の収集
VICTORY K / 追加月額費用0円 / 公開JSONスキーマ1を維持。

## 収集・公開
1. config/discovery.json の全20ジャンルについて、番組名・当該回予告全文・局別番組表・専門サイト・再調査を使う。scripts/discovery.py --plan は100経路の計画を生成するが、検索したことにはならない。
2. 専門サイトの一致は候補として保存する。公式に照合できていない日時は claimedStart/claimedEnd へ記録。公開 start/end に転記しない。
3. config/stations.json の地上波・無料BSに照合する。paid_cs/paid_bs/streaming/subscription は除外。未知の無料局は局照合待ちとし、有料と断定しない。同じ作品の無料枠は別IDで検証できる。
4. 公式の個別ページから番組名・局・当日を含む7暦日の開始日時と分類根拠を確認する。終了未確認はnull。紹介文・出演者・画像を保存しない。
5. 取得方法・利用条件を個別評価する。reviewed_independent_facts はサイト/番組表の包括ライセンスではない。config/source-policy.json 内の個別URL判断と一致する factUseReview が必要。本文非転載・非大量取得・非会員サービス利用・照合した事実のスナップショット・確認時刻を記録する。新規出典の未確認な条件を自動承認しない。既知出典でも新しい回は日時を確認し直す。
6. data/ai-candidates.json に records/discoveries/research を登録。data/source-checks.json にURL・役割・方法・確認日時・利用条件・確認できた事実を記録する。調査ログは実際に実行した検索だけ。失敗や0件を不存在の証拠にしない。
7. 既存Actionsが台帳保存→アニメAPI→検証・差分→公開→ライブJSONの完全一致確認を実施。不正入力・大量消失・取得失敗時は既存正常JSONを保護。変更・中止は同じ安定IDで公式根拠を確認する。単なる候補一覧からの消失で中止を推測しない。

## 役割
discovery は専門サイト等による発見、broadcast_facts は公式日時、genre_classification は当該回/作品の分類。公式サイトも個別参照条件を確認する。アニメの許諾済みAPI・User-Agent・直列間隔は従来のまま。

## 定期運用
既存 task automation の月木09:00 Asia/Tokyoを更新する。重複作成しない。GitHub Actionsの月木00:00 UTCも維持。
Actions自体はAI Web検索をしない。同時刻のAI調査が後から候補をコミットした場合、そのpushで再度検証・公開が起動する。
対話中の検索/書込実績と無人実行の成功は別。無人検索は次の実行履歴で確認するまで未検証。

## アクセスと権利
403/robots拒否を回避しない。専門サイトは候補発見だけに使い、表や説明の複製をしない。
BS朝日は各番組ページ下部の権利注意、テレビ東京は https://www.tv-tokyo.co.jp/index/company/link.html を参照。
BS12発信の個別発表 https://www.atpress.ne.jp/news/2830607 は https://www.atpress.ne.jp/term_use の会員サービス定義等を個別検討した。発表本文や画像、DB配信サービスを利用せず放送事実を独自記録する判断であり、@Pressからの再配信ライセンス取得ではない。
判断根拠と対象URLはsource-policy.json、今回の照合結果はsource-checks.json。判断のない出典にこの例を機械適用しない。

## 検証と承認削減
複数ファイルをまとめて読取・編集→一括テスト→1つの実装コミット。追加の承認依頼をファイル毎に行わない。システムの権限確認は遵守する。
APKは変更しない。Android本番の通信/日付/ジャンル処理を既存のJVMテストで検証し、実機UIでの確認とは区別する。
