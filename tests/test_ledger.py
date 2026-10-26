import copy,json,tempfile,unittest,sys
from pathlib import Path
from datetime import timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import ledger,autopublish
from discovery import quality,plan
from feed import ROOT,STATIONS,CH_MAP,build_feed,iso,read_json,atomic_json
from test_feed import NOW
from test_autopublish import P

def lead(**changes):
    r=dict(id="lead-1",seriesId="series-1",title="Unknown episode",stationId="nhk_bs",
      claimedStart=iso(NOW+timedelta(days=1)),claimedEnd=None,start=None,end=None,
      genreIds=[],candidateGenreIds=["ufo"],sourceUrl="https://official.example.test/episode",
      sourceUrls=["https://official.example.test/episode"],discoveredAt=iso(NOW),checkedAt=iso(NOW),lastAttemptAt=iso(NOW),
      officialVerification=dict(title=False,station=False,datetime=False,content=False),
      classification=dict(level="related",basis="Not confirmed"),decision="held",holdReasons=["need official time"],sourcePolicyId="unknown")
    r.update(changes);return r

class LedgerTest(unittest.TestCase):
    def test_unverified_claim_is_saved_not_projected(self):
        x=ledger.upsert([],[lead()])
        self.assertEqual(1,len(x));self.assertIsNone(x[0]["start"]);self.assertIsNone(ledger.project(x[0]))
    def test_false_confirmed_start_is_rejected(self):
        with self.assertRaises(ValueError): ledger.upsert([],[lead(start=iso(NOW))])
    def test_related_classification_never_becomes_public(self):
        r=lead(decision="eligible",start=iso(NOW+timedelta(days=1)),genreIds=["ufo"],officialVerification=dict(title=True,station=True,datetime=True,content=True,sourceUrl="https://official.example.test/episode"))
        self.assertIsNone(ledger.project(r))
    def test_complete_clear_fact_projects_without_claim_fields(self):
        r=lead(decision="eligible",start=iso(NOW+timedelta(days=1)),genreIds=["ufo"],classification=dict(level="clear",basis="verified episode"),
          officialVerification=dict(title=True,station=True,datetime=True,content=True,sourceUrl="https://official.example.test/episode"))
        p=ledger.project(r);self.assertIsNotNone(p);self.assertNotIn("claimedStart",p);self.assertFalse(p["publicationApproved"])
    def test_claim_url_and_body_secrets_are_rejected(self):
        for bad in [lead(description="no"),lead(sourceUrls=["https://official.example.test/?token=secret"])]:
            with self.assertRaises(ValueError): ledger.upsert([],[bad])
    def test_research_cache_and_old_update_does_not_overwrite(self):
        r=lead();self.assertFalse(ledger.ready_for_research(r,NOW));self.assertTrue(ledger.ready_for_research(r,NOW+timedelta(hours=49)))
        old=lead(title="older",checkedAt=iso(NOW-timedelta(days=1)))
        self.assertEqual(r,ledger.upsert([r],[old])[0])
    def test_save_discovery_even_if_source_acquisition_fails(self):
        class Broken:
            def collect(self,*args): raise OSError("source unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);atomic_json(root/"data/ai-candidates.json",dict(records=[],discoveries=[lead()]))
            feed=build_feed([],dict(rows=[]),NOW,True)[0];atomic_json(root/"public/v1/programs.json",feed)
            original=(root/"public/v1/programs.json").read_bytes();saved=autopublish.ROOT
            try:
                autopublish.ROOT=root
                with self.assertRaises(OSError): autopublish.run(NOW,Broken())
            finally: autopublish.ROOT=saved
            self.assertEqual(1,len(read_json(root/"data/discovered-candidates.json")["records"]))
            self.assertEqual(original,(root/"public/v1/programs.json").read_bytes())
    def test_nhk_bs_can_be_represented_without_guessing_provider_id(self):
        self.assertEqual(("NHK BS",None),STATIONS["nhk_bs"]);self.assertNotIn(None,CH_MAP)
    def test_three_levels_and_conflicts_are_validated(self):
        for x in [lead(classification=dict(level="unknown",basis="x")),lead(classification=dict(level="clear",basis=""))]:
            with self.assertRaises(ValueError): ledger.upsert([],[x])
        with self.assertRaises(ValueError): ledger.upsert([],[lead(),lead(title="conflict")])

class LedgerQualityTest(unittest.TestCase):
    def audit(self,rows):
        return quality(dict(records=[],research=[]),dict(programs=[]),dict(records=[]),{},P,NOW,rows)
    def test_unconfirmed_discovery_is_counted_without_being_confirmed_omission(self):
        q=self.audit([lead()]);g=next(g for g in q["genres"] if g["genreId"]=="ufo")
        self.assertEqual(1,g["candidates"]);self.assertEqual(0,g["datetimeConfirmed"]);self.assertEqual(0,g["omissions"]);self.assertEqual(1,g["held"])
    def test_confirmed_clear_unpublished_is_traceable_omission(self):
        r=lead(start=iso(NOW+timedelta(days=1)),genreIds=["ufo"],classification=dict(level="clear",basis="content"),
         officialVerification=dict(title=True,station=True,datetime=True,content=True,sourceUrl="https://official.example.test/episode"))
        q=self.audit([r]);self.assertEqual(1,len(q["confirmedOmissions"]));self.assertTrue(q["records"][0]["holdReasons"])
    def test_excluded_is_not_an_omission_or_held(self):
        q=self.audit([lead(decision="excluded",classification=dict(level="excluded",basis="wrong genre"))])
        self.assertEqual(1,q["excluded"]);self.assertEqual(0,q["held"]);self.assertFalse(q["confirmedOmissions"])
    def test_all_genres_have_four_discovery_routes(self):
        p=plan(read_json(ROOT/"config/discovery.json"),NOW)
        self.assertEqual(80,len(p["queries"]))
        self.assertEqual(20,len([r for r in p["queries"] if r["route"]=="miss_learning"]))
    def test_search_does_not_prove_absence(self):
        q=self.audit([]);self.assertTrue(all(g["zeroReasonCode"]=="search_insufficient" for g in q["genres"]))
