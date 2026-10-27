package jp.victoryk.minogasanight

import java.time.*

val Tokyo: ZoneId = ZoneId.of("Asia/Tokyo")
val genres = listOf("心霊・怪談", "UFO・都市伝説", "映画", "ホラー映画", "ディズニー", "USJ", "大食い", "温泉", "建物探訪", "車", "ダンス", "ゴルフ", "サッカー", "野球", "釣り", "健康", "旅", "ゲーム・チャレンジ", "アニメ", "電車・鉄道")

object Classifier {
    private val rules = listOf(
        listOf("心霊", "怪談", "幽霊"), listOf("UFO", "都市伝説", "未確認飛行"),
        listOf("映画", "シネマ"), listOf("ホラー映画", "恐怖映画"), listOf("ディズニー"), listOf("USJ", "ユニバーサル・スタジオ"),
        listOf("大食い", "デカ盛り"), listOf("温泉", "秘湯"), listOf("建物探訪", "豪邸", "素敵な家", "住宅紹介"),
        listOf("車", "自動車", "ドライブ"), listOf("ダンス", "踊り"), listOf("ゴルフ"), listOf("サッカー"), listOf("野球"),
        listOf("釣り", "マグロ漁師", "大間"), listOf("健康", "体操"),
        listOf("旅", "街歩き", "ブラタモリ", "モヤモヤさまぁ"), listOf("ゲーム", "チャレンジ", "逃走中", "戦闘中", "SASUKE"),
        listOf("アニメ"), listOf("電車", "鉄道", "列車")
    )
    fun classify(text: String): Set<String> = genres.filterIndexed { index, _ ->
        val target = if (index == 9) text.replace("電車", "").replace("列車", "").replace("貨車", "").replace("客車", "") else text
        rules[index].any { target.contains(it, ignoreCase = true) }
    }.toSet()
    fun features(text: String): List<String> = listOf("マグロ漁師", "大間", "街歩き", "ブラタモリ", "モヤモヤさまぁ", "逃走中", "戦闘中", "SASUKE", "豪邸", "素敵な家").filter { text.contains(it, true) }
}

data class Listing(
    val id: String, val seriesId: String, val title: String, val description: String,
    val station: String, val start: Long, val end: Long, val tags: Set<String>,
    val sample: Boolean = true, val rerunConfirmed: Boolean = false
)

fun normalized(list: List<Listing>): List<Listing> = list.groupBy { Triple(it.station, it.start, it.title.trim()) }.values.map { group ->
    group.first().copy(tags = group.flatMap { it.tags }.toSet(), rerunConfirmed = group.any { it.rerunConfirmed })
}.sortedBy { it.start }
fun inPeriod(p: Listing, period: Int, now: LocalDate): Boolean {
    val date = Instant.ofEpochMilli(p.start).atZone(Tokyo).toLocalDate()
    return when (period) { 0 -> date == now; 1 -> date == now.plusDays(1); else -> date >= now && date < now.plusDays(7) }
}

/** Replace only with a provider whose distribution/cache/notification rights have been approved. */
interface ProgramSource {
    suspend fun fetch(today: LocalDate): List<Listing>
    suspend fun fetchFeed(today: LocalDate): FeedSnapshot = FeedSnapshot(fetch(today), System.currentTimeMillis(), "", 0)
}

class SampleSource : ProgramSource {
    override suspend fun fetch(today: LocalDate): List<Listing> = (0L..6L).flatMap { day ->
        genres.mapIndexed { index, genre ->
            val detail = when (genre) {
                "釣り" -> "マグロ漁師・大間をテーマにした特集例。"
                "旅" -> "街歩きをテーマにした特集例。"
                "建物探訪" -> "豪邸・素敵な家紹介をテーマにした特集例。"
                "ゲーム・チャレンジ" -> "ゲームと運動チャレンジをテーマにした企画例。"
                else -> "$genre をテーマにした番組の表示例。"
            }
            val start = today.plusDays(day).atTime(6 + index * 50 / 60, index * 50 % 60).atZone(Tokyo).toInstant().toEpochMilli()
            Listing("sample-${today.plusDays(day)}-$index", "sample-series-$index", "【サンプル】$genre の時間", "実在する番組・放送予定ではありません。$detail", listOf("東京地上波（サンプル）", "千葉地上波（サンプル）", "無料BS（サンプル）")[index % 3], start, start + 45 * 60_000, Classifier.classify("$genre $detail") + genre)
        }
    }
}
