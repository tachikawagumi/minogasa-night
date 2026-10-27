package jp.victoryk.minogasanight

import android.Manifest
import android.app.*
import android.content.*
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.room.Room
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.work.*
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.time.*
import java.util.concurrent.TimeUnit

class NightApp : Application() {
    val db by lazy { Room.databaseBuilder(this, NightDatabase::class.java, "night.db").addMigrations(object : Migration(1, 2) {
        override fun migrate(db: SupportSQLiteDatabase) {
            db.execSQL("ALTER TABLE sync_state ADD COLUMN notice TEXT NOT NULL DEFAULT ''")
            db.execSQL("ALTER TABLE sync_state ADD COLUMN windowEnd INTEGER NOT NULL DEFAULT 0")
            db.execSQL("DELETE FROM programs WHERE sample = 1")
            db.execSQL("DELETE FROM sync_state")
        }
    }).build() }
    val settings by lazy { SettingsStore(this) }
    val repository by lazy { Repository(db.dao(), HttpProgramSource(endpoint = { BuildConfig.FEED_URL })) }
    override fun onCreate() {
        super.onCreate()
        getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel("programs", "番組と週間おすすめ", NotificationManager.IMPORTANCE_DEFAULT))
        WorkManager.getInstance(this).enqueueUniquePeriodicWork("refresh", ExistingPeriodicWorkPolicy.KEEP, PeriodicWorkRequestBuilder<RefreshWorker>(6, TimeUnit.HOURS).build())
    }
}
val Context.night: NightApp get() = applicationContext as NightApp
fun canNotify(context: Context): Boolean = (Build.VERSION.SDK_INT < 33 || ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) && NotificationManagerCompat.from(context).areNotificationsEnabled()

fun nextSunday(now: ZonedDateTime): ZonedDateTime {
    var target = now.withZoneSameInstant(Tokyo).toLocalDate().atTime(9, 0).atZone(Tokyo)
    while (target.dayOfWeek != DayOfWeek.SUNDAY || !target.isAfter(now)) target = target.plusDays(1)
    return target
}

object Schedules {
    private val lock = Mutex()
    fun weekly(context: Context, enabled: Boolean, append: Boolean = false) {
        val wm = WorkManager.getInstance(context)
        if (!enabled) { wm.cancelUniqueWork("weekly"); return }
        val delay = Duration.between(ZonedDateTime.now(Tokyo), nextSunday(ZonedDateTime.now(Tokyo))).toMillis()
        wm.enqueueUniqueWork("weekly", if (append) ExistingWorkPolicy.APPEND_OR_REPLACE else ExistingWorkPolicy.REPLACE, OneTimeWorkRequestBuilder<WeeklyWorker>().setInitialDelay(delay, TimeUnit.MILLISECONDS).build())
    }
    suspend fun reminders(context: Context) = lock.withLock {
        val app = context.night
        val wm = WorkManager.getInstance(context)
        // Reschedule the small local window after each data or favorite change.
        wm.cancelAllWorkByTag("reminder")
        if (!app.settings.flow.first().reminders) return@withLock
        val keys = app.db.dao().saved().map { it.key }.toSet()
        app.db.dao().all().map { it.listing() }.filter { "p:${it.id}" in keys || "s:${it.seriesId}" in keys }.forEach { p ->
            val now = System.currentTimeMillis()
            val delay = (p.start - 10 * 60_000 - now).coerceAtLeast(0)
            if (p.start > now) wm.enqueueUniqueWork("reminder-${p.id}", ExistingWorkPolicy.REPLACE,
                OneTimeWorkRequestBuilder<ReminderWorker>().addTag("reminder").setInputData(workDataOf("id" to p.id)).setInitialDelay(delay, TimeUnit.MILLISECONDS).build())
        }
    }
}

private fun notify(context: Context, id: Int, title: String, body: String): Boolean {
    if (!canNotify(context)) return false
    val intent = PendingIntent.getActivity(context, 0, Intent(context, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    val notification = NotificationCompat.Builder(context, "programs").setSmallIcon(R.drawable.ic_notification).setContentTitle(title).setContentText(body).setStyle(NotificationCompat.BigTextStyle().bigText(body)).setContentIntent(intent).setAutoCancel(true).build()
    return try { NotificationManagerCompat.from(context).notify(id, notification); true } catch (_: SecurityException) { false }
}
class RefreshWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = try { applicationContext.night.repository.refresh(); Schedules.reminders(applicationContext); Result.success() } catch (_: Exception) { Result.retry() }
}
class ReminderWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val app = applicationContext.night
        if (!app.settings.flow.first().reminders) return Result.success()
        val p = app.db.dao().all().find { it.id == inputData.getString("id") }?.listing() ?: return Result.success()
        val keys = app.db.dao().saved().map { it.key }
        if (p.start <= System.currentTimeMillis() || ("p:${p.id}" !in keys && "s:${p.seriesId}" !in keys)) return Result.success()
        val deliveredKey = stringSetPreferencesKey("delivered_reminders")
        val delivered = applicationContext.preferences.data.first()[deliveredKey] ?: emptySet()
        if (p.id in delivered) return Result.success()
        if (notify(applicationContext, p.id.hashCode(), if (p.sample) "サンプル通知・放送予定ではありません" else "まもなく放送", "${p.title} ／ ${p.station}")) {
            applicationContext.preferences.edit { it[deliveredKey] = (delivered.toList().takeLast(999) + p.id).toSet() }
        }
        return Result.success()
    }
}
class WeeklyWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val app = applicationContext.night
        val settings = app.settings.flow.first()
        if (!settings.weekly) return Result.success()
        try { app.repository.refresh() } catch (_: Exception) { /* Cache is still usable. */ }
        val now = System.currentTimeMillis()
        val candidates = app.db.dao().all().filter { it.start > now && it.start < now + 7 * 86_400_000L && it.listing().tags.any { tag -> tag in settings.enabled } }
        if (candidates.isNotEmpty()) notify(applicationContext, 700, "今週のおすすめ", "選択したジャンルで ${candidates.size} 件の放送予定が見つかりました。")
        Schedules.weekly(applicationContext, true, append = true)
        return Result.success()
    }
}
