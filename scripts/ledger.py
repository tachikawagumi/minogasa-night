"""Pre-publication discovery ledger. Keeps unverified claims separate from facts."""
from datetime import datetime, timedelta
from urllib.parse import urlparse
from feed import ROOT,JST,GENRE_IDS,STATIONS,canonical,parse_dt,iso,read_json,atomic_json

FIELDS={"id","seriesId","title","stationId","claimedStation","claimedStart","claimedEnd","start","end","genreIds","candidateGenreIds","sourceUrl","sourceUrls","discoveredAt","checkedAt","lastAttemptAt","officialVerification","classification","decision","holdReasons","sourcePolicyId","genreEvidence","acquisitionMethod","origin"}
LEVELS={"clear","related","excluded"}

def valid_url(url):
    p=urlparse(url)
    return p.scheme=="https" and bool(p.hostname) and p.username is None and p.password is None and not p.query

def upsert(previous,incoming):
    if not isinstance(incoming,list) or len(incoming)>2000: raise ValueError("候補台帳の形式・上限")
    rows={r["id"]:dict(r) for r in previous}
    seen={}
    for item in incoming:
        if not isinstance(item,dict) or not isinstance(item.get("id"),str) or not item["id"]: raise ValueError("候補ID不足")
        if any(k not in FIELDS for k in item): raise ValueError("台帳に不要な本文・未知項目")
        if not isinstance(item.get("title"),str) or not item["title"].strip(): raise ValueError("候補名不足")
        if item["id"] in seen and seen[item["id"]]!=item: raise ValueError("同一台帳IDに矛盾")
        seen[item["id"]]=item
        for u in item.get("sourceUrls",[])+([item["sourceUrl"]] if item.get("sourceUrl") else []):
            if not valid_url(u): raise ValueError("台帳出典URL不正")
        for key in ("genreIds","candidateGenreIds"):
            if not set(item.get(key,[]))<=set(GENRE_IDS): raise ValueError("台帳ジャンル不正")
        classification=item.get("classification",{})
        if classification.get("level") not in LEVELS or not classification.get("basis"): raise ValueError("3段階分類と根拠が必要")
        verify=item.get("officialVerification",{})
        if (item.get("start") or item.get("end")) and not verify.get("datetime"): raise ValueError("未確認日時はclaimedStart/Endだけに保存")
        if verify.get("datetime"): parse_dt(item.get("start"))
        for k in ("discoveredAt","checkedAt","lastAttemptAt"):
            if item.get(k): parse_dt(item[k])
        old=rows.get(item["id"])
        if old and old.get("checkedAt") and item.get("checkedAt") and parse_dt(item["checkedAt"])<parse_dt(old["checkedAt"]):
            continue
        row=dict(item)
        if old: row["discoveredAt"]=old.get("discoveredAt",item.get("discoveredAt"))
        rows[item["id"]]=row
    return list(rows.values())

def project(record):
    v=record.get("officialVerification",{})
    if record.get("decision")!="eligible" or record.get("classification",{}).get("level")!="clear":
        return None
    if not all(v.get(k) for k in ("title","station","datetime","content")) or not v.get("sourceUrl"):
        return None
    if record.get("stationId") not in STATIONS or not record.get("genreIds"): return None
    parse_dt(record["start"])
    if v["sourceUrl"] not in record.get("sourceUrls",[]): return None
    keys=("id","seriesId","title","stationId","start","end","genreIds","checkedAt","sourcePolicyId","genreEvidence","acquisitionMethod")
    c={k:record.get(k) for k in keys}
    c.update(sourceUrl=v["sourceUrl"],status="official_confirmed",officialVerified=True,updatedAt=record["checkedAt"],publicationApproved=False,operation="upsert")
    return c

def ready_for_research(record,now,hours=48):
    last=record.get("lastAttemptAt") or record.get("checkedAt")
    return not last or parse_dt(last)+timedelta(hours=hours)<=now

def prepare(batch,root=None):
    root=root or ROOT
    previous=read_json(root/"data/discovered-candidates.json",{"records":[]})
    rows=upsert(previous.get("records",[]),batch.get("discoveries",[]))
    # Persist every discovery before any source/API acquisition or publication decision.
    atomic_json(root/"data/discovered-candidates.json",dict(checkedAt=iso(datetime.now(JST)),records=rows))
    projected=[c for r in rows if (c:=project(r)) is not None]
    current=list(batch.get("records",[]))
    by_id={c["id"]:c for c in current}
    for c in projected:
        if c["id"] in by_id and by_id[c["id"]]!=c:
            # An existing explicit candidate wins. Never silently resolve contradictory data.
            raise ValueError("台帳と公開候補の同一IDが矛盾")
        by_id[c["id"]]=c
    return dict(batch,records=list(by_id.values()))
