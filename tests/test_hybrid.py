import copy,json,sys,unittest
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from hybrid import merge_inputs,build_plan
from feed import read_json,GENRE_IDS
from ledger import project
from autopublish import integrate_candidates,protect_last_good,PublicationBlocked

class HybridTests(unittest.TestCase):
    def setUp(self):
        self.inputs=read_json(ROOT/"docs/phase15/verified-inputs.json")["inputs"]
        self.config=read_json(ROOT/"config/collection.json")
        self.now=datetime.fromisoformat(read_json(ROOT/"docs/phase15/verified-inputs.json")["checkedAt"])
    def merge(self,inputs,base=None,prior=None,public=None):
        return merge_inputs(base or [],inputs,prior or [],public or [],self.config)
    def test_all_twenty_and_motorcycle_truck_search_targets(self):
        p=build_plan(read_json(ROOT/"config/discovery.json"),self.config,self.now)
        self.assertEqual(set(GENRE_IDS),{r["genreId"] for r in p["A"]})
        self.assertEqual(71,len(p["A"]))
        car=[r for r in p["A"] if r["genreId"]=="car"]
        self.assertTrue(any("バイク" in r["query"] for r in car))
        self.assertTrue(any("トラック" in r["query"] for r in car))
        self.assertTrue(all(r["status"]=="planned" for r in p["A"]+p["B"]))
        self.assertFalse(p["bulkCollectionEnabled"])
    def test_actual_eleven_pass_existing_publication_validator(self):
        rows,audit=self.merge(self.inputs)
        self.assertEqual({"A":2,"B":9},audit["inputCounts"])
        projected=[project(r) for r in rows]
        accepted,updates,held,cancelled=integrate_candidates([],{"records":projected},[],{"rows":[]},
            read_json(ROOT/"config/source-policy.json"),self.now)
        self.assertEqual(11,len(accepted));self.assertEqual(11,len(updates));self.assertEqual([],held)
        self.assertTrue(all(r["publicationApproved"] for r in accepted))
    def test_same_airing_found_by_both_routes_is_single(self):
        x=copy.deepcopy(self.inputs[0]);y=copy.deepcopy(x);y["route"]="A"
        rows,audit=self.merge([x,y]);self.assertEqual(1,len(rows));self.assertEqual(1,audit["duplicates"])
        self.assertEqual({"A","B"},set(audit["routesById"][x["record"]["id"]]))
    def test_car_and_travel_are_supported_together(self):
        x=next(i for i in self.inputs if "degawacharging" in i["record"]["id"])
        self.assertEqual({"car","travel"},set(self.merge([x])[0][0]["genreIds"]))
    def test_bike_and_truck_are_valid_vehicle_types(self):
        for vehicle in ("motorcycle","truck"):
            x=copy.deepcopy(next(i for i in self.inputs if i["route"]=="A"))
            x["record"]["classification"]["vehicleEvidence"]["vehicleType"]=vehicle
            self.assertEqual(1,len(self.merge([x])[0]))
    def test_incidental_vehicle_or_keyword_is_not_car(self):
        x=copy.deepcopy(next(i for i in self.inputs if i["route"]=="A"))
        x["record"]["classification"]["vehicleEvidence"]["role"]="transport_only"
        rows,audit=self.merge([x]);self.assertEqual([],rows);self.assertEqual(1,len(audit["held"]))
    def test_existing_series_id_is_preserved(self):
        x=copy.deepcopy(self.inputs[0]);old=copy.deepcopy(x["record"]);x["record"]["seriesId"]="wrong"
        rows,audit=self.merge([x],public=[old])
        self.assertEqual([],rows);self.assertEqual([],audit["acceptedInputIds"])
    def test_alternate_id_requires_fresh_fact_review_not_silent_rekey(self):
        x=copy.deepcopy(self.inputs[0]);old=copy.deepcopy(x["record"]);old["id"]="favorite-id"
        rows,audit=self.merge([x],public=[old]);self.assertEqual([],rows);self.assertEqual(1,len(audit["held"]))
    def test_contradictory_same_time_input_blocks(self):
        x=copy.deepcopy(self.inputs[0]);y=copy.deepcopy(x);y["record"]["title"]="矛盾"
        with self.assertRaises(ValueError): self.merge([x,y])
    def test_base_conflicts_still_block(self):
        x=copy.deepcopy(self.inputs[0]["record"]);y=copy.deepcopy(x);y["title"]="矛盾"
        with self.assertRaises(ValueError): self.merge([],base=[x,y])
    def test_no_bulk_or_unreviewed_acquisition(self):
        x=copy.deepcopy(self.inputs[0]);x["mode"]="bulk_scraper"
        self.assertEqual([],self.merge([x])[0])
    def test_unknown_source_remains_held_by_original_validator(self):
        x=copy.deepcopy(self.inputs[0]);x["record"]["sourcePolicyId"]="unknown"
        rows,_=self.merge([x])
        _,accepted,held,_=integrate_candidates([],{"records":[project(rows[0])]},[],{"rows":[]},
            read_json(ROOT/"config/source-policy.json"),self.now)
        self.assertEqual([],accepted);self.assertEqual(1,len(held))
    def test_missing_verification_not_projected(self):
        x=copy.deepcopy(self.inputs[0]);x["record"]["officialVerification"]["datetime"]=False
        self.assertIsNone(project(self.merge([x])[0][0]))
    def test_large_loss_guard_is_not_bypassed(self):
        previous=read_json(ROOT/"public/v1/programs.json");empty=copy.deepcopy(previous);empty["programs"]=[]
        with self.assertRaises(PublicationBlocked): protect_last_good(previous,empty,self.now)
