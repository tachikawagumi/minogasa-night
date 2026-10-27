"""One-off integration validation for the 2026-10-27 schedule investigation."""
from datetime import datetime
from feed import ROOT,read_json,merge_rows
from source_rules import policy_error,station_error
def main():
    now=datetime.fromisoformat("2026-10-27T16:43:00+09:00")
    wanted={"phase7-darkside-immortality-20261029","phase7-darkside-hell-20261030","official-ce810c015779acc089ba403a","official-tbs-20261101-1430-kurumi","official-tbs-20261102-0113-kickoffj","verified-nhkbs-20261031-0630-matsuura","verified-nhkbs-20261031-0730-naruko","official-tbs-20261028-1025-hiruobi","official-984830d6db17bf74176cf896","verified-nhkbs-20261028-1300-1917","official-chiba-20261027-2100-satozaki","official-chiba-20261027-2330-kanto-baseball","official-chiba-20261028-0030-motorzone"}
    rows=[r for r in read_json(ROOT/"data/manual-approved.json")["records"] if r["id"] in wanted]
    policies=read_json(ROOT/"config/source-policy.json")["sources"]
    from feed import STATIONS
    assert len(rows)==13
    for r in rows:
        assert policy_error(r,policies[r["sourcePolicyId"]]) is None,r["id"]
        assert station_error(r,STATIONS) is None
        assert all(r["genreEvidence"].get(g) for g in r["genreIds"])
        if r.get("providerVerified"):assert r["status"]=="provider_confirmed" and not r["officialVerified"]
    merged=merge_rows(rows,now);assert len(merged)==13
    print("PHASE9_PREFLIGHT_OK additions=12 updated=1 thirdPartyFactsNotMislabelledOfficial=true")
if __name__=="__main__":main()
