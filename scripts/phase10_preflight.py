"""Offline end-to-end handoff check, with no production/cache writes."""
import json,tempfile
from pathlib import Path
from datetime import datetime
from feed import ROOT,read_json,atomic_json,build_feed,validate_public,STATIONS,CH_MAP
from ledger import prepare
from autopublish import integrate_candidates
def main():
    now=datetime.fromisoformat("2026-10-27T17:41:36+09:00")
    expected=read_json(ROOT/"data/phase10-investigation.json")["eligibleIds"]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);atomic_json(root/"data/discovered-candidates.json",read_json(ROOT/"data/discovered-candidates.json",{"records":[]}))
        batch=prepare(read_json(ROOT/"data/ai-candidates.json"),root)
        state,ok,held,_=integrate_candidates([],batch,[],{"rows":[]},read_json(ROOT/"config/source-policy.json"),now)
        assert set(expected)<={x["id"] for x in state},held
        feed,_=build_feed(state,{"rows":[]},now,False);validate_public(feed)
        assert set(expected)<={x["id"] for x in feed["programs"]}
        assert STATIONS["nhk_bsp4k"][1] is None and None not in CH_MAP
        psycho=next(p for p in feed["programs"] if p["id"]=="phase8-psycho-20261031")
        assert set(psycho["genreIds"])=={"movie","horror_movie"}
        print(json.dumps({"webDiscoveredFactsPublishedOffline":len(expected),"manualApprovedModified":False,"bsp4kProviderIdGuessed":False,"schemaVersion":feed["schemaVersion"]}))
if __name__=="__main__":main()
