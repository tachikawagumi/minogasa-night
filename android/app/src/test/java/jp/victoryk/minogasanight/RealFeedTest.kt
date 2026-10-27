package jp.victoryk.minogasanight

import com.google.gson.JsonParser
import org.junit.Assert.*
import org.junit.Test
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import java.io.File
import java.io.ByteArrayInputStream
import java.net.HttpURLConnection
import java.net.URL
import java.time.*

class RealFeedTest {
    private val now get() = OffsetDateTime.parse(JsonParser.parseString(json()).asJsonObject["generatedAt"].asString).toInstant().toEpochMilli() + 60_000
    private fun json() = File("src/test/resources/feed-20261024.json").readText()
    @Test fun publishedGitHubPagesUsesProductionHttpClient() = runBlocking {
        org.junit.Assume.assumeTrue(System.getenv("MINOGASA_VERIFY_LIVE") == "1")
        val snapshot = HttpProgramSource(endpoint = { BuildConfig.FEED_URL }).fetchFeed(LocalDate.now(Tokyo))
        assertTrue(snapshot.programs.isNotEmpty())
        assertTrue(snapshot.programs.all { !it.sample && it.description.isEmpty() })
        assertTrue(snapshot.windowEnd > System.currentTimeMillis())
        val future = snapshot.programs.count { it.start > System.currentTimeMillis() }
        assertTrue(future > 0)
        println("LIVE_PAGES_OK url=${BuildConfig.FEED_URL} rows=${snapshot.programs.size} future=$future")
    }
    @Test fun realCollectedFeedDecodesWithoutSamplesOrDescriptions() {
        val snapshot = FeedDecoder.decode(json(), now)
        assertTrue(snapshot.programs.size > 30)
        assertTrue(snapshot.programs.all { !it.sample && it.description.isEmpty() && it.tags.isNotEmpty() })
        assertTrue(snapshot.programs.any { it.tags.contains("映画") })
        assertTrue(snapshot.programs.any { it.tags.contains("アニメ") })
        assertTrue(snapshot.programs.any { it.title.contains("フィッシング") })
    }
    @Test fun invalidModeAndUnknownGenreRejectWholeResponse() {
        for (edit in listOf<(com.google.gson.JsonObject) -> Unit>(
            { it.addProperty("sourceMode", "sample") },
            { it["programs"].asJsonArray[0].asJsonObject["genreIds"].asJsonArray.add("unknown") },
            { it["programs"].asJsonArray[0].asJsonObject.addProperty("status", "pending") }
        )) {
            val root = JsonParser.parseString(json()).asJsonObject
            edit(root)
            assertThrows(Exception::class.java) { FeedDecoder.decode(root.toString(), now) }
        }
    }
    @Test fun pastAndEighthDayNeverDisplay() {
        val snapshot = FeedDecoder.decode(json(), now)
        val date = LocalDate.of(2026, 10, 24)
        assertTrue(snapshot.programs.filter { visibleNow(it, 0, date, now) }.all { it.start > now })
        val p = snapshot.programs.first()
        assertFalse(visibleNow(p.copy(start = now - 1), 0, date, now))
        assertFalse(visibleNow(p.copy(start = date.plusDays(7).atStartOfDay(Tokyo).toInstant().toEpochMilli()), 2, date, now))
        assertFalse(visibleNow(p.copy(sample = true), 2, date, now))
    }
    @Test fun dateAndSelectedGenreMatchRealFeed() {
        val snapshot = FeedDecoder.decode(json(), now)
        val date = LocalDate.of(2026, 10, 24)
        val tomorrow = snapshot.programs.filter { visibleNow(it, 1, date, now) }
        assertTrue(tomorrow.isNotEmpty())
        assertTrue(tomorrow.all { Instant.ofEpochMilli(it.start).atZone(Tokyo).toLocalDate() == date.plusDays(1) })
        assertTrue(snapshot.programs.any { visibleNow(it, 2, date, now) && "映画" in it.tags })
    }
    @Test fun expiredFeedShowsWarningAndNoOldPrograms() {
        val old = now + 8 * 86_400_000L
        val snapshot = FeedDecoder.decode(json(), old)
        assertTrue(snapshot.notice.contains("古く"))
        assertTrue(snapshot.programs.none { visibleNow(it, 2, Instant.ofEpochMilli(old).atZone(Tokyo).toLocalDate(), old) })
    }
    @Test fun httpsResponseIsDecodedAndErrorIsRejected() = runBlocking {
        val valid = HttpProgramSource({ "https://feed.example.test/v1/programs.json" }, { FakeConnection(it, 200, json()) })
        assertTrue(valid.fetch(LocalDate.now(Tokyo)).isNotEmpty())
        val bad = HttpProgramSource({ "https://feed.example.test/v1/programs.json" }, { FakeConnection(it, 503, "") })
        try { bad.fetch(LocalDate.now(Tokyo)); fail("503 accepted") } catch (_: IllegalArgumentException) { }
        val cleartext = HttpProgramSource({ "http://feed.example.test/v1/programs.json" })
        try { cleartext.fetch(LocalDate.now(Tokyo)); fail("HTTP accepted") } catch (_: IllegalArgumentException) { }
    }
    @Test fun confirmedEmptyFeedDoesNotResurrectBundledPrograms() = runBlocking {
        val snapshot = FeedDecoder.decode(json(), now)
        val dao = MemoryDao(emptyList())
        val source = object : ProgramSource { override suspend fun fetch(today: LocalDate) = emptyList<Listing>() }
        val repo = Repository(dao, source)
        repo.prepare { snapshot }
        assertTrue(dao.all().isNotEmpty())
        repo.refresh()
        repo.prepare { fail("confirmed empty cache must not be seeded again"); snapshot }
        assertTrue(dao.all().isEmpty())
    }
    @Test fun failedRefreshKeepsLastGoodDatabaseAndValidEmptyRefreshClearsIt() = runBlocking {
        val snapshot = FeedDecoder.decode(json(), now)
        val dao = MemoryDao(snapshot.programs.take(2).map { it.row() })
        val failing = object : ProgramSource { override suspend fun fetch(today: LocalDate): List<Listing> = throw java.io.IOException("offline") }
        try { Repository(dao, failing).refresh(); fail("expected offline") } catch (_: java.io.IOException) { }
        assertEquals(2, dao.all().size)
        val empty = object : ProgramSource { override suspend fun fetch(today: LocalDate) = emptyList<Listing>() }
        Repository(dao, empty).refresh()
        assertTrue(dao.all().isEmpty())
    }
}

private class FakeConnection(url: URL, private val status: Int, private val body: String) : HttpURLConnection(url) {
    override fun connect() { }
    override fun disconnect() { }
    override fun usingProxy() = false
    override fun getResponseCode() = status
    override fun getInputStream() = ByteArrayInputStream(body.toByteArray())
}

private class MemoryDao(initial: List<ProgramRow>) : NightDao {
    private val rows = MutableStateFlow(initial)
    private val state = MutableStateFlow<SyncState?>(null)
    override fun observe(): Flow<List<ProgramRow>> = rows
    override suspend fun all() = rows.value
    override fun favorites(): Flow<List<Favorite>> = MutableStateFlow(emptyList())
    override suspend fun saved() = emptyList<Favorite>()
    override suspend fun save(favorite: Favorite) { }
    override suspend fun unsave(key: String) { }
    override suspend fun clear() { rows.value = emptyList() }
    override suspend fun clearSamples() { rows.value = rows.value.filterNot { it.sample } }
    override suspend fun insert(rows: List<ProgramRow>) { this.rows.value = rows }
    override suspend fun stamp(state: SyncState) { this.state.value = state }
    override fun updated(): Flow<Long?> = MutableStateFlow(null)
    override fun sync(): Flow<SyncState?> = state
}
