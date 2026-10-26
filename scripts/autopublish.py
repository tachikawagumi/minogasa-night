"""Conditional AI publication with provenance, diff and last-good protection."""
from __future__ import annotations
import json, sys
from urllib.parse import urlparse
from datetime import datetime, timedelta
from feed import ROOT, JST, GENRE_IDS, STATIONS, Syobocal, read_json, atomic_json, parse_dt, iso, canonical, merge_rows, build_feed, validate_public, window

class PublicationBlocked(ValueError): pass

def host_allowed(url, policy):
    return urlparse(url).scheme == "https" and urlparse(url).hostname in policy.get("hosts", [])

def public_diff(previous, proposed, now):
    old = {x["id"]: x for x in previous.get("programs", [])}
    new = {x["id"]: x for x in proposed.get("programs", [])}
    future = {k for k,v in old.items() if parse_dt(v["start"]) > now}
    return dict(added=sorted(new.keys()-old.keys()), scheduleChanged=sorted(k for k in old.keys() & new.keys() if any(old[k].get(f)!=new[k].get(f) for f in ("title","stationId","start","end"))), genreChanged=sorted(k for k in old.keys() & new.keys() if set(old[k]["genreIds"])!=set(new[k]["genreIds"])), removed=sorted(future-new.keys()), expired=sorted((old.keys()-new.keys())-future))

def protect_last_good(previous, proposed, now, cancelled=()):
    validate_public(proposed)
    diff = public_diff(previous, proposed, now)
    future = [x for x in previous.get("programs", []) if parse_dt(x["start"]) > now]
    if future and not proposed["programs"]:
        raise PublicationBlocked("全件消失を検知。正常な公開JSONを保持")
    unexpected = set(diff["removed"]) - set(cancelled)
    if len(unexpected)>=10 and len(unexpected)/max(1,len(future))>0.35:
        raise PublicationBlocked("将来枠が35%超かつ10件以上消失。公開を保留")
    # A source disappearing completely can hide inside an otherwise healthy total.
    for station in STATIONS:
        ids={x["id"] for x in future if x["stationId"]==station}
        if len(ids)>=10 and len(ids & unexpected)/len(ids)>0.5:
            raise PublicationBlocked("局別の大量消失を検知: "+station)
    return diff

