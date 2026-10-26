import copy, json, tempfile, unittest, sys
from pathlib import Path
from datetime import timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import autopublish as a
from feed import build_feed, iso
from test_feed import fact, NOW

P={"sources":{"test":{"enabled":True,"mode":"official_facts","hosts":["official.example.test"],"permissions":["metadata","cache","redistribute","automated_access"]},"syobocal":{"enabled":True,"mode":"provider_match","hosts":["cal.syoboi.jp"],"permissions":["metadata","cache","redistribute","automated_access"],"officialVerificationHosts":["www.tbs.co.jp"]}}}
def candidate(**changes):
    r=fact(sourceUrl="https://official.example.test/episode",sourcePolicyId="test",officialVerified=True,genreEvidence={"fishing":"official episode confirms fishing"})
    r.update(changes);return r
def apply(rows,existing=(),previous=(),provider=None,policies=P):
    return a.integrate_candidates(list(existing),{"records":rows},list(previous),provider or {"rows":[]},policies,NOW)
def envelope(rows):
    return build_feed(rows,{"rows":[]},NOW,True)[0]

class AutoPublishTest(unittest.TestCase):
    def test_unreviewed_rights_are_held_without_approval(self):
        state,ok,held,_=apply([candidate(sourcePolicyId="unknown")])
        self.assertFalse(state);self.assertFalse(ok);self.assertIn("条件",held[0]["reason"])
    def test_policy_host_cannot_be_forged(self):
        _,ok,held,_=apply([candidate(sourceUrl="https://other.example.test/")])
        self.assertFalse(ok);self.assertTrue(held)
    def test_provider_match_accepts_only_authoritative_slot(self):
        p=fact(id="syobocal-99",sourcePid="99",origin="syobocal",title="氷の城壁",genreIds=["anime"],sourceUrl="https://cal.syoboi.jp/1/time",status="provider_confirmed")
        c=candidate(id=p["id"],title="氷の城壁 第19話",sourcePid="99",sourcePolicyId="syobocal",sourceUrl=p["sourceUrl"],genreIds=["anime"],officialVerificationUrl="https://www.tbs.co.jp/tv/")
        state,ok,held,_=apply([c],provider={"rows":[p]})
        self.assertEqual("syobocal-99",state[0]["id"]);self.assertEqual(1,len(ok));self.assertFalse(held)
    def test_provider_schedule_mismatch_is_held(self):
        p=fact(sourcePid="99",title="Anime",genreIds=["anime"])
        _,ok,held,_=apply([candidate(title="Anime",sourcePid="99",sourcePolicyId="syobocal",sourceUrl="https://cal.syoboi.jp/1/time",genreIds=["anime"],stationId="tbs")],provider={"rows":[p]})
        self.assertFalse(ok);self.assertTrue(held)
    def test_provider_cannot_supply_unproven_extra_genres(self):
        p=fact(sourcePid="99",title="Anime",genreIds=["anime"])
        _,ok,held,_=apply([candidate(title="Anime",sourcePid="99",sourcePolicyId="syobocal",sourceUrl="https://cal.syoboi.jp/1/time",genreIds=["anime","ghost"])],provider={"rows":[p]})
        self.assertFalse(ok);self.assertTrue(held)
    def test_schedule_change_preserves_program_and_series_ids(self):
        old=fact()
        state,ok,held,_=apply([candidate(start="2026-10-25T17:30:00+09:00",stationId="tbs",seriesId="new-wrong-series")],previous=[old])
        self.assertFalse(held);self.assertEqual(old["id"],state[0]["id"]);self.assertEqual(old["seriesId"],state[0]["seriesId"])
        diff=a.public_diff(envelope([old]),envelope(state),NOW)
        self.assertEqual([old["id"]],diff["scheduleChanged"]);self.assertFalse(diff["added"])
    def test_genre_correction_replaces_old_tags(self):
        old=fact(genreIds=["fishing","travel"])
        state,_,held,_=apply([candidate()],existing=[old],previous=[old])
        self.assertFalse(held);self.assertEqual(["fishing"],state[0]["genreIds"])
        self.assertEqual([old["id"]],a.public_diff(envelope([old]),envelope(state),NOW)["genreChanged"])
    def test_duplicate_airing_keeps_existing_id(self):
        old=fact()
        state,_,held,_=apply([candidate(id="new-duplicate")],previous=[old])
        self.assertFalse(held);self.assertEqual(old["id"],state[0]["id"]);self.assertEqual(1,len(state))
    def test_cancellation_requires_confirmation(self):
        old=fact()
        _,ok,held,_=apply([candidate(operation="cancel")],existing=[old],previous=[old])
        self.assertFalse(ok);self.assertTrue(held)
        state,ok,held,cancelled=apply([candidate(operation="cancel",cancellationConfirmed=True)],existing=[old],previous=[old])
        self.assertFalse(state);self.assertFalse(held);self.assertEqual([old["id"]],cancelled)
    def test_provider_cancellation_requires_deleted_pid(self):
        c=candidate(id="syobocal-99",operation="cancel",sourcePid="99",sourcePolicyId="syobocal",sourceUrl="https://cal.syoboi.jp/1/time")
        _,ok,held,cancelled=apply([c],provider={"rows":[],"deletedPids":["99"]})
        self.assertFalse(held);self.assertEqual(["syobocal-99"],cancelled)
    def test_unrelated_title_at_same_station_time_is_conflict(self):
        _,ok,held,_=apply([candidate(id="different",title="Unrelated")],previous=[fact()])
        self.assertFalse(ok);self.assertTrue(held)
    def test_ambiguous_duplicate_candidates_are_both_held(self):
        state,ok,held,_=apply([candidate(),candidate(title="Conflicting title")])
        self.assertFalse(state);self.assertFalse(ok);self.assertEqual(2,len(held))
    def test_absence_from_batch_is_not_cancellation(self):
        old=fact()
        state,_,_,cancelled=apply([],existing=[old])
        self.assertEqual([old],state);self.assertFalse(cancelled)
    def test_stale_and_past_candidates_are_held(self):
        for c in [candidate(checkedAt=iso(NOW-timedelta(days=5))),candidate(start=iso(NOW-timedelta(minutes=1)))]:
            _,ok,held,_=apply([c]);self.assertFalse(ok);self.assertTrue(held)
    def test_missing_genre_evidence_is_held(self):
        _,ok,held,_=apply([candidate(genreEvidence={})])
        self.assertFalse(ok);self.assertTrue(held)
    def test_secret_field_is_not_persisted_in_hold(self):
        _,_,held,_=apply([candidate(token="secret")])
        self.assertNotIn("secret",json.dumps(held))
    def test_empty_result_is_blocked(self):
        with self.assertRaises(a.PublicationBlocked): a.protect_last_good(envelope([fact()]),envelope([]),NOW)
    def test_mass_disappearance_is_blocked(self):
        rows=[fact(id=str(i),title="Test programme",start=iso(NOW+timedelta(hours=1,minutes=i))) for i in range(20)]
        with self.assertRaises(a.PublicationBlocked): a.protect_last_good(envelope(rows),envelope(rows[:5]),NOW)
    def test_normal_expiry_is_not_false_mass_loss(self):
        old=envelope([fact()])
        later=NOW+timedelta(days=2)
        empty=build_feed([],{"rows":[]},later,True)[0]
        self.assertFalse(a.protect_last_good(old,empty,later)["removed"])
    def test_acquisition_failure_preserves_public_and_cache_bytes(self):
        class Broken:
            def collect(self,*_): raise OSError("source unavailable")
        original=a.ROOT
        try:
            with tempfile.TemporaryDirectory() as d:
                a.ROOT=Path(d)
                for rel,obj in [("public/v1/programs.json",envelope([fact()])),("data/current-db.json",{"records":[fact()]}),("data/anime-cache.json",{"rows":[fact()]})]:
                    p=a.ROOT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj))
                before={rel:(a.ROOT/rel).read_bytes() for rel in ["public/v1/programs.json","data/anime-cache.json"]}
                with self.assertRaises(OSError): a.run(NOW,Broken())
                for rel,raw in before.items(): self.assertEqual(raw,(a.ROOT/rel).read_bytes())
                self.assertEqual("failed",json.loads((a.ROOT/"data/update-result.json").read_text())["status"])
        finally: a.ROOT=original
