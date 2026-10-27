"""Compatibility tests for manually researched third-party programme facts."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from ledger import upsert,project
from discovery import quality
from test_autopublish import candidate,P
from test_feed import NOW
from feed import iso

class ScheduleReferenceTest(unittest.TestCase):
    def lead(self):
        c=candidate()
        r={k:c[k] for k in ("id","seriesId","title","stationId","start","end","genreIds","sourceUrl","checkedAt","sourcePolicyId","genreEvidence")}
        r.update(sourceUrls=[c["sourceUrl"]],classification={"level":"clear","basis":"当該回の内容を確認"},decision="published",officialVerification={"title":False,"station":False,"datetime":False,"content":False},scheduleVerification={"title":True,"station":True,"datetime":True,"content":True,"sourceUrl":c["sourceUrl"]})
        return r
    def test_third_party_fact_is_retained_without_claiming_official_verification(self):
        r=self.lead();saved=upsert([], [r])[0]
        self.assertEqual(r["start"],saved["start"])
        self.assertFalse(saved["officialVerification"]["datetime"])
        self.assertIsNone(project(saved)) # This one-off publication uses the existing approved-record path.
        bad=copy.deepcopy(r);bad["scheduleVerification"]["datetime"]=False
        with self.assertRaises(ValueError):upsert([], [bad])
    def test_published_third_party_fact_is_not_a_false_unconfirmed_omission(self):
        r=self.lead();p=dict(candidate(),status="provider_confirmed")
        q=quality({"records":[]},{"programs":[p]},{"records":[]},{},P,NOW,[r])
        out=q["records"][0]
        self.assertTrue(out["publishedExact"]);self.assertTrue(out["datetimeConfirmed"])
        self.assertFalse(out["officialDatetimeConfirmed"])
        self.assertFalse(out["held"]);self.assertFalse(out["omission"])