def integrate_candidates(existing, batch, previous_rows, provider, policies, now):
    if not isinstance(batch,dict) or not isinstance(batch.get("records",[]),list):
        raise PublicationBlocked("AI候補バッチの形式が不正")
    if len(batch.get("records",[]))>1000: raise PublicationBlocked("AI候補が上限超過")
    fresh={x["sourcePid"]:x for x in provider.get("rows",[])}
    state={x["id"]:dict(x) for x in existing if x.get("origin")!="syobocal" or x.get("sourcePid") in fresh}
    known={x["id"]:dict(x) for x in previous_rows}
    known.update(state)
    accepted,held,cancelled=[],[],[]
    seen={}
    conflicts=set()
    for item in batch.get("records",[]):
        if isinstance(item,dict) and item.get("id"):
            key=item["id"]
            if key in seen and seen[key]!=item: conflicts.add(key)
            seen[key]=item
    seen={}
    _,finish=window(now)
    for candidate in batch.get("records",[]):
        try:
            if not isinstance(candidate,dict): raise ValueError("候補がオブジェクトでない")
            c=dict(candidate)
            if c.get("id") in conflicts: raise ValueError("同一IDに矛盾する複数候補")
            if any(k in c for k in ("description","cast","image","token","apiKey")): raise ValueError("不要な本文・秘密情報")
            for k in ("id","seriesId","title","stationId","sourceUrl","checkedAt","updatedAt","sourcePolicyId"):
                if not isinstance(c.get(k),str) or not c[k].strip(): raise ValueError("必須項目不足: "+k)
            if c["id"] in seen and seen[c["id"]]!=c: raise ValueError("同一IDに矛盾する複数候補")
            seen[c["id"]]=c
            policy=policies.get("sources",{}).get(c["sourcePolicyId"],{})
            scopes=set(policy.get("permissions",[]))
            if not policy.get("enabled") or not {"metadata","cache","redistribute","automated_access"} <= scopes:
                raise ValueError("情報源の取得・再配信条件が未確認")
            if not host_allowed(c["sourceUrl"],policy): raise ValueError("出典URLが情報源ポリシーと不一致")
            checked=parse_dt(c["checkedAt"])
            if not now-timedelta(hours=96)<=checked<=now+timedelta(minutes=5): raise ValueError("確認時刻が古い／未来")
            if c["stationId"] not in STATIONS: raise ValueError("対象外局")
            operation=c.get("operation","upsert")
            if policy.get("mode")=="provider_match":
                pid=str(c.get("sourcePid",""))
                if operation=="cancel":
                    if pid not in provider.get("deletedPids",[]): raise ValueError("提供元で中止未確認")
                    rid="syobocal-"+pid
                    state.pop(rid,None);cancelled.append(rid)
                    accepted.append({"id":rid,"operation":"cancel"})
                    continue
                p=fresh.get(pid)
                if not p: raise ValueError("現在の許諾済み提供元に該当枠がない")
                if c["stationId"]!=p["stationId"] or parse_dt(c["start"])!=parse_dt(p["start"]) or canonical(p["title"]) not in canonical(c["title"]):
                    raise ValueError("提供元と局・日時・番組名が不一致")
                if c.get("genreIds")!=["anime"]: raise ValueError("提供元の根拠で確認できない追加分類")
                row=dict(p)
                official=c.get("officialVerificationUrl")
                if official:
                    if urlparse(official).scheme!="https" or urlparse(official).hostname not in policy.get("officialVerificationHosts",[]): raise ValueError("公式照合URL不正")
                    row["officialVerificationUrl"]=official
                row["aiCheckedAt"]=c["checkedAt"]
                row["sourcePolicyId"]=c["sourcePolicyId"]
            elif policy.get("mode")=="official_facts":
                if c.get("status")!="official_confirmed" or not c.get("officialVerified"):
                    raise ValueError("公式照合が未完了")
                if operation=="cancel":
                    old=known.get(c["id"])
                    if not old or not c.get("cancellationConfirmed"): raise ValueError("中止根拠または既存枠がない")
                    state.pop(c["id"],None);cancelled.append(c["id"])
                    accepted.append({"id":c["id"],"operation":"cancel"})
                    continue
                tags=c.get("genreIds",[])
                evidence=c.get("genreEvidence",{})
                if not tags or not set(tags)<=set(GENRE_IDS) or not all(isinstance(evidence.get(g),str) and evidence[g].strip() for g in tags): raise ValueError("ジャンル根拠不足")
                if not now<parse_dt(c["start"])<finish: raise ValueError("過去または7日間の対象外")
                old=known.get(c["id"])
                if old and checked<parse_dt(old["checkedAt"]): raise ValueError("既存より古い情報")
                slot=[x for x in known.values() if x["stationId"]==c["stationId"] and parse_dt(x["start"])==parse_dt(c["start"])]
                same=next((x for x in slot if canonical(x["title"])==canonical(c["title"])),None)
                if any(x["id"]!=c["id"] and canonical(x["title"])!=canonical(c["title"]) for x in slot): raise ValueError("同一局・時刻に矛盾する番組")
                row={k:c.get(k) for k in ("id","seriesId","title","stationId","start","end","genreIds","sourceUrl","checkedAt","updatedAt","genreEvidence")}
                if same: row["id"],row["seriesId"]=same["id"],same["seriesId"]
                elif old: row["seriesId"]=old["seriesId"]
                row.update(status="official_confirmed",publicationApproved=True,origin="ai_official_facts",sourcePolicyId=c["sourcePolicyId"])
                merge_rows([row],now)
            else: raise ValueError("未対応の情報源ポリシー")
            if not now<parse_dt(row["start"])<finish: raise ValueError("対象期間外")
            state[row["id"]]=row;known[row["id"]]=row
            accepted.append({"id":row["id"],"operation":"upsert"})
        except (ValueError,KeyError,TypeError) as exc:
            safe={k:candidate.get(k) for k in ("id","title","stationId","start","genreIds","sourceUrl","sourcePolicyId")} if isinstance(candidate,dict) else {}
            held.append(dict(candidate=safe,reason=str(exc)))
    # Cancelling legacy rows is represented separately and never inferred from omission.
    return list(state.values()), accepted, held, cancelled

