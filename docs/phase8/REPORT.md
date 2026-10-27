# 第8次改修 検証レポート
VICTORY K — MINOGASA NIGHT

## 結果
2026-10-27 日本時間に調査。対象は10/27 00:00〜11/3 00:00（当日を含む7暦日）、東京・千葉の地上波・無料BS。
実装コミット e656806baa6a87a14db0e950c11596586202bb71。
[GitHub Actions実行40462571234](https://github.com/tachikawagumi/minogasa-night/actions/runs/40462571234) はvalidate・refresh・deployがすべて成功、rollbackは不要でskipped。
[公開JSON](https://tachikawagumi.github.io/minogasa-night/v1/programs.json) はHTTP200、151枠、13ジャンル。
Pages完全一致確認 2026-10-27T15:41:52+09:00、semantic SHA256 7c60394c4af821c678dbcf30d43c94f2409be99a5d3198dd86a7f393a808b425。

## 公開判定の改善と再評価
一律の「文章/番組表再配信の許諾」を要求する経路に加え、取得方法・最小事実の独立記録・利用条件を個別判断する経路を追加。
config/source-policy.json の reviewed_independent_facts は包括的なサイト利用許諾ではない。
確認済みURL、取得方式、本文非転載、非大量取得、非会員サービス利用、照合した最小事実のスナップショット、確認日時を全て照合する。日時変更は新しい根拠に一致するスナップショットが必要。旧日時の確認だけでは更新できない。
未知のURL・クローリング方式・本文複製・スナップショット不一致は保留。

| 対象 | 公式に確認した放送予定（JST） | 判定 |
|---|---|---|
| ケンコバのほろ酔いビジホ泊 全国版 | BS朝日 10/29 22:30–23:00 | 新規公開、旅＋温泉 |
| 辰巳琢郎の家物語 リモデル★きらり | BS朝日 10/31 12:00–12:30 | 新規公開、建物探訪 |
| THEフィッシング | テレビ東京 10/31 17:30–18:00 | 新規公開、釣り |
| 頂の先へ！ゴルフ対決 後編 | BS朝日 10/31 15:00–15:54 | 新規公開、ゴルフ |
| 幻魔大戦 | BS12 11/1 19:00、終了不明null | 新規公開、映画＋アニメ |
| カーグラフィックTV | BS朝日 10/29 23:00–23:30 | 既存IDの終了情報更新 |
| ダークサイド 不老不死 | 公式の今回の放送日時は未確認 | 保留。配信作品の実在から再放送日時を推定しない |
| ダークサイド 地獄 | 公式の今回の放送日時は未確認 | 保留。第三者掲載だけで確定しない |
| おいち不思議がたり | 公式の今回の再放送日時は未確認 | 保留 |
| 極上ゴルフ場探訪 | 確認できた回は10/26 | 過去。翌週へ動かさない |
| 温泉事件簿／潔癖クン | 当該回の内容・日時の照合不足 | 引き続き保留。タイトルだけで温泉/心霊に分類しない |

情報源と分類根拠はdata/source-checks.json、再評価はdata/phase8-reevaluation.json。
[ケンコバ公式](https://www.bs-asahi.co.jp/business_hotel/)、[家物語公式](https://www.bs-asahi.co.jp/tatsumi/)、[釣り公式](https://www.tv-tokyo.co.jp/broad_tvtokyo/program/detail/202610/13037_202610311730.html)、[ゴルフ公式](https://www.bs-asahi.co.jp/itadakinosakie/)、[車公式](https://www.bs-asahi.co.jp/cgtv/)を当該回で照合。
『幻魔大戦』は[BS12運営会社自身の公開発表](https://www.atpress.ne.jp/news/2830607)を一次情報として確認した。
[@Press規約](https://www.atpress.ne.jp/term_use)の会員・配信サービスの定義等を再確認し、公開読者として個別の放送事実だけ独自記録する判断を保存。本文・画像・DB配信サービスは利用せず、ポータル全体の取得許可を主張しない。
BS朝日は番組ページ末尾の権利注意、テレビ東京は[リンクと著作権](https://www.tv-tokyo.co.jp/index/company/link.html)を参照。放送番組/紹介文/画像と最小事実の区別に基づく個別判断であり、放送局からライセンスを取得したという意味ではない。

## 情報源と発見経路
config/discovery.json に役割 discovery / broadcast_facts / genre_classification と取得方法・条件を追加。全20ジャンルに情報源・タイトル・当該回予告全文・局別予定・専門サイト・取りこぼし再検索を設定。
scripts/discovery.py --plan は100経路の計画を生成。実行済みログは別管理し、計画だけで調査済みにしない。

| 発見元 | 今回の結果 | 継続取得 |
|---|---|---|
| occultic | 403。制限を回避せず公式で代替調査 | スクレイピングを追加していない |
| entafukuzou | 個別候補を発見。幻魔大戦は公式発表へ照合。サイコは公式予定未照合で保留 | 発見用個別参照のみ |
| ALBA | 見えた日程は過去の10/22–25。CS/配信混在も確認 | 無料テレビ枠を公式照合 |
| sports.yahoo | 野球・サッカーで検索。試合の開催とテレビの放送を区別 | 専門サイトの表を複製しない |
| J:COM鉄道 | この環境で取得できず。局公式の検索も実行 | 制限回避を行わない |
| しょぼいカレンダー | Actionsの既存連携が正常更新 | API・UA・直列間隔は変更なし |
| 放送局個別ページ | 上記6件を再照合し公開判定 | 個別参照の範囲のみ |

今回新しく台帳へ追加した候補は2件：サイコ（公式日時/局照合待ち）、有料WOWOWの映画候補（有料局で除外）。
既存候補を6件再照合し、5件の初回公開と1件の情報更新につなげた。NHK3件の再評価結果にも具体的な保留理由を記録した。専門サイトの大量複製は行っていない。
検索は接続されたWeb検索による公式ページ/予告の索引検索。全局の週間番組表本文を取得するクローラーは導入していない。

## 全20ジャンル
今回保存した実行ログは20件（各ジャンル1件）。個別ページ参照はこの件数に含めない。
以下の候補・日時確認は既存分を含む累積台帳で、過去枠・除外候補も含む。新規発見件数と混同しない。公開枠は現行JSONの対象期間内。複数ジャンルの枠は各行で数えるため合計は151と一致しない。
| ジャンル | 今回の検索ログ | 累積候補 | 日時確認 | 公開枠 | 0件の理由 |
|---|---:|---:|---:|---:|---|
| 心霊・怪談 | 1 | 4 | 1 | 1 | — |
| UFO・都市伝説 | 1 | 3 | 1 | 1 | — |
| 映画 | 1 | 8 | 6 | 4 | — |
| ホラー映画 | 1 | 2 | 0 | 0 | 情報源不足・個別の公式予定未確認（不存在とは断定しない） |
| ディズニー | 1 | 0 | 0 | 0 | 情報源不足・個別の公式予定未確認（不存在とは断定しない） |
| USJ | 1 | 0 | 0 | 0 | 情報源不足・個別の公式予定未確認（不存在とは断定しない） |
| 大食い | 1 | 1 | 1 | 1 | — |
| 温泉 | 1 | 2 | 1 | 1 | — |
| 建物探訪 | 1 | 1 | 1 | 1 | — |
| 車 | 1 | 1 | 1 | 1 | — |
| ダンス | 1 | 0 | 0 | 0 | 情報源不足・個別の公式予定未確認（不存在とは断定しない） |
| ゴルフ | 1 | 3 | 3 | 1 | — |
| サッカー | 1 | 0 | 0 | 0 | 情報源不足・個別の公式予定未確認（不存在とは断定しない） |
| 野球 | 1 | 1 | 1 | 1 | — |
| 釣り | 1 | 1 | 1 | 1 | — |
| 健康 | 1 | 1 | 0 | 0 | 情報源不足・個別の公式予定未確認（不存在とは断定しない） |
| 旅 | 1 | 1 | 1 | 2 | — |
| ゲーム・チャレンジ | 1 | 1 | 1 | 2 | — |
| アニメ | 1 | 3 | 3 | 136 | — |
| 電車・鉄道 | 1 | 0 | 0 | 0 | 情報源不足・個別の公式予定未確認（不存在とは断定しない） |

0件のホラー映画・ディズニー・USJ・ダンス・サッカー・健康・電車・鉄道は、公式の今回予定/内容または情報源が不足しており「放送が存在しない」と断定していない。
サイコ候補のNHK BSP4Kは未照合かつ現在の局設定外。有料と決めつけず追加確認待ち。
対象局はconfig/stations.jsonの検証済み18局。未知の無料局やNHK BSP4K等を全て網羅した状態ではない。受信機器・NHK受信契約と追加の有料専門チャンネル契約を区別する。

## 差分と品質
今回の差分は26追加（再評価による公式5枠＋アニメAPI等21枠）、番組情報変更1、ジャンル変更0、将来枠削除1、自然な過去化21。
削除/過去化を今回の公開改善5件と混同しない。公開JSONはスキーマ1、ID/シリーズIDを維持し重複枠を作っていない。
台帳28候補、公開受け渡しエラー0、公式日時確認済みの未来枠で公開に届いていないもの0。
品質JSONのheld=18は「現在の候補再投入の審査状態」を表し、そのうち7件は従来の承認経路で既に同じ枠が公開中、4件は過去。現行公開から漏れた未確認未来候補は7件。これらを18件の表示漏れとは数えない。
legacyの承認済み公開と、今のAI再投入ポリシーの未確認を区別し、未確認ソースを包括的に有効化していない。
不正・全件消失・大量消失・取得失敗時の正常JSON保持、中止の明示根拠、日時/ジャンル変更、ID維持の既存テストも継続。

## テスト
Python 77件成功。実データ6件のオフライン受け渡しテストも成功（scripts/phase8_preflight.py、2026-10-27の再現用診断）。
Android JVM 17件成功（RealFeedTest 9、ProgramTest 5、Phase6/7/8LiveTest 各1）、失敗0。
本番 HttpProgramSource と既存の期間・タグ処理で151枠をHTTPS取得。新たな5枠の番組名/局/日時/分類、幻魔大戦の終了不明、今日/明日/1週間、複数ジャンル、既存お気に入りIDの維持を検証。
既存テストの通信失敗/キャッシュ保持も成功。お気に入りはキー互換性の検証であり、実機でのタップ操作やRoomの機種更新移行を今回実行したわけではない。実機UI表示は未確認。
旧Phase7テストの「幻魔大戦は不在」という期待値は、公開可能になったため外した。NHK保留3枠の不在チェックは維持。
APK再ビルドなし。v0.2.0のSHA256は C9CF6212D9AEBE40ADE38B51D1FC450BC012BE2F4B731D7FD5EF785F6C65048D のまま。

## 無人運用・費用・承認削減
既存automation ID automation を更新し月木09:00 Asia/Tokyoを維持。重複タスクなし。専門情報源・局フィルター・個別事実審査・実行ログを既存プロンプトへ接続した。
GitHub Actionsの月木00:00 UTCも維持。AI調査と同時刻でも、その後の候補コミットpushで再公開される。
今回の対話環境でGitHub書込→Actions→Pages→ライブJSON確認は成功した。
**無人でのAI Web検索/全20ジャンルの継続発掘/無人GitHub書込は未検証。次回10/29の実行証跡が揃うまで完成扱いにしない。**
GitHub Actions単体に無料AI検索機能を付けたとは報告しない。現在の許諾済みAPIによるアニメ自動取得と条件付き公開は稼働している。
追加の有料API/EPG/サーバー/Cloudflareは導入せず追加月額費用0円。ChatGPT等の既存利用枠の消費はある。
太刀川組/PALカリは変更していない。

必要ファイルをまとめて読み、複数ファイルを一括編集、一括テスト、実装を1コミットで反映した。テストで見つかった検索経路数の期待値だけ公開前に修正した。ファイル毎の許可質問はしていない。システムの権限確認は遵守した。最終検証レポートは公開結果を確認してから別の文書コミットとして保存する。

## Android検証の再現
既存プロジェクトのapp/src/test/java/jp/victoryk/minogasanightに以下のクラスを置き、MINOGASA_VERIFY_LIVE=1で :app:testDebugUnitTest を実行する。旧Phase7LiveTestの幻魔大戦不在チェックだけ外す。対象枠が過去化した後は現行の確認済み枠で期待値を更新する。アプリ本体の変更は不要。

```kotlin
package jp.victoryk.minogasanight

import org.junit.Assert.*
import org.junit.Test
import kotlinx.coroutines.runBlocking
import java.time.*

class Phase8LiveTest {
    @Test fun newlyReleasedFactsWorkWithExistingClientAndFilters() = runBlocking {
        org.junit.Assume.assumeTrue(System.getenv("MINOGASA_VERIFY_LIVE") == "1")
        val today=LocalDate.now(Tokyo)
        val snapshot=HttpProgramSource(endpoint={BuildConfig.FEED_URL}).fetchFeed(today)
        val expected=mapOf(
            "official-5175d86a5b23c2d551acb056" to setOf("旅","温泉"),
            "official-bab590a4f8e59ce88597843a" to setOf("建物探訪"),
            "official-tvtokyo-20261031-1730-thefishing" to setOf("釣り"),
            "official-bsasahi-20261031-1500-itadaki" to setOf("ゴルフ"),
            "official-bs12-20261101-1900-genma" to setOf("映画","アニメ")
        )
        expected.forEach { (id,tags) ->
            val p=snapshot.programs.single { it.id==id }
            assertEquals(tags,p.tags)
            assertTrue(visibleNow(p,2,today,System.currentTimeMillis()))
            val date=Instant.ofEpochMilli(p.start).atZone(Tokyo).toLocalDate()
            assertEquals(date==today,inPeriod(p,0,today))
            assertEquals(date==today.plusDays(1),inPeriod(p,1,today))
            assertFalse(p.sample)
            assertTrue(p.description.isEmpty())
        }
        val g=snapshot.programs.single { it.id=="official-bs12-20261101-1900-genma" }
        assertEquals("幻魔大戦",g.title)
        assertEquals("BS12トゥエルビ",g.station)
        assertEquals(OffsetDateTime.parse("2026-11-01T19:00:00+09:00").toInstant().toEpochMilli(),g.start)
        assertEquals(g.start,g.end) // Null end uses the existing decoder's start fallback.
        val hon=snapshot.programs.single { it.id=="official-f9558d382a201f8b6603526e" }
        assertEquals("official-series-2b9729b602a554921245711f",hon.seriesId)
        assertFalse(snapshot.programs.any { it.id.startsWith("phase7-darkside") || it.id.startsWith("phase7-oichi") || it.id.startsWith("phase8-paid") })
        println("PHASE8_LIVE_OK reviewed_nonanime=true genmaUnknownEnd=true dateAndGenreFilters=true stableFavoriteIdentity=true")
    }
}
```
