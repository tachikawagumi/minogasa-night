package jp.victoryk.minogasanight
import org.junit.Assert.*
import org.junit.Test
import kotlinx.coroutines.runBlocking
import java.time.*

class Phase9LiveTest {
    @Test fun investigatedSchedulesReachExistingAndroidDisplayFilters() = runBlocking {
        org.junit.Assume.assumeTrue(System.getenv("MINOGASA_VERIFY_LIVE")=="1")
        val today=LocalDate.now(Tokyo)
        val snapshot=HttpProgramSource(endpoint={BuildConfig.FEED_URL}).fetchFeed(today)
        val expected=mapOf(
            "phase7-darkside-immortality-20261029" to setOf("UFO・都市伝説"),
            "phase7-darkside-hell-20261030" to setOf("心霊・怪談"),
            "official-ce810c015779acc089ba403a" to setOf("健康"),
            "official-tbs-20261101-1430-kurumi" to setOf("ダンス"),
            "official-tbs-20261102-0113-kickoffj" to setOf("サッカー"),
            "verified-nhkbs-20261031-0630-matsuura" to setOf("旅","電車・鉄道"),
            "verified-nhkbs-20261031-0730-naruko" to setOf("旅","温泉"),
            "official-tbs-20261028-1025-hiruobi" to setOf("旅","サッカー"),
            "verified-nhkbs-20261028-1300-1917" to setOf("映画")
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
        val immortal=snapshot.programs.single { it.id=="phase7-darkside-immortality-20261029" }
        val hell=snapshot.programs.single { it.id=="phase7-darkside-hell-20261030" }
        assertEquals("NHK BS",immortal.station)
        assertEquals(OffsetDateTime.parse("2026-10-29T00:45:00+09:00").toInstant().toEpochMilli(),immortal.start)
        assertEquals(OffsetDateTime.parse("2026-10-30T09:00:00+09:00").toInstant().toEpochMilli(),hell.start)
        assertEquals("official-series-darkside",immortal.seriesId)
        assertEquals(immortal.seriesId,hell.seriesId)
        val p=snapshot.programs.single { it.id=="official-tbs-20261102-0113-kickoffj" }
        assertEquals(OffsetDateTime.parse("2026-11-02T01:13:00+09:00").toInstant().toEpochMilli(),p.start)
        val hon=snapshot.programs.single { it.id=="official-f9558d382a201f8b6603526e" }
        assertEquals("official-series-2b9729b602a554921245711f",hon.seriesId)
        println("PHASE9_LIVE_OK newSchedules=9 darkside=2 civilDates=true genresAndPeriods=true stableSavedIds=true")
    }
}
