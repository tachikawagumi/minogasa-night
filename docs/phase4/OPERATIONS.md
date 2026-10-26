# みのがさナイト 週2回更新の運用

VICTORY K／GitHub Pages版／追加の有料API・Cloudflare・データベース契約は不要。

## 構成

月曜・木曜のAI調査 → 管理者が事実と分類を確認 → data/manual-approved.jsonへ採用。

GitHub Actionsがしょぼいカレンダーを取得 → 最小事実DBで統合 → public/v1/programs.json → GitHub Pages → AndroidのRoomキャッシュ。

公開先は専用リポジトリ tachikawagumi/minogasa-night を想定する。アプリ内の同URLは配信先の設定値であり、デプロイ完了の証明ではない。太刀川組・PALカリのリポジトリや既存サイトは使用しない。

## 公開確認（2026-10-26）

GitHub Pagesは管理者が初回有効化済み。Actions #2で検証・アニメ取得・JSON更新・配信が成功し、公開JSONのHTTP 200と146枠を確認した。

公開JSON： https://tachikawagumi.github.io/minogasa-night/v1/programs.json

本リポジトリは番組データの配信用。Android StudioプロジェクトとAPKは別途納品する。以後の手動承認データは、接続済みGitHub連携またはGitHub上でdata/manual-approved.jsonだけを更新すれば配信処理が動く。Androidプロジェクト全体を配信リポジトリへ上書きpushする必要はない。

## 初回設定・再構築の参考手順

1. GitHubで公開の空リポジトリ `minogasa-night` を用意する。READMEの自動作成は不要。
2. 本プロジェクトのコミットを専用リポジトリへ反映する。Gitの認証が済んだ環境なら `scripts/publish.ps1` を実行する。接続済みGitHubツールでも専用リポジトリ作成後はファイルの追加・更新を行える。
3. Settings → Pages → Build and deployment → Sourceを **GitHub Actions** にする。
4. Actions → Validate and refresh program feed → Run workflow。更新→検証→同じ実行内でPages配信まで進む。GITHUB_TOKENによるコミットが別のpushワークフローを起動しない問題を避けている。
5. Actionsで実際に返されたPages URLの `/v1/programs.json` を開く。200応答・sourceMode=real・generatedAt・更新状態を確認する。想定URLは `https://tachikawagumi.github.io/minogasa-night/v1/programs.json`。存在を確認するまで公開済みと報告しない。
6. 別のURLになった場合は `-PminogasaFeedUrl=https://.../v1/programs.json` を付けてAPKを再ビルドする。認証トークンは付けない。

## 自動更新：月曜・木曜

GitHub Actionsの予定は月曜・木曜 **06:17 JST**。cronはUTCの前日（日・水）21:17。GitHubの都合で遅延・スキップする可能性があり、定刻保証はない。公開リポジトリの予定実行は、長期間活動がないと停止する場合があるため、実行履歴も確認する。

更新日00:00以上・7日後00:00未満の枠を取得し、公開時点で開始済みの枠は除外する。アニメ以外の手動確認情報も同じ期間に絞る。端末は表示時にも日本時間と開始時刻で除外する。

APIは独自User-Agent `MinogasaNight/1.0 (VICTORY K)`。ChLookupで局を照合し、ProgLookupで枠を取得、TitleLookupで最大100IDずつタイトル・分類を結合する。リクエストは直列、間隔1.1秒以上。Cat=1のアニメのみを自動分類し、CS・有料局・ラジオは許可リストから除外する。

実際のAPIアクセスURLは `data/anime-cache.json` の requests に記録される。

- `https://cal.syoboi.jp/db.php?Command=ChLookup&Fields=ChID%2CChName`
- `https://cal.syoboi.jp/db.php?Command=ProgLookup&Range=YYYYMMDD_000000-YYYYMMDD_000000&ChID=...&Fields=PID%2CTID%2CChID%2CStTime%2CEdTime%2CLastUpdate%2CDeleted%2CWarn%2CRevision`
- `https://cal.syoboi.jp/db.php?Command=TitleLookup&TID=...&Fields=TID%2CTitle%2CCat%2CLastUpdate`

