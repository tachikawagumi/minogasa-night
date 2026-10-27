package jp.victoryk.minogasanight

import org.junit.Assert.*
import org.junit.Test
import java.time.*
import kotlinx.coroutines.runBlocking

class ProgramTest {
    @Test fun multiGenreAndFeatureExtraction() {
        val text = "旅の途中で大間のマグロ漁師を取材。豪邸でホラー映画と怪談。SASUKEとブラタモリ"
        assertTrue(Classifier.classify(text).containsAll(setOf("旅", "釣り", "建物探訪", "映画", "ホラー映画", "心霊・怪談", "ゲーム・チャレンジ")))
        assertTrue(Classifier.features(text).containsAll(listOf("マグロ漁師", "大間", "豪邸", "SASUKE", "ブラタモリ")))
    }
    @Test fun trainsDoNotBecomeCarPrograms() {
        val tags = Classifier.classify("電車・鉄道で巡る列車旅")
        assertTrue("電車・鉄道" in tags)
        assertFalse("車" in tags)
        assertTrue("車" in Classifier.classify("自動車と電車の違い"))
    }
    @Test fun weekUsesTokyoCalendarAndExcludesEighthDay() = runBlocking {
        val date = LocalDate.of(2026, 10, 24)
        val list = SampleSource().fetch(date)
        assertEquals(20, list.count { inPeriod(it, 0, date) })
        assertEquals(20, list.count { inPeriod(it, 1, date) })
        assertEquals(140, list.count { inPeriod(it, 2, date) })
        val midnight = list.first().copy(start = Instant.parse("2026-10-24T15:00:00Z").toEpochMilli())
        assertFalse(inPeriod(midnight, 0, date))
        assertTrue(inPeriod(midnight, 1, date))
        assertFalse(inPeriod(midnight.copy(start = date.plusDays(7).atStartOfDay(Tokyo).toInstant().toEpochMilli()), 2, date))
        assertTrue(list.all { it.sample && !it.rerunConfirmed && it.title.contains("サンプル") })
        assertEquals(20, list.map { it.seriesId }.toSet().size)
    }
    @Test fun duplicatesMergeTagsButKeepStationsSeparate() = runBlocking {
        val p = SampleSource().fetch(LocalDate.of(2026, 10, 24)).first()
        val merged = normalized(listOf(p.copy(tags = setOf("旅")), p.copy(id = "duplicate", tags = setOf("釣り")), p.copy(station = "別局")))
        assertEquals(2, merged.size)
        assertEquals(setOf("旅", "釣り"), merged.first().tags)
    }
    @Test fun sundayAtNineIsAlwaysInFutureInTokyo() {
        val sun = ZonedDateTime.of(2026, 10, 25, 9, 0, 0, 0, Tokyo)
        assertEquals(sun, nextSunday(sun.minusMinutes(1)))
        assertEquals(sun.plusWeeks(1), nextSunday(sun))
        assertEquals(sun, nextSunday(sun.minusDays(2).withZoneSameInstant(ZoneId.of("UTC"))))
    }
}
