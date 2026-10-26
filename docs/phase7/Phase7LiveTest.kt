package jp.victoryk.minogasanight

import org.junit.Assert.*
import org.junit.Test
import kotlinx.coroutines.runBlocking
import java.time.*

class Phase7LiveTest {
    @Test fun liveDiscoveryUsesExistingFiltersAndStableSavedKeys() = runBlocking {
        org.junit.Assume.assumeTrue(System.getenv("MINOGASA_VERIFY_LIVE") == "1")
        val today=LocalDate.now(Tokyo)
        val snapshot=HttpProgramSource(endpoint={BuildConfig.FEED_URL}).fetchFeed(today)
        val p=snapshot.programs.single { it.id=="official-fuji-20261028-1900-nandakore" }
        assertEquals("世界の何だコレ!?ミステリー",p.title)
        assertEquals("フジテレビ",p.station)
        assertEquals(OffsetDateTime.parse("2026-10-28T19:00:00+09:00").toInstant().toEpochMilli(),p.start)
        assertEquals(p.start,p.end) // Existing decoder represents an unknown end by start.
        assertEquals(setOf("UFO・都市伝説"),p.tags)
        assertTrue(visibleNow(p,2,today,System.currentTimeMillis()))
        val day=Instant.ofEpochMilli(p.start).atZone(Tokyo).toLocalDate()
        assertEquals(day==today,inPeriod(p,0,today))
        assertEquals(day==today.plusDays(1),inPeriod(p,1,today))
        assertTrue(p.tags.any { it in setOf("UFO・都市伝説") })
        assertFalse(p.tags.any { it in setOf("心霊・怪談") })
        val hon=snapshot.programs.single { it.id=="official-f9558d382a201f8b6603526e" }
        assertEquals("official-series-2b9729b602a554921245711f",hon.seriesId)
        val saved=setOf("p:"+hon.id,"s:"+hon.seriesId)
        assertTrue("p:"+hon.id in saved && "s:"+hon.seriesId in saved)
        assertFalse(snapshot.programs.any { it.id.startsWith("phase7-darkside") || it.id.startsWith("phase7-oichi") || it.id=="official-bs12-20261101-1900-genma" })
        assertTrue(snapshot.programs.all { !it.sample && it.description.isEmpty() })
        println("PHASE7_LIVE_OK NANDAKORE=2026-10-28T19:00+09:00 genre=UFO・都市伝説 unknownEnd=true weekVisible=true honkowaDuplicate=false heldCandidatesAbsent=true")
    }
}
