package jp.victoryk.minogasanight

import android.Manifest
import android.app.Application
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.platform.LocalContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.time.*
import java.time.format.DateTimeFormatter

private val Navy = Color(0xFF0B1124)
private val Panel = Color(0xFF18213A)
private val Purple = Color(0xFFC4AAFF)
private val Gold = Color(0xFFE8C66A)
private val Muted = Color(0xFFBDC4D8)
private val timeFormat = DateTimeFormatter.ofPattern("HH:mm")
private val dateFormat = DateTimeFormatter.ofPattern("M月d日（E）", java.util.Locale.JAPAN)
private fun time(ms: Long) = Instant.ofEpochMilli(ms).atZone(Tokyo).format(timeFormat)

class NightViewModel(application: Application) : AndroidViewModel(application) {
    private val app = application as NightApp
    val programs = app.db.dao().observe().map { it.map(ProgramRow::listing) }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val favorites = app.db.dao().favorites().map { it.map(Favorite::key).toSet() }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptySet())
    val settings = app.settings.flow.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), Settings())
    val updated = app.db.dao().updated().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)
    val sync = app.db.dao().sync().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)
    var busy by mutableStateOf(false); private set
    var error by mutableStateOf<String?>(null); private set
    init { refresh() }
    fun refresh() { if (busy) return; viewModelScope.launch {
        busy = true; error = null
        try {
            app.repository.prepare(app)
            Schedules.reminders(app)
            app.repository.refresh()
            Schedules.reminders(app)
        } catch (_: Exception) { error = if (BuildConfig.FEED_URL.isBlank()) "配信先の接続準備中です。同梱した実番組の確認情報を表示しています。" else "更新できませんでした。保存済みの情報を表示しています。" } finally { busy = false }
    } }
    fun favorite(key: String) = viewModelScope.launch { app.repository.toggle(key); Schedules.reminders(app) }
    fun genre(name: String, on: Boolean) = viewModelScope.launch { app.settings.genre(name, on) }
    fun weekly(on: Boolean) = viewModelScope.launch { app.settings.weekly(on); Schedules.weekly(app, on) }
    fun reminders(on: Boolean) = viewModelScope.launch { app.settings.reminders(on); Schedules.reminders(app) }
    fun draft(value: String) = viewModelScope.launch { app.settings.draft(value) }
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme(primary = Purple, secondary = Gold, background = Navy, surface = Panel, onSurface = Color(0xFFF4F3FA)), typography = Typography(bodyLarge = androidx.compose.ui.text.TextStyle(fontSize = 18.sp, lineHeight = 27.sp))) {
                Surface(color = Navy, modifier = Modifier.fillMaxSize()) { NightScreen() }
            }
        }
    }
}

