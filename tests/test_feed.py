import copy
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from feed import *
from approve import approve

NOW = datetime(2026, 10, 24, 11, 0, tzinfo=JST)

def fact(**changes):
    row = dict(id="real-test-slot", seriesId="real-test-series", title="THEフィッシング", stationId="tvtokyo", start="2026-10-24T17:30:00+09:00", end=None, genreIds=["fishing"], sourceUrl="https://www.tv-tokyo.co.jp/", checkedAt=iso(NOW), updatedAt=iso(NOW), status="official_confirmed", publicationApproved=True, origin="manual_official_facts", genreBasis="釣り番組の公式題名")
    row.update(changes)
    return row

class FeedTest(unittest.TestCase):
    def test_tokyo_window_has_seven_calendar_days(self):
        a, b = window(datetime(2026, 10, 23, 16, tzinfo=timezone.utc))
        self.assertEqual("2026-10-24T00:00:00+09:00", iso(a))
        self.assertEqual("2026-10-31T00:00:00+09:00", iso(b))

    def test_past_start_and_eighth_day_excluded(self):
        self.assertEqual([], merge_rows([fact(start=iso(NOW)), fact(start="2026-10-31T00:00:00+09:00")], NOW))

    def test_same_station_and_time_merges_tags(self):
        rows = merge_rows([fact(), fact(id="other", genreIds=["travel"])], NOW)
        self.assertEqual(1, len(rows))
        self.assertEqual({"travel", "fishing"}, set(rows[0]["genreIds"]))

    def test_subtitle_reconciles_with_provider_pid(self):
        rows = merge_rows([fact(title="THEフィッシング 第1回"), fact(id="syobocal-111", title="THEフィッシング", origin="syobocal")], NOW)
        self.assertEqual(1, len(rows))
        self.assertEqual("syobocal-111", rows[0]["id"])

    def test_same_time_unrelated_title_is_not_merged(self):
        rows = merge_rows([fact(), fact(id="b", title="鉄道伝説")], NOW)
        self.assertEqual(2, len(rows))

    def test_different_station_and_time_remain_separate(self):
        rows = merge_rows([fact(), fact(id="b", stationId="tbs"), fact(id="c", start="2026-10-25T17:30:00+09:00")], NOW)
        self.assertEqual(3, len(rows))

    def test_unapproved_and_uncertain_are_not_published(self):
        self.assertEqual([], merge_rows([fact(publicationApproved=False), fact(status="pending")], NOW))

    def test_unknown_genre_is_rejected(self):
        with self.assertRaises(ValueError):
            merge_rows([fact(genreIds=["unknown"])], NOW)

    def test_paid_channel_is_rejected(self):
        with self.assertRaises(ValueError):
            merge_rows([fact(stationId="skyperfectv")], NOW)

    def test_naive_time_and_invalid_end_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_dt("2026-10-24T17:30:00")
        with self.assertRaises(ValueError):
            merge_rows([fact(end="2026-10-24T17:00:00+09:00")], NOW)

    def test_descriptions_and_secrets_are_rejected(self):
        for key in ("description", "apiKey", "token", "cast", "image"):
            with self.assertRaises(ValueError):
                merge_rows([fact(**{key: "not permitted"})], NOW)

    def test_feed_has_twenty_genres_and_minimal_fields(self):
        feed, _ = build_feed([fact()], {"rows": []}, NOW, True)
        self.assertEqual(1, validate_public(feed))
        self.assertEqual(20, len(feed["genres"]))
        self.assertNotIn("genreBasis", feed["programs"][0])
        self.assertNotIn("sourceUrl", feed["programs"][0])

    def test_failure_preserves_cached_future_records_and_marks_partial(self):
        cache = {"rows": [fact(origin="syobocal")], "checkedAt": iso(NOW - timedelta(days=1))}
        original = copy.deepcopy(cache)
        feed, _ = build_feed([], cache, NOW, False)
        self.assertEqual(cache, original)
        self.assertEqual("partial", feed["updateStatus"])
        self.assertEqual(1, len(feed["programs"]))
        self.assertEqual(original["checkedAt"], feed["coverage"][0]["animeCheckedAt"])

    def test_duplicate_id_on_different_airing_is_rejected(self):
        with self.assertRaises(ValueError):
            merge_rows([fact(), fact(start="2026-10-25T17:30:00+09:00")], NOW)

    def test_manual_approval_requires_official_status_and_basis(self):
        with self.assertRaises(ValueError):
            approve({"records": [fact(status="pending")]}, {"records": []}, NOW)
        with self.assertRaises(ValueError):
            approve({"records": [fact(genreBasis="")]}, {"records": []}, NOW)
        approved = approve({"records": [fact(publicationApproved=False)]}, {"records": []}, NOW)
        self.assertTrue(approved["records"][0]["publicationApproved"])

    def test_api_parser_reads_saved_seven_day_response(self):
        path = ROOT / "docs/phase3-2026-10-24/syobocal-week-probe.xml"
        if not path.exists():
            self.skipTest("初回調査資料がない配信専用パッケージ")
        root = ET.fromstring(path.read_text(encoding="utf-8-sig"))
        self.assertEqual("200", root.findtext("Result/Code"))
        dates = {x.findtext("StTime")[:10] for x in root.findall("ProgItems/ProgItem")}
        self.assertEqual(7, len(dates))

if __name__ == "__main__":
    unittest.main()
