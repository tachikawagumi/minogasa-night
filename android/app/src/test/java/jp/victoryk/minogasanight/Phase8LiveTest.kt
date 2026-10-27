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
        assertFalse(snapshot.programs.any { it.id.startsWith("phase7-oichi") || it.id.startsWith("phase8-paid") })
        println("PHASE8_LIVE_OK reviewed_nonanime=true genmaUnknownEnd=true dateAndGenreFilters=true stableFavoriteIdentity=true")
    }
}