@Composable
fun NightScreen(vm: NightViewModel = viewModel()) {
    val programs by vm.programs.collectAsStateWithLifecycle()
    val favorites by vm.favorites.collectAsStateWithLifecycle()
    val settings by vm.settings.collectAsStateWithLifecycle()
    val updated by vm.updated.collectAsStateWithLifecycle()
    val sync by vm.sync.collectAsStateWithLifecycle()
    var period by remember { mutableIntStateOf(0) }
    var onlySaved by rememberSaveable { mutableStateOf(false) }
    var screen by rememberSaveable { mutableStateOf("home") }
    BackHandler(enabled = screen != "home") { screen = if (screen == "request") "settings" else "home" }
    var today by remember { mutableStateOf(LocalDate.now(Tokyo)) }
    var currentTime by remember { mutableLongStateOf(System.currentTimeMillis()) }
    LaunchedEffect(Unit) { while (true) {
        currentTime = System.currentTimeMillis()
        val date = LocalDate.now(Tokyo)
        if (date != today) { today = date; vm.refresh() }
        delay(30_000)
    } }
    val context = LocalContext.current
    var permissionMessage by remember { mutableStateOf<String?>(null) }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        permissionMessage = if (granted) "通知を許可しました。" else "通知は許可されていません。番組の閲覧・保存はそのまま利用できます。"
    }
    fun requestPermission() { if (Build.VERSION.SDK_INT >= 33 && !canNotify(context)) permission.launch(Manifest.permission.POST_NOTIFICATIONS) }

    Column(Modifier.fillMaxSize().safeDrawingPadding().padding(horizontal = 20.dp)) {
        Row(Modifier.fillMaxWidth().padding(top = 16.dp, bottom = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("VICTORY K", color = Gold, fontSize = 12.sp, letterSpacing = 2.sp)
                Text("みのがさナイト", fontSize = 27.sp, fontWeight = FontWeight.Bold)
            }
            TextButton(onClick = { screen = if (screen == "home") "settings" else "home" }) { Text(if (screen == "home") "設定" else "戻る", fontSize = 17.sp) }
        }
        if (screen == "settings") {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                item { Text("自分の好きな番組だけ。", fontSize = 24.sp, fontWeight = FontWeight.Bold) }
                item { Text("東京・千葉の地上波／無料BSの放送予定を表示します。", color = Muted) }
                item { Text("通知", color = Gold, fontSize = 20.sp, modifier = Modifier.padding(top = 16.dp)) }
                item { SettingSwitch("日曜のおすすめ", "毎週日曜 9:00（日本時間）", settings.weekly) { vm.weekly(it); if (it) requestPermission() } }
                item { SettingSwitch("お気に入りの放送前通知", "ONにすると、お気に入りの放送10分前に通知", settings.reminders) { vm.reminders(it); if (it) requestPermission() } }
                item { Text("通知時刻はAndroidの省電力設定などで遅れる場合があります。", fontSize = 14.sp, color = Muted) }
                item { Text(permissionMessage ?: if (canNotify(context)) "端末の通知：許可されています" else "端末の通知：OFF（通常利用できます）", fontSize = 14.sp, color = Gold) }
                item { TextButton(onClick = {
                    context.startActivity(android.content.Intent(android.provider.Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(android.provider.Settings.EXTRA_APP_PACKAGE, context.packageName))
                }) { Text("端末の通知設定を開く") } }
                item { Text("表示するジャンル", color = Gold, fontSize = 20.sp, modifier = Modifier.padding(top = 16.dp)) }
                item { Text("複数選べます。お気に入りにはジャンル設定を適用しません。", color = Muted, fontSize = 14.sp) }
                items(genres) { genre -> SettingSwitch(genre, null, genre in settings.enabled) { vm.genre(genre, it) } }
                item { TextButton(onClick = { screen = "request" }) { Text("ジャンル追加リクエスト", fontSize = 16.sp) } }
                item { Text(BrowseText.creditsTitle, color = Gold, fontSize = 20.sp) }
                item { Text(BrowseText.credits, color = Muted, fontSize = 15.sp) }
                item { TextButton(onClick = { context.startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse("https://cal.syoboi.jp/"))) }) { Text("アニメ情報：しょぼいカレンダー") } }
                item { Text("登録不要・広告なし／v${BuildConfig.VERSION_NAME}\n設定とお気に入りは端末内に保存されます。", color = Muted, fontSize = 14.sp, modifier = Modifier.padding(bottom = 32.dp)) }
            }
        } else if (screen == "request") {
            Column(Modifier.weight(1f).verticalScroll(rememberScrollState())) {
            var draft by remember(settings.draft) { mutableStateOf(settings.draft) }
            var saved by remember { mutableStateOf(false) }
            Text("ジャンル追加リクエスト", fontSize = 23.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(16.dp))
            Text("送信先は準備中です。下書きをこの端末に保存できます。", color = Muted)
            Spacer(Modifier.height(16.dp))
            OutlinedTextField(draft, { draft = it.take(2000); saved = false }, label = { Text("追加したいジャンル・番組例") }, modifier = Modifier.fillMaxWidth().heightIn(min = 160.dp), supportingText = { Text("${draft.length}/2000文字") })
            Button(onClick = { vm.draft(draft); saved = true }, modifier = Modifier.fillMaxWidth()) { Text("下書きを保存", fontSize = 18.sp) }
            if (saved) Text("端末に保存しました。まだ送信されていません。", color = Gold)
            TextButton(onClick = { screen = "settings" }) { Text("設定へ戻る") }
            }
        } else {
            Text(today.format(dateFormat), color = Muted, fontSize = 16.sp)
            Text(if (onlySaved) "全ジャンルのお気に入り" else listOf("今日の気になる番組を。", "明日の楽しみを見つけよう。", "1週間の楽しみをまとめて。")[period], fontSize = 22.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(vertical = 8.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("今日", "明日", "1週間").forEachIndexed { index, label ->
                    FilterChip(selected = period == index, onClick = { period = index }, label = { Text(label, fontSize = 18.sp) }, modifier = Modifier.weight(1f))
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                FilterChip(onlySaved, { onlySaved = !onlySaved }, label = { Text(if (onlySaved) "★ お気に入り" else "☆ お気に入り", fontSize = 16.sp) })
                TextButton(onClick = vm::refresh, enabled = !vm.busy) { Text(if (vm.busy) "更新中…" else "更新") }
            }
            Text("最終更新 ${updated?.let { Instant.ofEpochMilli(it).atZone(Tokyo).format(DateTimeFormatter.ofPattern("M/d HH:mm")) } ?: "未更新"}（日本時間）", color = Muted, fontSize = 12.sp, modifier = Modifier.padding(vertical = 8.dp))
            vm.error?.let { Text(it, color = Gold, fontSize = 14.sp) }
            sync?.notice?.takeIf { it.isNotBlank() }?.let { Text(it, color = Gold, fontSize = 13.sp) }
            if (sync?.let { currentTime >= it.windowEnd && it.windowEnd > 0 } == true) Text("保存済み情報の対象期間が過ぎています。更新してください。", color = Gold, fontSize = 13.sp)
            val visible = remember(programs, favorites, settings.enabled, period, onlySaved, today, currentTime) {
                browsePrograms(programs, favorites, settings.enabled, period, onlySaved, today, currentTime)
            }
            if (visible.isEmpty()) {
                Text(if (vm.busy) "番組を準備しています…" else BrowseText.empty(onlySaved, favorites.isNotEmpty(), settings.enabled.isNotEmpty()), color = Muted, modifier = Modifier.padding(vertical = 32.dp))
            }
            val listState = rememberLazyListState()
            LaunchedEffect(period, visible) {
                val firstUpcoming = if (period == 0) visible.indexOfFirst { it.end > System.currentTimeMillis() } else 0
                listState.scrollToItem(if (firstUpcoming > 0) firstUpcoming + 1 else 0)
            }
            LazyColumn(state = listState, modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(12.dp), contentPadding = PaddingValues(bottom = 24.dp)) {
                visible.groupBy { Instant.ofEpochMilli(it.start).atZone(Tokyo).toLocalDate() }.forEach { (date, list) ->
                    item(key = "date-$date") { Text("${date.format(dateFormat)}  ·  ${list.size}件", color = Muted, modifier = Modifier.padding(top = 8.dp)) }
                    items(list, key = { it.id }) { p -> ProgramCard(p, "p:${p.id}" in favorites, "s:${p.seriesId}" in favorites, { vm.favorite("p:${p.id}") }, { vm.favorite("s:${p.seriesId}") }) }
                }
                item { TextButton(onClick = { screen = "request" }) { Text("ジャンル追加リクエスト", color = Muted, fontSize = 14.sp) } }
            }
        }
    }
}

