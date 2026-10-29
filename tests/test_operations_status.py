import json, sys, tempfile, unittest
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from operations_status import build_status, latest_due

NOW = datetime.fromisoformat("2026-10-29T13:30:00+09:00")
class OperationsStatusTests(unittest.TestCase):
    def fixture(self, root):
        def put(path, obj):
            target=root/path; target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(obj),encoding="utf-8")
        put("public/v1/programs.json",dict(windowStart="2026-10-29T00:00:00+09:00",windowEnd="2026-11-05T00:00:00+09:00",
            genres=[dict(id="movie",name="映画"),dict(id="usj",name="USJ")],
            programs=[dict(id="film",genreIds=["movie"],start="2026-11-04T19:00:00+09:00")]))
        put("data/update-result.json",dict(status="published",publicationVerified=True,at="2026-10-29T09:40:31+09:00",
            verification=dict(verifiedAt="2026-10-29T09:40:58+09:00")))
        return put
    def test_morning_actions_success_is_not_new_ai_search(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); put=self.fixture(root)
            put("data/ai-candidates.json",dict(researchedAt="2026-10-27T17:41:36+09:00",executionContext="interactive_preflight"))
            v=build_status(root,NOW,{})
            self.assertTrue(v["lastPages"]["verified"])
            self.assertFalse(v["latestScheduledSlot"]["heartbeatObserved"])
            self.assertEqual("2026-10-27T17:41:36+09:00",v["lastAIResearch"]["at"])
    def test_late_heartbeat_keeps_actual_time(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); put=self.fixture(root)
            put("data/ai-research-runs.json",dict(runs=[dict(executionContext="scheduled_heartbeat",
                scheduledFor="2026-10-29T09:00:00+09:00",triggerReceivedAt="2026-10-29T13:04:47+09:00",onTime=False)]))
            v=build_status(root,NOW,{})
            self.assertEqual("late_observed",v["latestScheduledSlot"]["status"])
            self.assertFalse(v["latestScheduledSlot"]["onTime"])
    def test_interactive_research_does_not_prove_scheduled_trigger(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); put=self.fixture(root)
            put("data/ai-research-runs.json",dict(runs=[dict(executionContext="interactive_preflight",
                scheduledFor="2026-10-29T09:00:00+09:00",onTime=True)]))
            self.assertFalse(build_status(root,NOW,{})["latestScheduledSlot"]["heartbeatObserved"])
    def test_coverage_preserves_zero_genres_and_last_start(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.fixture(root)
            v=build_status(root,NOW,{})
            self.assertEqual(2,len(v["genreCoverage"]))
            self.assertEqual("2026-11-04T19:00:00+09:00",v["genreCoverage"][0]["lastStart"])
            self.assertEqual(0,v["genreCoverage"][1]["programs"])
            self.assertIsNone(v["genreCoverage"][1]["lastStart"])
    def test_only_actual_current_window_searches_count(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); put=self.fixture(root); t="2026-10-29T13:20:00+09:00"
            log=dict(genreId="movie",checkedAt=t,windowStart="2026-10-29T00:00:00+09:00",
                     windowEnd="2026-11-05T00:00:00+09:00",status="executed")
            put("data/ai-candidates.json",dict(researchedAt=t,research=[log,dict(log,status="planned"),
                dict(log,checkedAt="2026-10-27T17:00:00+09:00")]))
            v=build_status(root,NOW,dict(GITHUB_RUN_ID="123",GITHUB_EVENT_NAME="push"))
            self.assertEqual(1,v["lastAIResearch"]["queries"])
            self.assertEqual("123",v["lastActions"]["runId"])
            self.assertIsNone(v["lastActions"]["startTime"])
    def test_due_slot_uses_japan_calendar_and_future_dates_rejected(self):
        self.assertEqual("2026-10-26T09:00:00+09:00",latest_due(datetime.fromisoformat("2026-10-29T08:59:00+09:00")).isoformat())
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); put=self.fixture(root)
            put("data/ai-candidates.json",dict(researchedAt="2026-10-30T09:00:00+09:00"))
            with self.assertRaises(ValueError): build_status(root,NOW,{})
