"""VICTORY K: minimal fact feed, Python standard library only; no OpenAI API."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9), "Asia/Tokyo")
UA = "MinogasaNight/1.0 (VICTORY K)"
API = "https://cal.syoboi.jp/db.php"
GENRES = ["心霊・怪談", "UFO・都市伝説", "映画", "ホラー映画", "ディズニー", "USJ", "大食い", "温泉", "建物探訪", "車", "ダンス", "ゴルフ", "サッカー", "野球", "釣り", "健康", "旅", "ゲーム・チャレンジ", "アニメ", "電車・鉄道"]
GENRE_IDS = ["ghost", "ufo", "movie", "horror_movie", "disney", "usj", "big_eating", "onsen", "architecture", "car", "dance", "golf", "soccer", "baseball", "fishing", "health", "travel", "challenge", "anime", "railway"]
# IDs were resolved using ChLookup, never from channel numbers or substring matching.
STATIONS = {"nhk_g": ("NHK総合", "1"), "nhk_e": ("NHK Eテレ", "2"), "fuji": ("フジテレビ", "3"), "ntv": ("日本テレビ", "4"), "tbs": ("TBS", "5"), "tvasahi": ("テレビ朝日", "6"), "tvtokyo": ("テレビ東京", "7"), "chiba": ("チバテレ", "13"), "bstvtokyo": ("BSテレ東", "15"), "bstbs": ("BS-TBS", "16"), "bsfuji": ("BSフジ", "17"), "bsasahi": ("BS朝日", "18"), "mx": ("TOKYO MX", "19"), "bsntv": ("BS日テレ", "71"), "bs11": ("BS11イレブン", "128"), "bs12": ("BS12トゥエルビ", "129"), "mx2": ("TOKYO MX2", "187")}
STATIONS["nhk_bs"] = ("NHK BS", None)  # Official-fact source only; no guessed provider channel ID.
from source_rules import load_stations
STATIONS = load_stations(ROOT / "config/stations.json", STATIONS)
CH_MAP = {value[1]: key for key, value in STATIONS.items() if value[1] is not None}

def iso(dt):
    return dt.astimezone(JST).isoformat(timespec="seconds")

def parse_dt(value):
    if not isinstance(value, str):
        raise ValueError("日時はタイムゾーン付き文字列が必要")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("タイムゾーン省略不可")
    return dt.astimezone(JST)

def canonical(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).casefold()

def short_id(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]

def window(now):
    start = now.astimezone(JST).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=7)

def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default

def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)

class Syobocal:
    def __init__(self):
        self.last_call = 0
        self.requests = []

    def get(self, **params):
        # Always serial. A failed attempt never starts a tight retry loop.
        time.sleep(max(0, 1.1 - (time.monotonic() - self.last_call)))
        url = API + "?" + urllib.parse.urlencode(params)
        self.requests.append(url)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as response:
                raw = response.read(3_000_001)
            if len(raw) > 3_000_000:
                raise ValueError("API応答が上限を超過")
            root = ET.fromstring(raw)
            if root.findtext("Result/Code") != "200":
                raise ValueError("API Result/Code が200でない")
            return root
        finally:
            self.last_call = time.monotonic()

    def collect(self, now, cache):
        start, finish = window(now)
        channels = self.get(Command="ChLookup", Fields="ChID,ChName")
        actual = {x.findtext("ChID"): x.findtext("ChName") for x in channels.findall("ChItems/ChItem")}
        for station, (name, chid) in STATIONS.items():
            if chid is None:
                continue
            # Chiba uses a different official label in this database.
            if actual.get(chid) != ("チバテレビ" if station == "chiba" else name):
                raise ValueError("局IDと局名の対応が変化: " + station)
        root = self.get(Command="ProgLookup", Range=start.strftime("%Y%m%d_%H%M%S") + "-" + finish.strftime("%Y%m%d_%H%M%S"), ChID=",".join(CH_MAP), Fields="PID,TID,ChID,StTime,EdTime,LastUpdate,Deleted,Warn,Revision")
        items = root.findall("ProgItems/ProgItem")
        if len(items) >= 5000:
            raise ValueError("API上限に達したため不完全な全件更新を拒否")
        tids = sorted({x.findtext("TID") for x in items if x.findtext("Deleted") != "1"})
        titles = {}
        for offset in range(0, len(tids), 100):
            result = self.get(Command="TitleLookup", TID=",".join(tids[offset:offset + 100]), Fields="TID,Title,Cat,LastUpdate")
            titles.update({x.findtext("TID"): x for x in result.findall("TitleItems/TitleItem")})
        rows = []
        for item in items:
            values = {x.tag: x.text or "" for x in item}
            if values.get("Deleted") == "1" or values.get("Warn") not in ("", "0"):
                continue
            title_data = titles.get(values["TID"])
            if title_data is None:
                raise ValueError("タイトル結合に不足があり更新を中止")
            # Cat=1 is anime; related radio, variety and live-action are not auto-classified.
            if title_data.findtext("Cat") != "1":
                continue
            title = title_data.findtext("Title") or ""
            station_id = CH_MAP.get(values["ChID"])
            if not title or not station_id:
                raise ValueError("必須項目が不足")
            begin = datetime.fromisoformat(values["StTime"]).replace(tzinfo=JST)
            end = datetime.fromisoformat(values["EdTime"]).replace(tzinfo=JST)
            rows.append(dict(id="syobocal-" + values["PID"], seriesId="syobocal-title-" + values["TID"], title=title, stationId=station_id, start=iso(begin), end=iso(end), genreIds=["anime"], sourceUrl="https://cal.syoboi.jp/" + values["TID"] + "/time?Filter=" + values["ChID"], checkedAt=iso(now), updatedAt=iso(now), sourceUpdatedAt=values.get("LastUpdate"), status="provider_confirmed", publicationApproved=True, origin="syobocal", sourcePid=values["PID"], revision=values.get("Revision")))
        return {"checkedAt": iso(now), "rows": rows, "requests": self.requests, "rawSlots": len(items), "deletedPids": [x.findtext("PID") for x in items if x.findtext("Deleted")=="1"]}

def merge_rows(rows, now):
    begin, finish = window(now)
    groups = {}
    for source in rows:
        row = dict(source)
        if not row.get("publicationApproved") or row.get("status") not in ("official_confirmed", "provider_confirmed"):
            continue
        start = parse_dt(row["start"])
        if not (now < start < finish and start >= begin):
            continue
        if row.get("end") and parse_dt(row["end"]) <= start:
            raise ValueError("終了時刻が開始以前")
        if row.get("stationId") not in STATIONS or not set(row.get("genreIds", [])) <= set(GENRE_IDS) or not row.get("genreIds"):
            raise ValueError("未定義の局・ジャンル")
        for field in ("checkedAt", "updatedAt"):
            if parse_dt(row[field]) > now + timedelta(minutes=5):
                raise ValueError("確認日時が未来")
        if not row.get("sourceUrl", "").startswith("https://"):
            raise ValueError("出典URLが不足")
        if any(key in row for key in ("description", "cast", "image", "apiKey", "token")):
            raise ValueError("不要な本文・秘密情報は保存不可")
        key = (row["stationId"], iso(start), canonical(row["title"]))
        # Preserve provider PID/series IDs across cancellation and time changes.
        # A provider title can omit the official episode subtitle. Only reconcile
        # when station and exact start agree AND one normalized title contains the other.
        alias = next((k for k in groups if k[:2] == key[:2] and (k[2] in key[2] or key[2] in k[2])), key)
        existing = groups.get(alias)
        if existing:
            tags = sorted(set(existing["genreIds"]) | set(row["genreIds"]))
            if row.get("origin") == "syobocal":
                groups[alias] = row
            groups[alias]["genreIds"] = tags
        else:
            groups[key] = row
    result = sorted(groups.values(), key=lambda x: (x["start"], x["stationId"], x["id"]))
    if len({x["id"] for x in result}) != len(result):
        raise ValueError("異なる枠で同じ番組IDが使われている")
    return result

def build_feed(manual, anime, now, anime_ok):
    rows = merge_rows(manual + anime.get("rows", []), now)
    start, end = window(now)
    coverage = []
    for station_id, (name, chid) in STATIONS.items():
        coverage.append({"stationId": station_id, "station": name, "anime": ("updated" if anime_ok else "cached") if chid is not None else "not_collected", "otherGenres": "selected_verified_facts_only", "animeCheckedAt": anime.get("checkedAt") if chid is not None else None, "complete": False})
    public_rows = [{key: row.get(key) for key in ("id", "seriesId", "title", "stationId", "start", "end", "genreIds", "status", "checkedAt", "updatedAt")} for row in rows]
    return {"schemaVersion": 1, "sourceMode": "real", "timeZone": "Asia/Tokyo", "generatedAt": iso(now), "windowStart": iso(start), "windowEnd": iso(end), "updateStatus": "ok" if anime_ok else "partial", "notice": "対象局の全番組を網羅するものではありません。" + ("" if anime_ok else "アニメの更新に失敗し、保存済みの情報を使用しています。"), "genres": [{"id": key, "name": name} for key, name in zip(GENRE_IDS, GENRES)], "stations": [{"id": key, "name": value[0]} for key, value in STATIONS.items()], "coverage": coverage, "programs": public_rows}, rows

def validate_public(feed):
    if feed.get("schemaVersion") != 1 or feed.get("sourceMode") != "real" or feed.get("timeZone") != "Asia/Tokyo":
        raise ValueError("不正なフィード種別")
    now = parse_dt(feed["generatedAt"])
    if len(feed["genres"]) != 20:
        raise ValueError("20ジャンルが必要")
    if [x["id"] for x in feed["genres"]] != GENRE_IDS:
        raise ValueError("ジャンルID不一致")
    ids, keys = set(), set()
    for row in feed["programs"]:
        if row["id"] in ids:
            raise ValueError("ID重複")
        ids.add(row["id"])
        key = (row["stationId"], row["start"], canonical(row["title"]))
        if key in keys:
            raise ValueError("放送枠重複")
        keys.add(key)
        if not now < parse_dt(row["start"]) < parse_dt(feed["windowEnd"]):
            raise ValueError("生成時点で過去または期間外")
        if not row["genreIds"] or not set(row["genreIds"]) <= set(GENRE_IDS):
            raise ValueError("ジャンル不正")
        if row["stationId"] not in STATIONS:
            raise ValueError("対象外局")
        if row["status"] not in ("official_confirmed", "provider_confirmed"):
            raise ValueError("未確認データの公開を拒否")
        if not row["title"].strip() or "サンプル" in row["title"]:
            raise ValueError("空タイトル・サンプル不可")
    return len(ids)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="保存済みAPIキャッシュを使う。更新成功とは記録しない")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    public_path = ROOT / "public/v1/programs.json"
    if args.validate:
        print("VALID", validate_public(read_json(public_path)))
        return
    now = datetime.now(JST)
    cache_path = ROOT / "data/anime-cache.json"
    old = read_json(cache_path, {"rows": [], "checkedAt": None})
    ok, error = False, None
    if not args.offline:
        try:
            candidate = Syobocal().collect(now, old)
            # Validate before replacing the last good cache, including date/end checks.
            merge_rows(candidate["rows"], now)
            old = candidate
            atomic_json(cache_path, old)
            ok = True
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)[:240]
            print("ANIME_UPDATE_FAILED; last good cache preserved:", error)
    manual = read_json(ROOT / "data/manual-approved.json", {"records": []})["records"]
    feed, internal = build_feed(manual, old, now, ok)
    validate_public(feed)
    atomic_json(ROOT / "data/current-db.json", {"generatedAt": iso(now), "records": internal})
    atomic_json(public_path, feed)
    atomic_json(ROOT / "data/update-result.json", {"at": iso(now), "animeSuccess": ok, "error": error, "publicPrograms": len(feed["programs"]), "apiRawSlots": old.get("rawSlots"), "animeCheckedAt": old.get("checkedAt")})
    print("FEED", len(feed["programs"]), "anime_updated", ok)

if __name__ == "__main__":
    main()
