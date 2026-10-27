package jp.victoryk.minogasanight
import org.junit.Assert.*
import org.junit.Test
import kotlinx.coroutines.runBlocking
import java.time.*
class Phase10LiveTest {
    @Test fun webDiscoveredSchedulesReachExistingAndroidDisplayFilters() = runBlocking {
        org.junit.Assume.assumeTrue(System.getenv("MINOGASA_VERIFY_LIVE")=="1")
        val today=LocalDate.now(Tokyo)
        val snapshot=HttpProgramSource(endpoint={BuildConfig.FEED_URL}).fetchFeed(today)
        val expected=mapOf(
            "verified-bs12-20261028-1900-jeans" to setOf("映画"),
            "verified-nhke-20261028-2200-backyard" to setOf("電車・鉄道"),
            "verified-nhkbs-20261029-1300-brothersanta" to setOf("映画"),
            "verified-nhkbs-20261030-1300-goodbadugly" to setOf("映画"),
            "official-ntv-20261030-2100-godzilla-minusone" to setOf("映画"),
            "official-bs12-20261031-1900-diehard3" to setOf("映画"),
            "official-bsntv-20261101-1900-godzilla1954" to setOf("映画"),
            "official-tvtokyo-20261031-1130-moyasama" to setOf("旅"),
            "official-bsntv-20261027-2100-mousoutrain" to setOf("旅","電車・鉄道"),
            "phase8-psycho-20261031" to setOf("映画","ホラー映画"),
            "verified-nhkbs-20261102-1300-fordferrari" to setOf("映画","車"),
            "verified-tvtokyo-20261102-1340-outbreak" to setOf("映画")
        )
        expected.forEach { (id,tags) ->
            val p=snapshot.programs.single { it.id==id }
            assertEquals(tags,p.tags)
            assertFalse(p.sample)
            assertTrue(p.description.isEmpty())
            assertTrue(visibleNow(p,2,today,System.currentTimeMillis()))
            val date=Instant.ofEpochMilli(p.start).atZone(Tokyo).toLocalDate()
            assertEquals(date==today,inPeriod(p,0,today))
            assertEquals(date==today.plusDays(1),inPeriod(p,1,today))
        }
        val psycho=snapshot.programs.single { it.id=="phase8-psycho-20261031" }
        assertEquals("NHK BSプレミアム4K",psycho.station)
        assertEquals("phase8-psycho-20261031-series",psycho.seriesId)
        assertEquals(OffsetDateTime.parse("2026-10-31T21:00:00+09:00").toInstant().toEpochMilli(),psycho.start)
        assertEquals("official-series-2b9729b602a554921245711f",snapshot.programs.single { it.id=="official-f9558d382a201f8b6603526e" }.seriesId)
        assertTrue(snapshot.programs.any { it.id=="official-15bd27175d27a7cbb8b71b6e" })
        assertTrue(snapshot.programs.any { it.id=="official-4a9c16fb7436ca6009605718" })
        println("PHASE10_LIVE_OK newSchedules=12 genresAndPeriods=true stableSavedIds=true")
    }
}