def record_result(result):
    atomic_json(ROOT/"data/update-result.json",result)
    history=read_json(ROOT/"data/update-history.json",[])
    atomic_json(ROOT/"data/update-history.json",(history+[result])[-50:])

def run(now=None, collector=None):
    now=now or datetime.now(JST)
    previous=read_json(ROOT/"public/v1/programs.json",{})
    previous_rows=read_json(ROOT/"data/current-db.json",{"records":[]})["records"]
    cache=read_json(ROOT/"data/anime-cache.json",{"rows":[]})
    try:
        # Nothing is persisted until source acquisition, integration and guard checks pass.
        provider=(collector or Syobocal()).collect(now,cache)
        merge_rows(provider["rows"],now)
        cached_future={x["id"] for x in cache.get("rows",[]) if parse_dt(x["start"])>now}
        fresh_ids={x["id"] for x in provider["rows"]}
        deleted={"syobocal-"+str(x) for x in provider.get("deletedPids",[])}
        lost=cached_future-fresh_ids-deleted
        if (cached_future and not provider["rows"] and lost) or (len(lost)>=10 and len(lost)/len(cached_future)>0.35):
            raise PublicationBlocked("アニメ提供元の大量消失を検知。キャッシュと公開JSONを保持")
        policies=read_json(ROOT/"config/source-policy.json",{"sources":{}})
        batch=read_json(ROOT/"data/ai-candidates.json",{"records":[]})
        existing=read_json(ROOT/"data/ai-state.json",{"records":[]})["records"]
        auto,accepted,held,cancelled=integrate_candidates(existing,batch,previous_rows,provider,policies,now)
        legacy=read_json(ROOT/"data/manual-approved.json",{"records":[]})["records"]
        # AI updates and cancellations supersede legacy records by stable ID.
        overrides={x["id"] for x in auto}|set(cancelled)
        legacy=[x for x in legacy if x["id"] not in overrides]
        feed,internal=build_feed(legacy+auto,provider,now,True)
        diff=protect_last_good(previous,feed,now,cancelled)
        # Stage-safe files only. Git commit and Pages deployment remain separate, atomic actions.
        atomic_json(ROOT/"data/anime-cache.json",provider)
        atomic_json(ROOT/"data/ai-state.json",{"checkedAt":iso(now),"records":auto})
        atomic_json(ROOT/"data/ai-held.json",{"checkedAt":iso(now),"batchId":batch.get("batchId"),"records":held})
        atomic_json(ROOT/"data/current-db.json",{"generatedAt":iso(now),"records":internal})
        atomic_json(ROOT/"public/v1/programs.json",feed)
        result={"at":iso(now),"status":"prepared","animeSuccess":True,"publicPrograms":len(feed["programs"]),"aiAccepted":len(accepted),"aiHeld":len(held),"batchId":batch.get("batchId"),"diff":diff,"counts":{k:len(v) for k,v in diff.items()},"publicationVerified":False}
        record_result(result)
        print(json.dumps(result,ensure_ascii=False))
        return result
    except Exception as exc:
        result={"at":iso(now),"status":"failed","publicationVerified":False,"error":type(exc).__name__+": "+str(exc)[:350],"previousPublicPreserved":True}
        record_result(result)
        print(json.dumps(result,ensure_ascii=False))
        raise

if __name__=="__main__":
    try: run()
    except Exception: sys.exit(1)
