# みのがさナイト Android 0.3.0
VICTORY K / Android 8.0 (API26)以上 / Kotlin + Jetpack Compose

既存0.2.0のプロジェクトを継続した第11次UI改修。番組収集・公開処理と月木09:00の定期設定は変更しない。

## ビルド
Android Studioでこのフォルダーを開きSDKの場所を指定する。JDK17以上、Android SDK35、Build Tools35.0.0、Gradle8.9。
Windowsは gradlew.bat :app:testDebugUnitTest :app:lintDebug :app:assembleDebug を実行する。
公開先の実通信試験を含める場合のみ環境変数 MINOGASA_VERIFY_LIVE=1 を指定する。過去フェーズの実通信試験には当時の放送枠が必要なので、対象期間経過後は通常のローカル回帰試験を使用する。
公開JSON：https://tachikawagumi.github.io/minogasa-night/v1/programs.json

## お気に入り
この回は既存のp:番組ID、毎回チェックは既存のs:シリーズIDを保存する。Room night.db、スキーマversion2、設定のDataStore名とキーは変更していない。
お気に入り一覧はジャンル設定を無視し、選択した今日・明日・1週間内の開始前の枠を日時順に表示する。1週間は今日を含む7暦日、Asia/Tokyo。登録済みでも期間内に枠がなければ専用メッセージを表示する。
単発作品・放送枠由来のシリーズIDでは毎回チェックを隠す。映画は一律ではなく、現行のゴジラ作品群とダイ・ハード作品群の既存IDを継続対象として明示管理する。新しい映画枠・作品群は同じIDが何を指すかを確認してBrowse.ktの対象を追加する。映画枠を勝手に新しいIDへまとめ直さない。
旧アプリで単発作品のシリーズキーを保存していた場合も一覧に含め、登録を解除ボタンで解除できる。データの勝手な変換・削除はしない。
通知は別設定。お気に入り操作は通知設定をONにしない。

## 情報提供元
設定画面の情報提供元にクレジットとしょぼいカレンダーへのリンクをまとめた。通常カードに取得元・確認状況・紹介文・画像・出演者を表示しない。通信失敗、データ期限切れ、一部更新失敗は表示する。
しょぼいカレンダー利用案内：https://docs.cal.syoboi.jp/about/
既存のサーバー取得はUser-Agent MinogasaNight/1.0 (VICTORY K)を維持。
利用URL： https://cal.syoboi.jp/db.php
- Command=ProgLookup、Range=開始_終了、ChID=対象局、Fields=PID,TID,ChID,StTime,EdTime,LastUpdate,Deleted,Warn,Revision
- Command=TitleLookup、TID=対象作品ID、Fields=TID,Title,Cat,LastUpdate
アプリは上記APIへ直接アクセスせず公開JSONを取得する。ソース記録・検証ログは配信リポジトリで保持する。

## インストール
debug APKは検証用。同じ署名・アプリIDの旧版へ上書きインストールし、データ保持のため旧版をアンインストールしない。署名違いのエラーが出た場合も、データを消さず管理者へ確認する。
SDK、JDK、ローカル設定、署名鍵、キャッシュはソースZIP・公開リポジトリに含めない。
