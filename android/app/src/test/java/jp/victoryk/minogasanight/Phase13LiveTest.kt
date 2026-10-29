package jp.victoryk.minogasanight
import org.junit.Assert.*
import org.junit.Test
import kotlinx.coroutines.runBlocking
import java.time.*
class Phase13LiveTest {
    @Test fun newlyPublishedGolfAiringsUseExistingAndroidClient() = runBlocking {
        org.junit.Assume.assumeTrue(System.getenv("MINOGASA_VERIFY_PHASE13")=="1")
        val today=LocalDate.now(Tokyo)
        val now=System.currentTimeMillis()
        val snapshot=HttpProgramSource(endpoint={BuildConfig.FEED_URL}).fetchFeed(today)
        val expected=mapOf(
            "official-tvtokyo-20261101-2320-weekly-women-golf" to "2026-11-01T23:20:00+09:00",
            "official-bsasahi-20261102-2154-golfmatch" to "2026-11-02T21:54:00+09:00",
            "official-bsasahi-20261102-2230-golfjotanbo" to "2026-11-02T22:30:00+09:00",
            "official-bsasahi-20261031-1700-mitsubishi-ladies" to "2026-10-31T17:00:00+09:00",
            "official-bstvtokyo-20261101-0800-golf-samurai" to "2026-11-01T08:00:00+09:00",
            "official-bstvtokyo-20261101-0730-golf-koyusho" to "2026-11-01T07:30:00+09:00",
            "official-fuji-20261101-1605-vantelin-final" to "2026-11-01T16:05:00+09:00",
            "official-bs11-20261101-1730-akane-golf" to "2026-11-01T17:30:00+09:00"
        )
        expected.forEach { (id,start) ->
            val p=snapshot.programs.single { it.id==id }
            assertEquals(OffsetDateTime.parse(start).toInstant().toEpochMilli(),p.start)
            assertEquals(setOf("ゴルフ"),p.tags)
            assertFalse(p.sample)
            assertTrue(p.description.isEmpty())
            assertTrue(visibleNow(p,2,today,now))
        }
        val pair=snapshot.programs.single { it.id=="official-bsasahi-20261102-2154-golfmatch" }
        val favorites=setOf("s:official-series-142a8e1007439f2e224e685c")
        assertTrue(browsePrograms(snapshot.programs,favorites,setOf("映画"),2,true,today,now).any { it.id==pair.id })
        assertEquals(snapshot.programs.size,snapshot.programs.map { it.id }.toSet().size)
        println("PHASE13_LIVE_OK rows=${snapshot.programs.size} newGolf=8 seriesFavoriteRetained=true")
    }
}
