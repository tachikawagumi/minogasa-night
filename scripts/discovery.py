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

def quality(batch, public, held, update, policies, now):
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

def write_quality():
    return quality(read_json(ROOT/"data/ai-candidates.json",{}),read_json(ROOT/"public/v1/programs.json",{}),
        read_json(ROOT/"data/ai-held.json",{}),read_json(ROOT/"data/update-result.json",{}),
        read_json(ROOT/"config/source-policy.json",{}),datetime.now(JST))

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--plan",action="store_true");parser.add_argument("--quality",action="store_true")
    args=parser.parse_args()
    if args.plan:
        atomic_json(ROOT/"data/search-plan.json",plan(read_json(ROOT/"config/discovery.json"),datetime.now(JST)))
    if args.quality:
        report=write_quality();atomic_json(ROOT/"data/collection-quality.json",report)
        print("QUALITY discovered=%s held=%s unpublishedFuture=%s attention=%s"%(report["discovered"],report["held"],report["unpublishedFuture"],len(report["attention"])))
