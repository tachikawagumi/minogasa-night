package jp.victoryk.minogasanight

import android.content.Context
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import androidx.room.*
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.time.LocalDate

val Context.preferences by preferencesDataStore("night_settings")

@Entity(tableName = "programs")
data class ProgramRow(@PrimaryKey val id: String, val seriesId: String, val title: String, val description: String, val station: String, val start: Long, val end: Long, val tags: String, val sample: Boolean, val rerunConfirmed: Boolean) {
    fun listing() = Listing(id, seriesId, title, description, station, start, end, tags.split("|").filter { it.isNotEmpty() }.toSet(), sample, rerunConfirmed)
}
fun Listing.row() = ProgramRow(id, seriesId, title, description, station, start, end, tags.joinToString("|"), sample, rerunConfirmed)
@Entity(tableName = "favorites")
data class Favorite(@PrimaryKey val key: String)
@Entity(tableName = "sync_state")
data class SyncState(@PrimaryKey val id: Int = 1, val updated: Long, @ColumnInfo(defaultValue = "''") val notice: String = "", @ColumnInfo(defaultValue = "0") val windowEnd: Long = 0)

@Dao
interface NightDao {
    @Query("SELECT * FROM programs ORDER BY start") fun observe(): Flow<List<ProgramRow>>
    @Query("SELECT * FROM programs ORDER BY start") suspend fun all(): List<ProgramRow>
    @Query("SELECT * FROM favorites") fun favorites(): Flow<List<Favorite>>
    @Query("SELECT * FROM favorites") suspend fun saved(): List<Favorite>
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun save(favorite: Favorite)
    @Query("DELETE FROM favorites WHERE `key` = :key") suspend fun unsave(key: String)
    @Query("DELETE FROM programs") suspend fun clear()
    @Query("DELETE FROM programs WHERE sample = 1") suspend fun clearSamples()
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun insert(rows: List<ProgramRow>)
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun stamp(state: SyncState)
    @Query("SELECT updated FROM sync_state WHERE id = 1") fun updated(): Flow<Long?>
    @Query("SELECT * FROM sync_state WHERE id = 1") fun sync(): Flow<SyncState?>
    @Transaction suspend fun replace(rows: List<ProgramRow>, timestamp: Long, notice: String = "", windowEnd: Long = 0) { clear(); insert(rows); stamp(SyncState(updated = timestamp, notice = notice, windowEnd = windowEnd)) }
}
@Database(entities = [ProgramRow::class, Favorite::class, SyncState::class], version = 2, exportSchema = false)
abstract class NightDatabase : RoomDatabase() { abstract fun dao(): NightDao }

data class Settings(val enabled: Set<String> = genres.toSet(), val weekly: Boolean = false, val reminders: Boolean = false, val draft: String = "")
class SettingsStore(private val context: Context) {
    private val enabled = stringSetPreferencesKey("enabled_genres")
    private val weekly = booleanPreferencesKey("weekly")
    private val reminders = booleanPreferencesKey("reminders")
    private val draft = stringPreferencesKey("request_draft")
    val flow = context.preferences.data.map { Settings(it[enabled] ?: genres.toSet(), it[weekly] ?: false, it[reminders] ?: false, it[draft] ?: "") }
    suspend fun genre(name: String, on: Boolean) = context.preferences.edit { val old = it[enabled] ?: genres.toSet(); it[enabled] = if (on) old + name else old - name }
    suspend fun weekly(on: Boolean) = context.preferences.edit { it[weekly] = on }
    suspend fun reminders(on: Boolean) = context.preferences.edit { it[reminders] = on }
    suspend fun draft(value: String) = context.preferences.edit { it[draft] = value }
}

class Repository(val dao: NightDao, private val source: ProgramSource) {
    private val lock = Mutex()
    suspend fun prepare(context: Context) = prepare { bundledFeed(context) }
    suspend fun prepare(seed: suspend () -> FeedSnapshot) = lock.withLock {
        dao.clearSamples()
        if (dao.sync().first() == null) {
            val feed = seed()
            dao.replace(feed.programs.map { it.row() }, feed.generatedAt, feed.notice, feed.windowEnd)
        }
    }
    suspend fun refresh() = lock.withLock {
        val feed = source.fetchFeed(LocalDate.now(Tokyo))
        require(feed.programs.none { it.sample })
        dao.replace(normalized(feed.programs).map { it.row() }, feed.generatedAt, feed.notice, feed.windowEnd)
    }
    suspend fun toggle(key: String) = lock.withLock { if (dao.saved().any { it.key == key }) dao.unsave(key) else dao.save(Favorite(key)) }
}
