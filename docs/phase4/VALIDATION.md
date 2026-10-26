# 第4次開発 最終検証結果（2026-10-26）

既存アプリを改修した v0.2.0-realdata。専用GitHubへの反映、Pages配信、アプリ本体のHTTP取得処理による実JSON読込、APKビルドを確認した。

## 配信と接続

- 公開JSON：https://tachikawagumi.github.io/minogasa-night/v1/programs.json
- HTTP 200、Content-Type application/json; charset=utf-8、実データ146枠、20ジャンル定義。生成時刻 2026-10-26T13:29:12+09:00。
- GitHub Actions #2でvalidate・refresh・deployが全て成功。実行：https://github.com/tachikawagumi/minogasa-night/actions/runs/40269291649
- publishedGitHubPagesUsesProductionHttpClientテストで、APKと同じHttpProgramSourceとFeedDecoderを実際のHTTPS URLへ接続し、非サンプルの番組取得と将来枠の存在を確認。JVM上での本体コードの検証であり、実機の画面操作と区別する。
- APKのBuildConfigに公開URLが設定されていることと、APK内の初期実データが取得した公開JSONと一致することを検証。

## テスト・ビルド

- Androidテスト：14件成功、失敗0、エラー0、スキップ0。公開先への接続、日付・ジャンル、キャッシュ保持、正しい0件更新後の再初期化防止を含む。
- データ処理テスト：16件成功。GitHubのvalidateジョブでも成功。
- Lint：エラー0。詳細はverification内のXML/HTML。
- 最終ビルド：BUILD SUCCESSFUL。minSdk26（Android8.0）、targetSdk35、versionCode2。
- APKのv2署名検証成功。試用用Android Debug署名でありストア公開用の正式署名ではない。
- APK SHA-256：c9cf6212d9aebe40ade38b51d1fc450bc012be2f4b731d7fd5ef785f6c65048d

## 運用

- アニメ取得・JSON更新・Pages配信：月曜・木曜06:17 JST。標準Ubuntuランナー。予定実行はGitHub側で遅れる場合がある。
- AI公式調査：月曜・木曜09:00 JST、下書きまで。管理者承認なしに公開しない。10/26の16枠の下書きは承認前のまま保持。
- 全20ジャンルを定義するが、全局・全番組の網羅はしていない。紹介文・出演者・画像・秘密情報を公開JSONに入れない。
- 有料API・追加契約・Cloudflareを使用していない。公開リポジトリとPagesの無料枠を使う構成。
- 太刀川組・PALカリのリポジトリ・公開サイトは変更していない。

## 残る確認

Android実機は接続されていないため、実機のインストール、実画面、通知実到達、権限操作、3秒表示の実測は未検証。AIが管理者承認を経ず完全自動でGitHubへ書き込む運用は採用していない。

## 納品

MinogasaNight-0.2.0-realdata-debug.apk、MinogasaNight-0.2.0-project.zip、MinogasaNight-github-pages.zip、validation.json。

ローカルのネットワーク接続テストは環境変数 MINOGASA_VERIFY_LIVE=1 を設定して testDebugUnitTest を実行すると有効になる。通常のオフラインテストでは当該1件をスキップする。
