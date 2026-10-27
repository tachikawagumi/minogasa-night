package jp.victoryk.minogasanight

import org.junit.Assert.*
import org.junit.Test
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.flow.*
import java.time.LocalDate

class FavoritesTest {
    private val today = LocalDate.of(2026, 10, 27)
    private val now = today.atTime(8, 0).atZone(Tokyo).toInstant().toEpochMilli()
    private fun listing(id: String = "episode", series: String = "show", day: Long = 0,
                        tags: Set<String> = setOf("心霊・怪談")) =
        Listing(id, series, "番組$id", "", "テスト局", today.plusDays(day).atTime(21,0).atZone(Tokyo).toInstant().toEpochMilli(),
            today.plusDays(day).atTime(22,0).atZone(Tokyo).toInstant().toEpochMilli(), tags, sample=false)
    private fun shown(list: List<Listing>, keys: Set<String>, enabled: Set<String> = setOf("映画"), period: Int = 2, saved: Boolean = true) =
        browsePrograms(list, keys, enabled, period, saved, today, now)
    private fun source(rows: List<Listing>) = object : ProgramSource {
        override suspend fun fetch(today: LocalDate) = rows
    }

    @Test fun thisEpisodeCanBeSavedAndRemoved() = runBlocking {
        val dao = SavedDao()
        val repo = Repository(dao, source(emptyList()))
        repo.toggle("p:episode")
        assertEquals(setOf("p:episode"), dao.keys())
        repo.toggle("p:episode")
        assertTrue(dao.keys().isEmpty())
    }
    @Test fun everyEpisodeCanBeSavedAndRemovedWithoutConvertingKeys() = runBlocking {
        val dao = SavedDao()
        val repo = Repository(dao, source(emptyList()))
        repo.toggle("s:show")
        assertEquals(setOf("s:show"), dao.keys())
        assertTrue(isFavorite(listing(), dao.keys()))
        repo.toggle("s:show")
        assertFalse(isFavorite(listing(), dao.keys()))
    }
    @Test fun favoriteIgnoresDifferentAndEvenDisabledGenres() {
        val p = listing()
        assertTrue(shown(listOf(p), emptySet(), saved=false).isEmpty())
        assertEquals(listOf(p), shown(listOf(p), setOf("p:episode")))
        assertEquals(listOf(p), shown(listOf(p), setOf("p:episode"), emptySet()))
    }
    @Test fun favoritesMergeGenresAreSortedAndDoNotRepeatAnEpisode() {
        val ghost = listing(day=1)
        val movie = listing("film","single-film",tags=setOf("映画"))
        val alias = ghost.copy(id="alias",tags=setOf("旅"))
        val result = shown(listOf(ghost, movie, alias, ghost), setOf("p:episode","p:film","p:alias"))
        assertEquals(2,result.size)
        assertEquals(listOf("film","episode"),result.map { it.id })
        assertEquals(setOf("心霊・怪談","旅"),result.last().tags)
    }
    @Test fun favoriteAliasDoesNotDisappearDuringNormalization() {
        val p=listing()
        assertEquals(1,shown(listOf(p,p.copy(id="alias")),setOf("p:alias")).size)
    }
    @Test fun uncheckingFavoritesImmediatelyChangesTheList() = runBlocking {
        val dao=SavedDao()
        val repo=Repository(dao,source(emptyList()))
        repo.toggle("p:episode")
        assertEquals(1,shown(listOf(listing()),dao.keys()).size)
        repo.toggle("p:episode")
        assertTrue(shown(listOf(listing()),dao.keys()).isEmpty())
    }
    @Test fun newBroadcastMatchesSavedSeriesAfterJsonRefresh() = runBlocking {
        val dao=SavedDao()
        val first=listing()
        Repository(dao,source(listOf(first))).refresh()
        dao.save(Favorite("s:show"))
        val next=listing("next","show",day=1)
        Repository(dao,source(listOf(next))).refresh()
        val rows=dao.all().map { it.listing() }
        assertEquals(listOf("next"),shown(rows,dao.keys()).map { it.id })
        assertEquals(setOf("s:show"),dao.keys())
    }
    @Test fun repositoryRecreationAndPrepareDoNotDeleteStoredFavorites() = runBlocking {
        // Same persisted DAO across Repository instances; actual Room reopen needs a device.
        val dao=SavedDao()
        dao.save(Favorite("p:episode"))
        dao.save(Favorite("s:show"))
        val restarted=Repository(dao,source(listOf(listing())))
        restarted.prepare { FeedSnapshot(listOf(listing()),now,"",now+7*86_400_000L) }
        restarted.refresh()
        assertEquals(setOf("p:episode","s:show"),dao.keys())
        assertEquals(1,shown(dao.all().map { it.listing() },dao.keys()).size)
    }
    @Test fun failedRefreshKeepsBothCacheAndFavorites() = runBlocking {
        val dao=SavedDao()
        Repository(dao,source(listOf(listing()))).refresh()
        dao.save(Favorite("s:show"))
        val fail=object:ProgramSource { override suspend fun fetch(today:LocalDate):List<Listing> = throw java.io.IOException("offline") }
        try { Repository(dao,fail).refresh(); fail("expected failure") } catch (_:java.io.IOException) {}
        assertEquals(1,dao.all().size)
        assertEquals(setOf("s:show"),dao.keys())
    }
    @Test fun favoritesRespectTodayTomorrowAndSevenCalendarDays() {
        val a=listing(); val b=listing("tomorrow",day=1); val outside=listing("eighth",day=7)
        val rows=listOf(a,b,outside)
        assertEquals(listOf(a),shown(rows,setOf("s:show"),period=0))
        assertEquals(listOf(b),shown(rows,setOf("s:show"),period=1))
        assertEquals(listOf(a,b),shown(rows,setOf("s:show"),period=2))
        assertTrue(shown(listOf(a.copy(start=now-1)),setOf("s:show")).isEmpty())
        assertTrue(shown(listOf(a.copy(sample=true)),setOf("s:show")).isEmpty())
    }
    @Test fun emptyPeriodDoesNotClaimSavedKeysWereDeleted() {
        assertTrue(BrowseText.empty(true,true,false).contains("お気に入り登録済み"))
        assertTrue(BrowseText.empty(true,true,true).contains("期間内"))
        assertTrue(BrowseText.empty(true,false,true).contains("まだありません"))
        assertTrue(BrowseText.empty(false,false,false).contains("OFF"))
    }
    @Test fun filmSpecificIdsAreSingleButExistingCollectionsRemainAvailable() {
        assertFalse(seriesFavoriteAvailable(listing("phase8-psycho-20261031","phase8-psycho-20261031-series",tags=setOf("映画","ホラー映画"))))
        assertFalse(seriesFavoriteAvailable(listing("ford","verified-series-fordvferrari",tags=setOf("映画","車"))))
        assertFalse(seriesFavoriteAvailable(listing("genma","genma-series",tags=setOf("映画","アニメ"))))
        assertTrue(seriesFavoriteAvailable(listing("godzilla","official-series-godzilla-films",tags=setOf("映画"))))
        assertTrue(seriesFavoriteAvailable(listing("diehard","official-series-diehard-films",tags=setOf("映画"))))
        assertTrue(seriesFavoriteAvailable(listing("hon","official-series-2b9729b602a554921245711f")))
        assertTrue(seriesFavoriteAvailable(listing("anime","syobocal-title-8046",tags=setOf("アニメ"))))
    }
    @Test fun perBroadcastAndBlankSeriesDoNotOfferEveryEpisode() {
        assertFalse(seriesFavoriteAvailable(listing("x","x-series")))
        assertFalse(seriesFavoriteAvailable(listing("x","x")))
        assertFalse(seriesFavoriteAvailable(listing("x","")))
    }
    @Test fun legacySingleFilmSeriesFavoriteStaysVisibleAndCanBeRemoved() = runBlocking {
        val p=listing("film","specific-film",tags=setOf("映画"))
        val dao=SavedDao(); dao.save(Favorite("s:specific-film"))
        assertFalse(seriesFavoriteAvailable(p))
        assertEquals(listOf(p),shown(listOf(p),dao.keys()))
        Repository(dao,source(emptyList())).toggle("s:specific-film")
        assertTrue(shown(listOf(p),dao.keys()).isEmpty())
    }
    @Test fun buttonLabelsAndCreditRemainAvailableWithoutSourceOnCards() {
        assertEquals("☆ この回",BrowseText.episode(false))
        assertEquals("★ この回",BrowseText.episode(true))
        assertEquals("☆ 毎回チェック",BrowseText.series(false))
        assertEquals("★ 毎回チェック",BrowseText.series(true))
        assertTrue(BrowseText.credits.contains("しょぼいカレンダー"))
    }
}

private class SavedDao : NightDao {
    private val rows=MutableStateFlow<List<ProgramRow>>(emptyList())
    private val saved=MutableStateFlow<List<Favorite>>(emptyList())
    private val state=MutableStateFlow<SyncState?>(null)
    suspend fun keys()=saved().map { it.key }.toSet()
    override fun observe():Flow<List<ProgramRow>> = rows
    override suspend fun all()=rows.value
    override fun favorites():Flow<List<Favorite>> = saved
    override suspend fun saved()=saved.value
    override suspend fun save(favorite:Favorite) { saved.value=saved.value.filterNot { it.key==favorite.key }+favorite }
    override suspend fun unsave(key:String) { saved.value=saved.value.filterNot { it.key==key } }
    override suspend fun clear() { rows.value=emptyList() }
    override suspend fun clearSamples() { rows.value=rows.value.filterNot { it.sample } }
    override suspend fun insert(rows:List<ProgramRow>) { this.rows.value=rows }
    override suspend fun stamp(state:SyncState) { this.state.value=state }
    override fun updated():Flow<Long?> = state.map { it?.updated }
    override fun sync():Flow<SyncState?> = state
}