参考：[運営の利用案内](https://docs.cal.syoboi.jp/about/)、[API仕様](https://docs.cal.syoboi.jp/spec/db.php/)、[レート制限](https://docs.cal.syoboi.jp/spec/rate_limit/)。RSS/更新RSSは今回の処理では呼ばない。

取得失敗・XML異常・API上限・局名不一致・タイトル結合不足では最後に成功したアニメキャッシュを維持する。削除・警告枠は成功した全件更新から外す。失敗した更新を成功時刻で上書きしない。公開JSONのupdateStatus=partialで残っているキャッシュを示す。

## AI調査：管理者の確認方式

ChatGPTの定期実行は、OpenAI APIの課金契約とは別。今回のPython処理・ActionsはOpenAI APIを呼ばない。AI調査には既存ChatGPT/Workの利用枠を使うため、枠がなくなれば自動調査が続くとは保証できない。有料APIへの自動切替はしない。

定期実行にGitHubプラグインが使える場合でも、ブラウザー認証とは別であり、保存済みタスクの実行環境・対象リポジトリ・許可による。今回の完全自動書込みは未検証。初期運用は以下で行う。

1. AIが当日を含む7日間について公式情報を調べ、20ジャンルすべての調査結果と `data/manual-draft.json` を作る。局・日時・ジャンルの根拠が揃わない行は採用しない。
2. 管理者が番組名、局、日付と深夜表記、分類、出典と確認日時を確認する。事実を独自整理し、紹介文や画像をコピーしない。自動取得や公開利用が許可されない情報源は採用しない。
3. 承認した行に `python scripts/approve.py --approve` を実行する。AIが自分で承認コマンドを実行する運用にはしない。
4. 差分を確認して `data/manual-approved.json` を専用GitHubへ反映する。Actionsがアニメと統合し、検証後にPagesへ配信する。
5. 実行履歴・update-result.json・公開JSONを確認。失敗なら前回の情報と古さを確認する。

下書きは次の形式。架空の見本番組を実データへ足さず、初期の空下書きはそのままにしている。

`records` の各行：id、seriesId、title、stationId、start（JSTオフセット付き）、end（不明ならnull）、genreIds、sourceUrl（https）、checkedAt、updatedAt、status=`official_confirmed`、publicationApproved=false、genreBasis。

seriesIdは作品・シリーズごとに同じ値を続ける。番組IDは同じ枠で予定変更が起きても維持し、別日の放送には別IDを使う。管理者が中止を確認した手動行は承認データから削除して反映する。アニメの自動行はPID/TIDを利用する。

## ローカルでの確認

Python 3.12（標準ライブラリーのみ）で実行する。

```
python -m unittest discover -s tests -v
python scripts/feed.py
python scripts/feed.py --validate
```

通信しない確認は `python scripts/feed.py --offline`。これは取得成功と記録しない。初回調査資料の31件とAPI29枠は検証に利用し、その日付を現在へ動かして捏造しない。

## 無料枠と秘密情報

- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)はGitHub Freeの公開リポジトリで利用できる。
- [Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions)は公開リポジトリの標準Ubuntuランナーを利用する。大型・Windows・有料セルフホストランナーを使わない。通常は週2回、月約9回の小さい更新。配信用アーティファクトは保存1日。
- GitHub Pagesにも利用・帯域・ビルド制限がある。無料枠の仕様に適合する構成であり、未知の利用量や将来の規約変更に対する永続無料保証ではない。
- クラウドDB・独自ドメイン・Cloudflare・有料番組API・OpenAI APIは使わない。追加課金設定や支払い方法の変更はしない。
- Actionsは短命GITHUB_TOKENを使い、更新ジョブだけcontents:write、配信ジョブだけpages:writeとid-token:write。アプリ・公開JSON・コードにトークンを置かない。
- publicだけがPagesへ出る。dataの出典や分類根拠も公開リポジトリ上では閲覧可能だが、個人情報・秘密情報は含めない。

## アプリで確認する項目

APKは初回だけ同梱した実番組キャッシュを表示できる。新しい日付へ生成し直すサンプルではない。配信失敗でもRoomの取得済みデータを消さず、エラーと最終更新を表示する。期限を過ぎた枠は表示しない。

「今日」「明日」「1週間」、ジャンルON/OFF、番組とシリーズのお気に入り、通知ON/OFF、権限拒否、オフライン起動を確認する。予定変更・中止後は保存済みの通知を取り消して再予約する。通知はOS制約による遅延があり、週2回の収集だけで直前変更の検知までは保証しない。
