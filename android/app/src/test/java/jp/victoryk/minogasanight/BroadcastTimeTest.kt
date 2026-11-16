package jp.victoryk.minogasanight

import java.time.Instant
import org.junit.Assert.assertEquals
import org.junit.Test

class BroadcastTimeTest {
    private fun time(value: String) = Instant.parse(value).toEpochMilli()

    @Test fun formatsJapaneseDateAndTimeFromUtc() {
        assertEquals("11/16（月）19:00〜21:00", BrowseText.broadcastTime(
            time("2026-11-16T10:00:00Z"), time("2026-11-16T12:00:00Z")
        ))
    }

    @Test fun showsOnlyTheStartWhenEndIsUnknownOrEarlier() {
        val start = time("2026-11-16T10:00:00Z")
        assertEquals("11/16（月）19:00〜", BrowseText.broadcastTime(start, start))
        assertEquals("11/16（月）19:00〜", BrowseText.broadcastTime(start, start - 60_000))
    }

    @Test fun usesTheJapaneseDateAcrossMonthAndYearBoundaries() {
        assertEquals("11/30（月）23:30〜00:15", BrowseText.broadcastTime(
            time("2026-11-30T14:30:00Z"), time("2026-11-30T15:15:00Z")
        ))
        assertEquals("12/1（火）00:15〜", BrowseText.broadcastTime(
            time("2026-11-30T15:15:00Z"), time("2026-11-30T15:15:00Z")
        ))
        assertEquals("1/1（金）00:15〜01:00", BrowseText.broadcastTime(
            time("2026-12-31T15:15:00Z"), time("2026-12-31T16:00:00Z")
        ))
    }
}
