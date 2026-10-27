package jp.victoryk.minogasanight

import org.junit.Assert.*
import org.junit.Test
import kotlinx.coroutines.runBlocking
import java.time.*

class Phase6LiveTest {
    @Test fun liveHonkowaUsesOfficialSlotAndExistingFilters() = runBlocking {
        org.junit.Assume.assumeTrue(System.getenv("MINOGASA_VERIFY_LIVE") == "1")
        val today = LocalDate.now(Tokyo)
        val snapshot = HttpProgramSource(endpoint = { BuildConfig.FEED_URL }).fetchFeed(today)
        val p = snapshot.programs.single { it.id == "official-f9558d382a201f8b6603526e" }
        assertEquals("ほんとにあった怖い話 秋の特別編2026", p.title)
        assertEquals("フジテレビ", p.station)
        assertEquals(OffsetDateTime.parse("2026-10-31T21:00:00+09:00").toInstant().toEpochMilli(), p.start)
        assertEquals(OffsetDateTime.parse("2026-10-31T23:10:00+09:00").toInstant().toEpochMilli(), p.end)
        assertEquals(setOf("心霊・怪談"), p.tags)
        assertFalse(p.sample)
        assertEquals("",p.description)
        assertTrue(visibleNow(p, 2, today, System.currentTimeMillis()))
        val date=Instant.ofEpochMilli(p.start).atZone(Tokyo).toLocalDate()
        assertEquals(date==today, inPeriod(p,0,today))
        assertEquals(date==today.plusDays(1), inPeriod(p,1,today))
        assertTrue(p.tags.any { it in setOf("心霊・怪談") })
        assertFalse(p.tags.any { it in setOf("アニメ") })
        println("HONKOWA_LIVE_OK id="+p.id+" station="+p.station+" start=2026-10-31T21:00+09:00 end=23:10 genre=心霊・怪談 weekVisible=true")
    }
}

