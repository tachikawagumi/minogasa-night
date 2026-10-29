"""A+B discovery inputs only. No network or title-based genre inference."""
from copy import deepcopy
from feed import canonical, parse_dt, iso, window, GENRE_IDS

VEHICLES={"automobile","motorcycle","truck","bus","special_vehicle","heavy_machinery","motorsport"}
def slot(r):
    if not r.get("start") or not r.get("stationId"): return None
    return (r["stationId"],iso(parse_dt(r["start"])),canonical(r["title"]))

def merge_inputs(base, inputs, prior, public, config):
    if not isinstance(inputs,list) or len(inputs)>2000: raise ValueError("A+B入力の形式・上限")
    rows={}
    for r in base:
        if r["id"] in rows and rows[r["id"]]!=r: raise ValueError("既存台帳の同一IDに矛盾")
        rows[r["id"]]=deepcopy(r)
    accepted=[]
    known={r["id"]:r for r in prior+public}
    identities={slot(r):r for r in prior+public+base if slot(r)}
    audit={"inputCounts":{"A":0,"B":0},"duplicates":0,"held":[],"routesById":{}}
    for envelope in inputs:
        if not isinstance(envelope,dict) or envelope.get("route") not in ("A","B") or not isinstance(envelope.get("record"),dict):
            raise ValueError("A/B経路と共通台帳recordが必要")
        route=envelope["route"];r=deepcopy(envelope["record"]);rid=r.get("id")
        if not rid: raise ValueError("候補IDが必要")
        audit["inputCounts"][route]+=1
        audit["routesById"].setdefault(rid,[])
        if route not in audit["routesById"][rid]: audit["routesById"][rid].append(route)
        reason=None
        if envelope.get("mode")!="individual_reference": reason="個別参照以外の取得方式は未接続"
        if route=="B" and not config.get("B",{}).get("enabled"): reason="B経路は無効"
        if r.get("decision")=="eligible" and (r.get("acquisitionMethod")!="ai_web_reference" or (r.get("factUseReview") or {}).get("bulkAccess") is not False):
            reason="取得方式・大量取得の利用条件が未確認"
        old=known.get(rid)
        same=identities.get(slot(r)) if slot(r) else None
        if old and old.get("seriesId")!=r.get("seriesId"): reason="既存シリーズIDの変更は不可"
        if same and same["id"]!=rid: reason="同一放送枠の既存IDへ合わせ個別審査を再実施する必要"
        if "car" in r.get("genreIds",[]) and r.get("decision")=="eligible":
            v=r.get("classification",{}).get("vehicleEvidence",{})
            if v.get("role")!="central" or v.get("vehicleType") not in VEHICLES or not v.get("basis"):
                reason="車両が主役である当該回の根拠が必要（移動手段だけは対象外）"
        if reason:
            audit["held"].append({"id":rid,"title":r.get("title"),"route":route,"reason":reason})
            continue
        accepted.append(rid)
        existing=rows.get(rid)
        if existing:
            if existing==r:
                audit["duplicates"]+=1;continue
            before=parse_dt(existing["checkedAt"]);after=parse_dt(r["checkedAt"])
            if after<before:
                audit["duplicates"]+=1;continue
            if after==before: raise ValueError("同一ID・確認時刻のA+B候補に矛盾")
        rows[rid]=r;known[rid]=r
        if slot(r): identities[slot(r)]=r
    audit["acceptedInputIds"]=sorted(set(accepted))
    return list(rows.values()),audit

def build_plan(discovery,collection,now):
    start,end=window(now);span=start.strftime("%Y-%m-%d")+"〜"+end.strftime("%Y-%m-%d")+"（末尾日を含まない）"
    if set(discovery["genres"])!=set(GENRE_IDS): raise ValueError("20ジャンルが必要")
    a=[]
    for gid,item in discovery["genres"].items():
        groups=item.get("subcategories",[])
        for group in groups:
            if not group.get("id") or not group.get("keywords"): raise ValueError("内部検索対象が必要")
            a.append({"genreId":gid,"subcategoryId":group["id"],"query":" OR ".join(group["keywords"])+" 番組 放送予定 "+span,"status":"planned"})
    b=[]
    from datetime import timedelta
    for host in collection.get("B",{}).get("queryHosts",[]):
        for offset in (0,6):
            day=(start+timedelta(days=offset)).date().isoformat()
            b.append({"route":"B","query":"site:"+host+" "+day+" 番組 放送予定","mode":"individual_reference","status":"planned"})
    limit=collection.get("B",{}).get("maxStationDateQueries",8)
    return {"A":a,"B":b[:limit] if collection.get("B",{}).get("enabled") else [],
        "execution":"Workの実検索が必要。計画を実行済みと扱わない。キーワードから分類しない。",
        "bulkCollectionEnabled":False,"budgetCapIsNotCompletionCriterion":True}
