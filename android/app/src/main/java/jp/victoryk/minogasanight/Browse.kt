package jp.victoryk.minogasanight

import java.time.LocalDate

/** Keeps the existing p:/s: keys and their Room storage unchanged. */
fun isFavorite(program: Listing, keys: Set<String>): Boolean =
    "p:${program.id}" in keys || "s:${program.seriesId}" in keys

/**
 * The selected period always applies. Genre switches only apply to ordinary browsing.
 * Filtering before normalization also preserves favorites saved under an alias ID.
 */
fun browsePrograms(programs: List<Listing>, keys: Set<String>, enabledGenres: Set<String>,
                   period: Int, favoritesOnly: Boolean, today: LocalDate, now: Long): List<Listing> =
    normalized(programs.filter { p ->
        visibleNow(p, period, today, now) &&
            if (favoritesOnly) isFavorite(p, keys) else p.tags.any { it in enabledGenres }
    }.distinctBy { it.id })

/**
 * Reviewed existing collection IDs, not a guessed new series or a change to the feed.
 * Godzilla has two different works under one existing ID. Die Hard is already a
 * franchise collection in the current feed. Film-specific IDs remain single-work.
 */
private val filmCollections = setOf("official-series-godzilla-films", "official-series-diehard-films")

fun seriesFavoriteAvailable(p: Listing): Boolean {
    if (p.seriesId.isBlank() || p.seriesId == p.id || p.seriesId == "${p.id}-series") return false
    if (p.seriesId in filmCollections) return true
    return p.tags.none { it == "映画" || it == "ホラー映画" }
}

object BrowseText {
    fun episode(saved: Boolean) = if (saved) "★ この回" else "☆ この回"
    fun series(saved: Boolean) = if (saved) "★ 毎回チェック" else "☆ 毎回チェック"
    fun empty(favoritesOnly: Boolean, hasSaved: Boolean, genresEnabled: Boolean): String = when {
        favoritesOnly && hasSaved -> "お気に入り登録済みですが、期間内の放送予定はありません"
        favoritesOnly -> "お気に入りはまだありません。☆で登録できます"
        !genresEnabled -> "ジャンルがすべてOFFです。設定から選んでください"
        else -> "この期間の放送予定はありません"
    }
    const val creditsTitle = "情報提供元"
    const val credits = "アニメ放送情報：しょぼいカレンダー\nその他の放送予定：各放送局の公開情報・テレビ番組情報サイト\n放送予定は変更される場合があります。"
}

