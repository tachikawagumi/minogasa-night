import copy, json, sys, unittest
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from ledger import project, upsert
from autopublish import integrate_candidates
from feed import GENRE_IDS
class Phase13FactIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.rows=json.loads((ROOT/"docs/phase13/verified-additions.json").read_text(encoding="utf-8"))["records"]
        self.policy=json.loads((ROOT/"config/source-policy.json").read_text(encoding="utf-8"))
        self.now=datetime.fromisoformat("2026-10-29T14:42:05+09:00")
    def integrate(self, rows):
        ledger=upsert([],rows)
        return integrate_candidates([],{"records":[project(r) for r in ledger]},[],{"rows":[]},self.policy,self.now)
    def test_all_eight_verified_airings_pass_existing_publication_rules(self):
        result,accepted,held,cancelled=self.integrate(self.rows)
        self.assertEqual(8,len(result));self.assertEqual(8,len(accepted));self.assertEqual([],held)
        self.assertTrue(all(r["genreIds"]==["golf"] for r in result))
        self.assertEqual(8,len({(r["stationId"],r["start"]) for r in result}))
        pair=next(r for r in result if r["title"]=="女子ゴルフペアマッチ選手権")
        self.assertEqual("official-series-142a8e1007439f2e224e685c",pair["seriesId"])
    def test_unreviewed_date_change_is_held_without_acceptance(self):
        rows=copy.deepcopy(self.rows[:1]);rows[0]["start"]="2026-11-02T23:20:00+09:00"
        result,accepted,held,_=self.integrate(rows)
        self.assertEqual([],result);self.assertEqual([],accepted);self.assertEqual(1,len(held))
        self.assertIn("不一致",held[0]["reason"])
    def test_regular_references_cover_twenty_genres_without_creating_slots(self):
        db=json.loads((ROOT/"config/regular-programs.json").read_text(encoding="utf-8"))
        self.assertEqual(set(GENRE_IDS),{g for r in db["entries"] for g in r["genreIds"]})
        self.assertTrue(all("start" not in r and "end" not in r for r in db["entries"]))
        self.assertEqual([],integrate_candidates([],{"records":[],"regularPrograms":db},[],{"rows":[]},self.policy,self.now)[0])
