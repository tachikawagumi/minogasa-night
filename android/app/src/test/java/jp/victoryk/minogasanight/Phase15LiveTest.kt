package jp.victoryk.minogasanight
import org.junit.Assert.*
import org.junit.Test
import kotlinx.coroutines.runBlocking
import java.time.*
class Phase15LiveTest {
    @Test fun hybridPublishedProgramsUseUnchangedAndroidClient() = runBlocking {
        org.junit.Assume.assumeTrue(System.getenv("MINOGASA_VERIFY_PHASE15")=="1")
        val today=LocalDate.now(Tokyo)
        val now=System.currentTimeMillis()
        val snapshot=HttpProgramSource(endpoint={BuildConfig.FEED_URL}).fetchFeed(today)
        val expected=mapOf(
            "official-bsasahi-20261102-2100-kyototabi" to "2026-11-02T21:00:00+09:00",
            "official-tvtokyo-20261031-1830-degawacharging" to "2026-10-31T18:30:00+09:00",
            "official-bstvtokyo-20261101-1430-airwalk-special" to "2026-11-01T14:30:00+09:00",
            "official-bstvtokyo-20261101-2230-gaia" to "2026-11-01T22:30:00+09:00",
            "official-bsntv-20261031-1700-yumetyoko" to "2026-10-31T17:00:00+09:00",
            "official-bsntv-20261031-1800-italy" to "2026-10-31T18:00:00+09:00",
            "official-tvtokyo-20261101-1830-private-rail-special" to "2026-11-01T18:30:00+09:00",
            "official-tvtokyo-20261103-1200-ai-sama-special" to "2026-11-03T12:00:00+09:00",
            "official-tbs-20261101-1800-heritage" to "2026-11-01T18:00:00+09:00",
            "official-chiba-20261104-2230-weekly-bike-tv" to "2026-11-04T22:30:00+09:00",
            "official-bsntv-20261031-2100-aisya-henreki" to "2026-10-31T21:00:00+09:00"
        )
        expected.forEach { (id,start) ->
            val p=snapshot.programs.single { it.id==id }
            assertEquals(OffsetDateTime.parse(start).toInstant().toEpochMilli(),p.start)
            assertFalse(p.sample)
            assertTrue(p.description.isEmpty())
            assertTrue(visibleNow(p,2,today,now))
        }
        val bike=snapshot.programs.single { it.id=="official-chiba-20261104-2230-weekly-bike-tv" }
        assertEquals("チバテレ",bike.station)
        assertEquals(setOf("車"),bike.tags)
        val charge=snapshot.programs.single { it.id=="official-tvtokyo-20261031-1830-degawacharging" }
        assertEquals(setOf("車","旅"),charge.tags)
        val old=snapshot.programs.single { it.id=="official-ce810c015779acc089ba403a" }
        assertTrue(browsePrograms(snapshot.programs,setOf("p:${old.id}"),setOf("車"),2,true,today,now).any { it.id==old.id })
        assertTrue(browsePrograms(snapshot.programs,setOf("s:${bike.seriesId}"),setOf("映画"),2,true,today,now).any { it.id==bike.id })
        assertEquals(snapshot.programs.size,snapshot.programs.map { it.id }.toSet().size)
        assertTrue(snapshot.programs.none { it.id.startsWith("held-bsntv142") })
        println("PHASE15_LIVE_OK rows=${snapshot.programs.size} newHybrid=11 carTravel=true favoritesRetained=true")
    }
}