@Composable
private fun SettingSwitch(title: String, subtitle: String?, checked: Boolean, change: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().padding(vertical = 5.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f).padding(end = 12.dp)) { Text(title, fontSize = 18.sp); subtitle?.let { Text(it, color = Muted, fontSize = 13.sp) } }
        Switch(checked, change)
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ProgramCard(p: Listing, saved: Boolean, series: Boolean, toggle: () -> Unit, toggleSeries: () -> Unit) {
    Surface(color = Panel, shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            Text(time(p.start), color = Gold, fontSize = 23.sp, fontWeight = FontWeight.Bold)
            Text(p.station, color = Muted, fontSize = 15.sp)
            Text(p.title, fontSize = 21.sp, lineHeight = 28.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 10.dp))
            Text(p.tags.joinToString(" · "), color = Purple, fontSize = 13.sp, modifier = Modifier.padding(top = 10.dp))
            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = toggle, modifier = Modifier.heightIn(min = 48.dp).semantics { stateDescription = if (saved) "登録済み" else "未登録" }) { Text(BrowseText.episode(saved), color = if (saved) Gold else Purple, fontSize = 16.sp) }
                if (seriesFavoriteAvailable(p)) {
                    TextButton(onClick = toggleSeries, modifier = Modifier.heightIn(min = 48.dp).semantics { stateDescription = if (series) "登録済み" else "未登録" }) { Text(BrowseText.series(series), color = if (series) Gold else Purple, fontSize = 16.sp) }
                } else if (series) {
                    // Old single-work s: favorites still work and can be removed.
                    TextButton(onClick = toggleSeries, modifier = Modifier.heightIn(min = 48.dp)) { Text("★ 登録を解除", color = Gold, fontSize = 16.sp) }
                }
            }
        }
    }
}
