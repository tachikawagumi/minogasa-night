import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from discovery import quality,plan,issues
from feed import GENRE_IDS,read_json,ROOT,iso
from test_feed import NOW
from test_autopublish import candidate,P

class DiscoveryTest(unittest.TestCase):
    def audit(self,c,public=(),held=(),research=()):
        return quality(dict(records=c,research=list(research)),dict(programs=list(public)),dict(records=list(held)),{},P,NOW)
    def test_all_twenty_have_name_genre_and_schedule_routes(self):
        p=plan(read_json(ROOT/"config/discovery.json"),NOW)
        self.assertEqual(60,len(p["queries"]))
        for g in GENRE_IDS:
            self.assertEqual({"program_name","genre","official_schedule"},{q["route"] for q in p["queries"] if q["genreId"]==g})
    def test_discovered_but_terms_held_is_not_discovery_failure(self):
        c=candidate(sourcePolicyId="unknown",title="ほんとにあった怖い話")
        r=self.audit([c],held=[dict(candidate=c,reason="terms")])
        self.assertEqual("held",r["records"][0]["missingStage"]);self.assertEqual(1,r["heldReasonCounts"]["terms_unconfirmed"])
        self.assertEqual(1,len(r["attention"]))
    def test_same_slot_different_id_is_already_published(self):
        c=candidate();p=dict(c,id="old")
        r=self.audit([c],[p]);self.assertEqual(1,r["alreadyPublished"]);self.assertEqual(0,r["unpublishedFuture"])
    def test_schedule_changed_public_is_outdated(self):
        c=candidate();p=dict(c,start="2026-10-25T18:30:00+09:00")
        self.assertEqual("published_outdated",self.audit([c],[p])["records"][0]["missingStage"])
    def test_zero_without_research_is_not_absence(self):
        r=self.audit([]);self.assertTrue(all(g["zeroExplanation"]=="調査不足" for g in r["genres"]))
    def test_query_plan_cannot_claim_executed_search(self):
        log=dict(genreId="ghost",route="genre",query="怪談",status="planned")
        r=self.audit([],research=[log]);self.assertEqual("not_searched",r["genres"][0]["searchCoverage"])
    def test_both_executed_routes_required_and_no_absence_claim(self):
        logs=[dict(genreId="ghost",route=x,query="怪談",tool="web",status="executed",checkedAt=iso(NOW)) for x in ("program_name","genre")]
        r=self.audit([],research=logs);self.assertEqual("name_and_genre_searched",r["genres"][0]["searchCoverage"])
        self.assertIn("断定しない",r["genres"][0]["zeroExplanation"])
    def test_duplicate_candidates_count_once_and_conflicts_remain_visible(self):
        c=candidate();r=self.audit([c,copy.deepcopy(c),dict(c,title="conflict")])
        self.assertEqual(1,r["discovered"]);self.assertEqual(2,r["inputDuplicates"]);self.assertEqual([c["id"]],r["conflictingIds"])
    def test_expired_candidate_separated_from_rights(self):
        c=candidate(start="2026-10-23T01:00:00+09:00",sourcePolicyId="unknown")
        r=self.audit([c]);self.assertEqual(0,r["unpublishedFuture"]);self.assertIn("outside_window",r["records"][0]["reasonCodes"])
    def test_secret_description_never_in_quality_output(self):
        c=candidate(description="PRIVATE");self.assertNotIn("PRIVATE",str(self.audit([c])))

class MinimalFactScopeTest(unittest.TestCase):
    def apply_scope(self,**changes):
        from test_autopublish import apply,P,candidate
        p=copy.deepcopy(P);c=candidate(sourcePolicyId="limited",acquisitionMethod="ai_web_reference")
        scope={k:c[k] for k in ("title","stationId","start","end","genreIds")}
        p["sources"]["limited"]=dict(p["sources"]["test"],allowedUrls=[c["sourceUrl"]],factRecordScope=scope)
        c.update(changes)
        return apply([c],policies=p)
    def test_reviewed_single_minimal_fact_can_publish(self):
        state,ok,held,_=self.apply_scope()
        self.assertEqual(1,len(ok));self.assertFalse(held)
    def test_scope_does_not_authorize_next_week_or_other_program(self):
        _,ok,held,_=self.apply_scope(start="2026-10-26T17:30:00+09:00")
        self.assertFalse(ok);self.assertTrue(held)
    def test_same_host_other_url_is_not_authorized(self):
        _,ok,held,_=self.apply_scope(sourceUrl="https://official.example.test/unreviewed")
        self.assertFalse(ok);self.assertTrue(held)
    def test_bulk_scraping_or_raw_description_is_not_authorized(self):
        _,ok,held,_=self.apply_scope(acquisitionMethod="bulk_scraper")
        self.assertFalse(ok);self.assertTrue(held)
        _,ok,held,_=self.apply_scope(description="do not republish")
        self.assertFalse(ok);self.assertTrue(held)
