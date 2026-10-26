# みのがさナイト — 番組データ配信

VICTORY K。東京・千葉の地上波と無料BSで確認できた放送予定の最小JSONをGitHub Pagesで配信します。

月曜・木曜にしょぼいカレンダーAPIのアニメ予定と管理者が確認した公式情報を統合し、過去枠・重複・形式を検証します。詳細は [運用手順](docs/phase4/OPERATIONS.md) と [形式](docs/phase4/FORMAT.md) を参照してください。

公開JSON： https://tachikawagumi.github.io/minogasa-night/v1/programs.json

2026-10-26にHTTP 200・実データ146枠を確認。GitHub Actions #2でvalidate・refresh・deployが成功しました。

紹介文・出演者・画像・認証情報は配信しません。対象局の全番組を網羅するものではありません。
