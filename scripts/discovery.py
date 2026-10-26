"""Search planning and omission audit. No search API credentials or scraper.
A tool-enabled AI executes planned queries; Actions only audits supplied evidence.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timedelta
from feed import ROOT, JST, GENRE_IDS, GENRES, STATIONS, read_json, atomic_json, parse_dt, iso, window, canonical

REASONS = {
 "datetime_unconfirmed":"放送日時が確認できない", "station_unconfirmed":"放送局が確認できない",
 "genre_uncertain":"ジャンル分類が不明", "terms_unconfirmed":"情報源の利用条件が未確認",
 "duplicate":"重複している", "outside_window":"対象期間外", "other":"その他"
}

def plan(config, now):
    start, end = window(now)
    if set(config["genres"]) != set(GENRE_IDS):
        raise ValueError("20ジャンルの設定が必要")
    result = []
    for g, label in zip(GENRE_IDS, GENRES):
        item = config["genres"][g]
        span = start.strftime("%Y年%m月%d日")+" "+(end-timedelta(days=1)).strftime("%Y年%m月%d日")
        domains = " OR ".join("site:"+x for x in item["officialHosts"])
        for route, terms in (("program_name",item["programs"]),("genre",item["keywords"])):
            result.append(dict(genreId=g,route=route,query=" OR ".join(terms)+" 放送予定 "+span+" ("+domains+")"))
        result.append(dict(genreId=g,route="official_schedule",urls=item["officialScheduleUrls"]))
        result.append(dict(genreId=g,route="miss_learning",features=item.get("learning",{}).get("missFeatures",[]),recheckAfterHours=item.get("learning",{}).get("recheckAfterHours",48)))
    return dict(windowStart=iso(start),windowEnd=iso(end),queries=result,
                execution="AI connected web search only; GitHub Actions does not execute web search")

def issues(c, policies, now):
    found=[]
    try:
        dt=parse_dt(c.get("start")); begin,end=window(now)
        if not now < dt < end: found.append("outside_window")
    except (ValueError,TypeError): found.append("datetime_unconfirmed")
    if c.get("stationId") not in STATIONS: found.append("station_unconfirmed")
    tags=c.get("genreIds",[])
    evidence=c.get("genreEvidence",{})
    if not isinstance(tags,list) or not tags or not set(tags)<=set(GENRE_IDS) or not all(evidence.get(g) for g in tags):
        found.append("genre_uncertain")
    p=policies.get("sources",{}).get(c.get("sourcePolicyId"),{})
    if not p.get("enabled") or not {"metadata","cache","redistribute","automated_access"}<=set(p.get("permissions",[])):
        found.append("terms_unconfirmed")
    return found

def matching(c, programs):
    by_id=next((p for p in programs if p.get("id")==c.get("id")),None)
    by_slot=next((p for p in programs if p.get("stationId")==c.get("stationId") and p.get("start")==c.get("start") and canonical(p.get("title",""))==canonical(c.get("title",""))),None)
    p=by_id or by_slot
    if not p: return None,False
    exact=all(p.get(k)==c.get(k) for k in ("stationId","start")) and canonical(p.get("title",""))==canonical(c.get("title","")) and set(p.get("genreIds",[]))==set(c.get("genreIds",[]))
    return p,exact

def _base_quality(batch, public, held, update, policies, now):
    records=batch.get("records",[])
    if not isinstance(records,list): raise ValueError("候補形式が不正")
    programs=public.get("programs",[])
    held_by_id={h.get("candidate",{}).get("id"):h for h in held.get("records",[])}
    rows=[]; unique={}; conflicts=set(); repeated=0
    for c in records:
        if not isinstance(c,dict): raise ValueError("候補はオブジェクト")
        key=c.get("id")
        if not isinstance(key,str) or not key: raise ValueError("候補ID不足")
        if key in unique:
            repeated+=1
            if unique[key]!=c: conflicts.add(key)
        else: unique[key]=c
    for rid,c in unique.items():
        p,exact=matching(c,programs)
        h=held_by_id.get(rid)
        reasons=issues(c,policies,now)
        if rid in conflicts: reasons.append("other")
        if h and not reasons: reasons.append("other")
        rows.append(dict(id=rid,title=c.get("title"),genreIds=c.get("genreIds",[]),
                         published=bool(p),publishedExact=exact,held=bool(h) or bool(reasons),
                         reasonCodes=reasons,validationReason=h.get("reason") if h else None,
                         missingStage="published" if exact else "published_outdated" if p else "held" if reasons else "awaiting_publication"))
    survey=batch.get("research",[])
    genre_rows=[]
    for gid,label in zip(GENRE_IDS,GENRES):
        logs=[r for r in survey if r.get("genreId")==gid]
        # Query text alone is a plan, not evidence it was executed.
        def executed(r):
            try: return bool(r.get("query")) and bool(r.get("tool")) and now-timedelta(hours=96)<=parse_dt(r.get("checkedAt"))<=now+timedelta(minutes=5) and r.get("status")=="executed"
            except (TypeError,ValueError): return False
        routes={r.get("route") for r in logs if executed(r)}
        n=sum(gid in p.get("genreIds",[]) and parse_dt(p["start"])>now for p in programs)
        count=sum(gid in c.get("genreIds",[]) for c in unique.values())
        coverage="name_and_genre_searched" if {"program_name","genre"}<=routes else "partially_searched" if routes else "not_searched"
        genre_rows.append(dict(genreId=gid,name=label,candidates=count,publicPrograms=n,searchCoverage=coverage,
                               zeroExplanation=None if n else "候補あり・未公開" if count else "検索実施・日時まで確認できる候補なし（番組不存在とは断定しない）" if routes else "調査不足"))
    names=read_json(ROOT/"config/discovery.json",{}).get("priorityTitles",["ほんとにあった怖い話"])
    attention=[r for r in rows if any(canonical(n) in canonical(r.get("title") or "") for n in names) and not r["publishedExact"] and "outside_window" not in r["reasonCodes"]]
    counts=update.get("counts",{})
    missing_future=[r for r in rows if not r["publishedExact"] and "outside_window" not in r["reasonCodes"]]
    return dict(checkedAt=iso(now),batchId=batch.get("batchId"),target="current_public_json" if update.get("publicationVerified") else "validated_candidate_not_yet_deployed",
        discovered=len(unique),inputDuplicates=repeated,conflictingIds=sorted(conflicts),
        newRegistrations=counts.get("added",0),updates=len(set(update.get("diff",{}).get("scheduleChanged",[]))|set(update.get("diff",{}).get("genreChanged",[]))),
        alreadyPublished=sum(r["publishedExact"] for r in rows),held=sum(r["held"] for r in rows),
        heldReasonCounts=dict(Counter(code for r in rows if r["held"] for code in r["reasonCodes"])),
        reasonLabels=REASONS,unpublishedFuture=len(missing_future),attention=attention,genres=genre_rows,records=rows,
        limitations=["検索結果なしは放送予定なしの証明ではない","GitHub ActionsにAI Web検索機能はない","対話中の実行と無人定期実行の証跡は別"])

def quality(batch, public, held, update, policies, now, ledger=None):
    from ledger import ready_for_research
    originals=list(batch.get("records",[]))
    combined={r["id"]:dict(r) for r in originals}
    audit_records=list(originals)
    discoveries=ledger if ledger is not None else batch.get("discoveries",[])
    leadmap={r["id"]:r for r in discoveries}
    for r in discoveries:
        if r["id"] not in combined:
            c=dict(r)
            c["genreIds"]=r.get("genreIds") or r.get("candidateGenreIds",[])
            combined[r["id"]]=c
            audit_records.append(c)
    b=dict(batch,records=audit_records)
    report=_base_quality(b,public,held,update,policies,now)
    byid={r["id"]:r for r in report["records"]}
    for rid,c in combined.items():
        out=byid[rid];lead=leadmap.get(rid,{})
        v=lead.get("officialVerification",{})
        excluded=lead.get("classification",{}).get("level")=="excluded" or lead.get("decision")=="excluded"
        clear=lead.get("classification",{}).get("level","clear")=="clear"
        confirmed=all(v.get(k) for k in ("title","station","datetime")) if lead else c.get("status")=="official_confirmed" and not c.get("verificationIssues")
        out.update(classificationLevel=lead.get("classification",{}).get("level","clear"),officialDatetimeConfirmed=bool(confirmed),excluded=excluded,
                   sourceUrls=lead.get("sourceUrls",[c.get("sourceUrl")]),holdReasons=lead.get("holdReasons",[]),
                   researchDue=ready_for_research(lead or c,now),omission=bool(confirmed and clear and not excluded and not out["publishedExact"] and "outside_window" not in out["reasonCodes"]))
        if not confirmed and "datetime_unconfirmed" not in out["reasonCodes"]: out["reasonCodes"].append("datetime_unconfirmed")
        if not clear and not excluded and "genre_uncertain" not in out["reasonCodes"]: out["reasonCodes"].append("genre_uncertain")
        if excluded:
            out["held"]=False;out["missingStage"]="excluded"
        elif out["reasonCodes"] or lead.get("decision")=="held":
            out["held"]=True
        if out["holdReasons"] and "other" not in out["reasonCodes"]: out["reasonCodes"].append("other")
    for out in report["records"]:
        if out["omission"] and leadmap.get(out["id"],{}).get("decision")=="eligible" and not out["reasonCodes"]:
            out["reasonCodes"].append("pipeline_handoff_missing")
            out["validationReason"]="公開条件を満たす台帳候補が検証済みフィードに到達していない"
    report["reasonLabels"]["pipeline_handoff_missing"]="公開処理への受け渡し漏れ"
    report["pipelineErrors"]=sum("pipeline_handoff_missing" in r["reasonCodes"] for r in report["records"])
    for g in report["genres"]:
        gid=g["genreId"]
        members=[r for r in report["records"] if gid in r["genreIds"]]
        logs=[]
        for r in batch.get("research",[]):
            try:
                if r.get("genreId")==gid and r.get("status")=="executed" and r.get("tool") and r.get("query") and now-timedelta(hours=96)<=parse_dt(r.get("checkedAt"))<=now+timedelta(minutes=5):
                    logs.append((r.get("route"),r["query"],r["checkedAt"]))
            except (ValueError,TypeError): pass
        g.update(searches=len(set(logs)),datetimeConfirmed=sum(r["officialDatetimeConfirmed"] for r in members),
                 held=sum(r["held"] for r in members),excluded=sum(r["excluded"] for r in members),
                 omissions=sum(r["omission"] for r in members))
        if not g["publicPrograms"]:
            if not g["searches"]: code="search_insufficient"
            elif any(r["held"] and r["officialDatetimeConfirmed"] for r in members): code="decision_pending"
            else: code="source_insufficient"
            # No-result searches alone can NEVER prove there are no broadcasts.
            for proof in batch.get("absenceEvidence",[]):
                try:
                    if proof.get("genreId")==gid and proof.get("verifiedNoEligibleBroadcast") and set(proof.get("scopeStations",[]))==set(STATIONS) and proof.get("windowStart")==iso(window(now)[0]) and proof.get("windowEnd")==iso(window(now)[1]) and proof.get("sourceUrl","").startswith("https://") and now-timedelta(hours=24)<=parse_dt(proof.get("checkedAt"))<=now:
                        code="no_broadcast_verified"
                except (ValueError,TypeError): pass
            g["zeroReasonCode"]=code
            g["zeroExplanation"]={"search_insufficient":"検索不足","source_insufficient":"情報源不足・個別の公式予定未確認（不存在とは断定しない）","decision_pending":"判定保留","no_broadcast_verified":"全対象局・対象期間の確認証跡あり：該当放送なし"}[code]
        else: g["zeroReasonCode"]=None
    report["held"]=sum(r["held"] for r in report["records"])
    report["heldReasonCounts"]=dict(Counter(code for r in report["records"] if r["held"] for code in r["reasonCodes"]))
    report["confirmedOmissions"]=[r for r in report["records"] if r["omission"]]
    report["ledgerCandidates"]=len(discoveries)
    report["excluded"]=sum(r["excluded"] for r in report["records"])
    report["attention"]=[r for r in report["attention"] if not r["excluded"]]
    report["unconfirmedDiscoveries"]=sum(not r["officialDatetimeConfirmed"] and not r["excluded"] for r in report["records"])
    report["unpublishedFuture"]=sum(r["officialDatetimeConfirmed"] and not r["publishedExact"] and not r["excluded"] and "outside_window" not in r["reasonCodes"] for r in report["records"])
    return report

def write_quality():
    return quality(read_json(ROOT/"data/ai-candidates.json",{}),read_json(ROOT/"public/v1/programs.json",{}),
        read_json(ROOT/"data/ai-held.json",{}),read_json(ROOT/"data/update-result.json",{}),
        read_json(ROOT/"config/source-policy.json",{}),datetime.now(JST),read_json(ROOT/"data/discovered-candidates.json",{"records":[]})["records"])

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--plan",action="store_true");parser.add_argument("--quality",action="store_true")
    args=parser.parse_args()
    if args.plan:
        atomic_json(ROOT/"data/search-plan.json",plan(read_json(ROOT/"config/discovery.json"),datetime.now(JST)))
    if args.quality:
        report=write_quality();atomic_json(ROOT/"data/collection-quality.json",report)
        if report.get("pipelineErrors"): raise SystemExit("PUBLICATION BLOCKED: eligible discovery missing from validated feed; see collection-quality.json")
        print("QUALITY discovered=%s held=%s unpublishedFuture=%s attention=%s"%(report["discovered"],report["held"],report["unpublishedFuture"],len(report["attention"])))
