package jp.victoryk.minogasanight
import org.junit.Assert.*
import org.junit.Test
import kotlinx.coroutines.runBlocking
import java.time.*
class Phase12LiveTest {
    @Test fun updatedSevenDayFeedAndCrossGenreFavoritesUseProductionClient() = runBlocking {
        org.junit.Assume.assumeTrue(System.getenv("MINOGASA_VERIFY_PHASE12")=="1")
        val today=LocalDate.now(Tokyo)
        val now=System.currentTimeMillis()
        val snapshot=HttpProgramSource(endpoint={BuildConfig.FEED_URL}).fetchFeed(today)
        val expected=mapOf(
            "verified-bs12-20261030-1900-royalwarriors" to "2026-10-30T19:00:00+09:00",
            "verified-bs12-20261102-1900-showazankyo4" to "2026-11-02T19:00:00+09:00",
            "verified-bs12-20261103-1900-truckyaro4" to "2026-11-03T19:00:00+09:00",
            "verified-bs12-20261104-1900-satomi1983" to "2026-11-04T19:00:00+09:00"
        )
        expected.forEach { (id,start) ->
            val p=snapshot.programs.single { it.id==id }
            assertEquals("BS12トゥエルビ",p.station)
            assertEquals(OffsetDateTime.parse(start).toInstant().toEpochMilli(),p.start)
            assertEquals(setOf("映画"),p.tags)
            assertFalse(p.sample)
            assertTrue(p.description.isEmpty())
            assertTrue(visibleNow(p,2,today,now))
        }
        assertTrue(snapshot.programs.any { "アニメ" in it.tags && Instant.ofEpochMilli(it.start).atZone(Tokyo).toLocalDate()==today.plusDays(6) })
        val hon=snapshot.programs.single { it.id=="official-f9558d382a201f8b6603526e" }
        val keys=setOf("p:${hon.id}")
        assertTrue(browsePrograms(snapshot.programs,keys,setOf("映画"),2,true,today,now).any { it.id==hon.id })
        assertTrue(browsePrograms(snapshot.programs,keys,emptySet(),2,true,today,now).any { it.id==hon.id })
        assertTrue(browsePrograms(snapshot.programs,emptySet(),setOf("映画"),2,false,today,now).none { it.id==hon.id })
        println("PHASE12_LIVE_OK rows=${snapshot.programs.size} newMovies=4 currentWindow=true favoritesIndependent=true")
    }
}
