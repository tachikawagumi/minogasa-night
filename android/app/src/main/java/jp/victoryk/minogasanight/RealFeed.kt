package jp.victoryk.minogasanight

import android.content.Context
import com.google.gson.JsonParser
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL
import java.io.ByteArrayOutputStream
import java.time.Instant
import java.time.LocalDate
import java.time.OffsetDateTime

data class FeedSnapshot(val programs: List<Listing>, val generatedAt: Long, val notice: String, val windowEnd: Long)

object FeedDecoder {
    private fun instant(value: String): Long = OffsetDateTime.parse(value).toInstant().toEpochMilli()
    fun decode(text: String, now: Long = System.currentTimeMillis()): FeedSnapshot {
        require(text.length <= 2_000_000) { "番組データが大きすぎます" }
        val root = JsonParser.parseString(text).asJsonObject
        require(root["schemaVersion"].asInt == 1 && root["sourceMode"].asString == "real" && root["timeZone"].asString == "Asia/Tokyo")
        val generated = instant(root["generatedAt"].asString)
        val windowStart = instant(root["windowStart"].asString)
        val windowEnd = instant(root["windowEnd"].asString)
        require(generated <= now + 300_000 && windowEnd > windowStart)
        val genreMap = root["genres"].asJsonArray.associate { val o = it.asJsonObject; o["id"].asString to o["name"].asString }
        require(genreMap.size == 20 && genreMap.values.toSet() == genres.toSet())
        val stations = root["stations"].asJsonArray.associate { val o = it.asJsonObject; o["id"].asString to o["name"].asString }
        val ids = mutableSetOf<String>()
        val rows = root["programs"].asJsonArray.map { element ->
            val p = element.asJsonObject
            val id = p["id"].asString
            val series = p["seriesId"].asString
            val title = p["title"].asString
            val start = instant(p["start"].asString)
            val end = p["end"]?.takeUnless { it.isJsonNull }?.asString?.let(::instant) ?: start
            val tags = p["genreIds"].asJsonArray.map { requireNotNull(genreMap[it.asString]) }.toSet()
            require(ids.add(id) && id.isNotBlank() && series.isNotBlank() && title.isNotBlank() && !title.contains("サンプル"))
            require(start >= windowStart && start < windowEnd && end >= start && tags.isNotEmpty())
            require(p["status"].asString in setOf("official_confirmed", "provider_confirmed"))
            Listing(id, series, title, "", requireNotNull(stations[p["stationId"].asString]), start, end, tags, sample = false)
        }
        val notice = buildList {
            if (root["updateStatus"].asString != "ok") add("一部の情報を更新できていません。保存済みの予定を含みます。")
            if (now >= windowEnd || now - generated > 4 * 86_400_000L) add("番組データが古くなっています。更新してください。")
        }.joinToString("\n")
        return FeedSnapshot(normalized(rows), generated, notice, windowEnd)
    }
}

class HttpProgramSource(private val endpoint: () -> String, private val open: (URL) -> HttpURLConnection = { it.openConnection() as HttpURLConnection }) : ProgramSource {
    override suspend fun fetch(today: LocalDate) = fetchFeed(today).programs
    override suspend fun fetchFeed(today: LocalDate): FeedSnapshot = withContext(Dispatchers.IO) {
        val url = URL(endpoint().trim().ifEmpty { throw IllegalStateException("配信先未設定") })
        require(url.protocol == "https" && url.userInfo == null) { "HTTPSの配信先が必要です" }
        val connection = open(url)
        connection.connectTimeout = 15_000
        connection.readTimeout = 20_000
        connection.instanceFollowRedirects = false
        connection.setRequestProperty("User-Agent", "MinogasaNight/1.0 (VICTORY K)")
        connection.setRequestProperty("Accept", "application/json")
        try {
            require(connection.responseCode == 200) { "配信先の応答が正常でありません" }
            val bytes = connection.inputStream.use { stream ->
                val output = ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                while (true) {
                    val count = stream.read(buffer)
                    if (count < 0) break
                    require(output.size() + count <= 2_000_000)
                    output.write(buffer, 0, count)
                }
                output.toByteArray()
            }
            require(bytes.size <= 2_000_000)
            FeedDecoder.decode(bytes.toString(Charsets.UTF_8))
        } finally { connection.disconnect() }
    }
}

suspend fun bundledFeed(context: Context): FeedSnapshot = withContext(Dispatchers.IO) {
    FeedDecoder.decode(context.assets.open("initial-programs.json").bufferedReader().use { it.readText() })
}

fun visibleNow(p: Listing, period: Int, today: LocalDate, now: Long): Boolean = !p.sample && p.start > now && inPeriod(p, period, today)
