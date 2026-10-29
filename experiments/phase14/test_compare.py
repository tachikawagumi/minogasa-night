import copy, tempfile, unittest
from pathlib import Path
import compare as c
class ShadowExperimentTests(unittest.TestCase):
    def setUp(self):
        self.a=c.read("baseline-a.json");self.sources=c.read("source-feasibility.json")["sources"]
        self.obs=c.read("observations-b.json")["observations"]
        self.ann=c.read("classifications.json")["annotations"]
    def unify(self,rows,mode="individual_reference"):
        return c.unify(rows,self.a,self.sources,mode)
    def test_twenty_genres_and_no_production_handoff(self):
        v=c.compare(self.a,self.obs,self.ann,self.sources,c.read("reference-checklist.json"),c.read("regular-reference.json"))
        self.assertEqual(20,len(v["genreCoverage"]));self.assertFalse(v["productionHandoffEnabled"])
        self.assertEqual(25,v["bObserved"]);self.assertEqual(22,v["bFactsConfirmed"])
        self.assertEqual(11,v["bClassified"]);self.assertEqual(3,v["bHeld"])
    def test_duplicate_alias_width_and_whitespace_reuses_existing_id(self):
        r=copy.deepcopy(next(x for x in self.obs if x["observationId"]=="B-genki"))
        d=copy.deepcopy(r);d["observationId"]="duplicate";d["title"]="健康カプセル！ ゲンキの時間"
        result,held=self.unify([r,d]);self.assertEqual([],held);self.assertEqual(1,len(result))
        self.assertEqual("official-ce810c015779acc089ba403a",result[0]["id"])
    def test_distinct_station_and_date_are_not_merged(self):
        a=copy.deepcopy(self.obs[1]);b=copy.deepcopy(a);b.update(observationId="other-station",stationId="bstvtokyo")
        d=copy.deepcopy(a);d.update(observationId="other-date",start="2026-11-03T21:00:00+09:00",end="2026-11-03T21:54:00+09:00")
        rows,held=self.unify([a,b,d]);self.assertEqual(3,len(rows));self.assertEqual([],held)
    def test_conflicting_titles_quarantine_both(self):
        a=copy.deepcopy(self.obs[0]);b=copy.deepcopy(a);b.update(title="矛盾する番組",observationId="conflict")
        rows,held=self.unify([a,b]);self.assertEqual([],rows);self.assertEqual(2,len(held))
    def test_conflicting_end_times_quarantine_both(self):
        a=copy.deepcopy(self.obs[0]);b=copy.deepcopy(a);b.update(end="2026-11-02T22:00:00+09:00",observationId="conflict")
        self.assertEqual(2,len(self.unify([a,b])[1]))
    def test_missing_end_is_allowed_without_guessing(self):
        a=copy.deepcopy(self.obs[0]);a["end"]=None
        self.assertIsNone(self.unify([a])[0][0]["end"])
    def test_outside_window_and_naive_time_are_held(self):
        for value in ("2026-11-05T21:00:00+09:00","2026-11-02T21:00:00"):
            a=copy.deepcopy(self.obs[0]);a["start"]=value
            self.assertEqual(1,len(self.unify([a])[1]))
    def test_unverified_midnight_date_not_inferred(self):
        self.assertEqual([],self.unify([self.obs[-2]])[0])
    def test_unmapped_subchannel_not_converted(self):
        self.assertEqual([],self.unify([self.obs[-1]])[0])
    def test_automated_mode_rejects_unlicensed_sources(self):
        rows,held=self.unify(self.obs,"automated")
        self.assertEqual([],rows);self.assertEqual(25,len(held))
    def test_title_only_annotation_does_not_classify(self):
        rows,_=self.unify([self.obs[0]]);ann=copy.deepcopy(self.ann[:1]);ann[0]["derivedFromTitleOnly"]=True
        self.assertEqual("pending",c.classify(rows,ann,[g["id"] for g in self.a["genres"]])[0]["classificationStatus"])
    def test_unrelated_content_source_cannot_classify(self):
        rows,_=self.unify([self.obs[0]]);ann=copy.deepcopy(self.ann[:1]);ann[0]["contentSourceUrls"]=["https://example.com/"]
        self.assertEqual([],c.classify(rows,ann,[g["id"] for g in self.a["genres"]])[0]["genreIds"])
    def test_no_annotations_does_not_copy_title_genres(self):
        rows,_=self.unify([next(r for r in self.obs if r["observationId"]=="B-genki")])
        self.assertEqual([],c.classify(rows,[],[g["id"] for g in self.a["genres"]])[0]["genreIds"])
    def test_unexpected_copied_body_rejected(self):
        a=copy.deepcopy(self.obs[0]);a["description"]="not allowed"
        self.assertEqual([],self.unify([a])[0])
    def test_output_cannot_overwrite_active_feed(self):
        with self.assertRaises(ValueError): c.write_output(c.ROOT.parents[1]/"public/v1/programs.json",{})
    def test_source_id_cannot_launder_an_unreviewed_url(self):
        a=copy.deepcopy(self.obs[0]);a["sourceUrl"]="https://example.com/"
        self.assertEqual([],self.unify([a])[0])
    def test_conflict_with_existing_slot_is_held_not_replaced(self):
        a=copy.deepcopy(next(r for r in self.obs if r["observationId"]=="B-genki"))
        a["title"]="別番組"
        self.assertEqual([],self.unify([a])[0])
    def test_source_station_mismatch_is_held(self):
        a=copy.deepcopy(self.obs[0]);a["stationId"]="tvtokyo"
        self.assertEqual([],self.unify([a])[0])
    def test_24_hour_end_is_explicit_next_calendar_day(self):
        a=next(r for r in self.obs if r["observationId"]=="B-money")
        self.assertEqual("2026-11-04T00:01:00+09:00",a["end"])
if __name__=="__main__": unittest.main()
