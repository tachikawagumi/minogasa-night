import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from source_rules import load_stations,station_error,policy_error,FACT_FIELDS
from feed import ROOT,read_json,STATIONS
from test_autopublish import candidate,apply,P

class SourceRulesTest(unittest.TestCase):
    def reviewed(self):
        c=candidate(acquisitionMethod="ai_web_reference",sourcePolicyId="review")
        p=copy.deepcopy(P)
        p["sources"]["review"]=dict(enabled=True,mode="official_facts",hosts=["official.example.test"],individualFactReviews={"one":{"outcome":"minimal_facts_only","sourceUrl":c["sourceUrl"],"termsUrl":"https://official.example.test/terms","rationale":"Individual factual record; no expression copied"}})
        # Use fixture's actual source host rather than assuming a hostname.
        from urllib.parse import urlparse
        p["sources"]["review"]["hosts"]=[urlparse(c["sourceUrl"]).hostname]
        c["factUseReview"]=dict(reviewId="one",checkedAt=c["checkedAt"],method="ai_web_reference",minimalFactsOnly=True,noContentCopied=True,bulkAccess=False,accountServiceUsed=False,facts={k:c.get(k,"upsert" if k=="operation" else None) for k in FACT_FIELDS})
        return c,p
    def test_independent_fact_not_blanket_content_licence(self):
        c,p=self.reviewed();self.assertIsNone(policy_error(c,p["sources"]["review"]))
        _,ok,held,_=apply([c],policies=p);self.assertEqual(1,len(ok));self.assertFalse(held)
    def test_missing_review_held(self):
        c,p=self.reviewed();c.pop("factUseReview");self.assertIsNotNone(policy_error(c,p["sources"]["review"]))
    def test_changed_time_requires_fresh_fact_check(self):
        c,p=self.reviewed();c["start"]="2026-10-26T19:00:00+09:00";self.assertIsNotNone(policy_error(c,p["sources"]["review"]))
    def test_crawler_or_body_copy_is_not_permitted(self):
        for key,value in [("bulkAccess",True),("noContentCopied",False),("accountServiceUsed",True)]:
            c,p=self.reviewed();c["factUseReview"][key]=value;self.assertIsNotNone(policy_error(c,p["sources"]["review"]))
    def test_same_host_other_page_is_not_reviewed(self):
        c,p=self.reviewed();c["sourceUrl"]+="/other";self.assertIsNotNone(policy_error(c,p["sources"]["review"]))
    def test_unknown_review_is_held(self):
        c,p=self.reviewed();c["factUseReview"]["reviewId"]="unreviewed";self.assertIsNotNone(policy_error(c,p["sources"]["review"]))
    def test_paid_and_streaming_excluded_even_if_free_id_claimed(self):
        for kind in ("paid_cs","paid_bs","streaming","subscription"):
            self.assertIsNotNone(station_error(dict(stationId="bs12",distribution=kind),STATIONS))
    def test_free_airing_of_same_title_is_separately_eligible(self):
        self.assertIsNone(station_error(dict(title="same",stationId="bs12",distribution="free_bs"),STATIONS))
    def test_station_config_rejects_paid_and_unknown_channels(self):
        data=read_json(ROOT/"config/stations.json")
        for change in (dict(distribution="paid_bs"),dict(id="unverified")):
            bad=copy.deepcopy(data);bad["stations"][0].update(change)
            with tempfile.TemporaryDirectory() as td:
                path=Path(td)/"stations.json";path.write_text(json.dumps(bad),encoding="utf-8")
                with self.assertRaises(ValueError): load_stations(path,STATIONS)
    def test_all_genres_have_sources_and_five_search_methods(self):
        d=read_json(ROOT/"config/discovery.json");self.assertEqual(20,len(d["genres"]))
        for g in d["genres"].values():
            self.assertTrue(g["sourceIds"]);self.assertEqual(5,len(g["searchMethods"]))
            self.assertTrue(all(s in d["sourceCatalog"] for s in g["sourceIds"]))
