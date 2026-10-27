import copy,sys,unittest
from pathlib import Path
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from test_autopublish import candidate,apply,P
from test_feed import NOW
from source_rules import FACT_FIELDS
from ledger import project
from discovery import quality

class SchedulePublicationTest(unittest.TestCase):
    def setup_case(self):
        c=candidate(status="provider_confirmed",officialVerified=False,sourcePolicyId="schedule",acquisitionMethod="ai_web_reference")
        c["scheduleVerification"]=dict(title=True,station=True,datetime=True,content=True,sourceUrl=c["sourceUrl"])
        c["factUseReview"]=dict(reviewId="one",checkedAt=c["checkedAt"],method="ai_web_reference",minimalFactsOnly=True,noContentCopied=True,bulkAccess=False,accountServiceUsed=False,facts={k:c.get(k,"upsert" if k=="operation" else None) for k in FACT_FIELDS})
        policy=dict(enabled=True,mode="schedule_facts",hosts=[urlparse(c["sourceUrl"]).hostname],allowedUrls=[c["sourceUrl"]],individualFactReviews={"one":dict(sourceUrl=c["sourceUrl"],outcome="minimal_facts_only",verificationKind="third_party_schedule",termsUrl=c["sourceUrl"],rationale="個別の最小事実を独立確認")})
        p=copy.deepcopy(P);p["sources"]["schedule"]=policy
        return c,p
    def lead(self,c):
        keys=("id","seriesId","title","stationId","start","end","genreIds","sourceUrl","checkedAt","sourcePolicyId","genreEvidence","acquisitionMethod","factUseReview","scheduleVerification")
        r={k:c[k] for k in keys}
        r.update(sourceUrls=[c["sourceUrl"]],decision="eligible",classification={"level":"clear","basis":"当該回内容を確認"},officialVerification={})
        return r
    def test_verified_schedule_reaches_publisher_without_false_official_claim(self):
        c,p=self.setup_case();state,ok,held,_=apply([c],policies=p)
        self.assertEqual(1,len(ok));self.assertFalse(held)
        self.assertEqual("provider_confirmed",state[0]["status"]);self.assertEqual("ai_schedule_facts",state[0]["origin"])
        self.assertEqual(c["id"],state[0]["id"]);self.assertEqual(c["seriesId"],state[0]["seriesId"])
    def test_incomplete_schedule_does_not_publish(self):
        c,p=self.setup_case();c["scheduleVerification"]["datetime"]=False
        _,ok,held,_=apply([c],policies=p);self.assertFalse(ok);self.assertTrue(held)
    def test_schedule_cannot_claim_official_verification(self):
        c,p=self.setup_case();c["officialVerified"]=True
        _,ok,held,_=apply([c],policies=p);self.assertFalse(ok);self.assertTrue(held)
    def test_scope_review_is_required_even_with_legacy_permission_flags(self):
        c,p=self.setup_case();p["sources"]["schedule"].pop("individualFactReviews");p["sources"]["schedule"]["permissions"]=["metadata","cache","redistribute","automated_access"]
        _,ok,held,_=apply([c],policies=p);self.assertFalse(ok);self.assertTrue(held)
    def test_genre_proof_remains_required(self):
        c,p=self.setup_case();c["genreEvidence"]={}
        _,ok,held,_=apply([c],policies=p);self.assertFalse(ok);self.assertTrue(held)
    def test_eligible_ledger_schedule_projects_as_provider_confirmed(self):
        c,p=self.setup_case();out=project(self.lead(c))
        self.assertIsNotNone(out);self.assertEqual("provider_confirmed",out["status"]);self.assertIs(out["officialVerified"],False)
        _,ok,held,_=apply([out],policies=p);self.assertEqual(1,len(ok));self.assertFalse(held)
    def test_schedule_handoff_omission_is_detected(self):
        c,p=self.setup_case();r=self.lead(c)
        q=quality({"records":[]},{"programs":[]},{"records":[]},{},p,NOW,[r])
        self.assertTrue(q["records"][0]["omission"]);self.assertEqual(1,q["pipelineErrors"])
