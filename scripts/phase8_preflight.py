"""Offline integration check: never writes production cache/public files."""
import json,tempfile
from pathlib import Path
from datetime import datetime
from feed import ROOT,read_json,atomic_json
from ledger import prepare
from autopublish import integrate_candidates
def main():
    now=datetime.fromisoformat("2026-10-27T13:16:00+09:00")
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        atomic_json(root/"data/discovered-candidates.json",read_json(ROOT/"data/discovered-candidates.json",{"records":[]}))
        b=prepare(read_json(ROOT/"data/ai-candidates.json"),root)
        cache=read_json(ROOT/"data/anime-cache.json",{"rows":[]})
        previous=read_json(ROOT/"data/current-db.json",{"records":[]})["records"]
        state,ok,held,cancel=integrate_candidates([],b,previous,cache,read_json(ROOT/"config/source-policy.json"),now)
        wanted={c["id"] for c in b["records"] if c.get("sourcePolicyId")=="reviewed_independent_facts"}
        assert len(wanted)==6,wanted
        assert wanted <= {r["id"] for r in state},[(h.get("candidate"),h.get("reason")) for h in held]
        g=next(r for r in state if r["id"]=="official-bs12-20261101-1900-genma")
        assert g["end"] is None and set(g["genreIds"])=={"movie","anime"}
        assert len({r["id"] for r in state})==len(state)
        print(json.dumps({"reviewedFactsAccepted":len(wanted),"stableIds":True,"unknownEndPreserved":True,"writesProductionData":False},ensure_ascii=False))
if __name__=="__main__":main()
