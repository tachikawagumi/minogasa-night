"""Offline shadow experiment. No HTTP, GitHub write, publication, or AI API calls.
Work creates observations/episode annotations; this program validates and replays.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict
import argparse, hashlib, json, unicodedata, re

ROOT=Path(__file__).resolve().parent
JST=timezone(timedelta(hours=9))
OBS_FIELDS={"observationId","title","stationId","start","end","sourceId","sourceUrl","checkedAt","verification","verificationMethod","discoveryRoute","acquisitionMode","rerun","claimedStart","claimedLiteral","holdReason"}

def read(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8-sig"))

def dt(value):
    if not isinstance(value,str): raise ValueError("datetime_unconfirmed")
    d=datetime.fromisoformat(value.replace("Z","+00:00"))
    if d.tzinfo is None: raise ValueError("timezone_required")
    return d.astimezone(JST)

def canon(title):
    # No fuzzy similarity, no removal of episode numbers or replay identity.
    return re.sub(r"\s+","",unicodedata.normalize("NFKC",title)).casefold()

def key(row):
    return (row["stationId"],dt(row["start"]).isoformat(),canon(row["title"]))

def validate_observation(row, baseline, sources, mode="individual_reference"):
    if set(row)-OBS_FIELDS: raise ValueError("unexpected_body_or_fields")
    if not row.get("title") or not row.get("observationId"): raise ValueError("identity_missing")
    if row.get("stationId") not in {s["id"] for s in baseline["stations"]}: raise ValueError("station_out_of_scope")
    if not all(row.get("verification",{}).get(k) is True for k in ("title","station","datetime")):
        raise ValueError(row.get("holdReason") or "fact_verification_missing")
    start=dt(row.get("start"))
    if not dt(baseline["windowStart"])<=start<dt(baseline["windowEnd"]): raise ValueError("outside_window")
    if row.get("end") and dt(row["end"])<=start: raise ValueError("end_before_start")
    dt(row.get("checkedAt"))
    source=sources.get(row.get("sourceId"))
    if not source: raise ValueError("source_unreviewed")
    if row["stationId"] not in source.get("stationIds",[]): raise ValueError("source_station_mismatch")
    if row.get("sourceUrl") not in source.get("individuallyReviewedUrls",[]): raise ValueError("source_url_not_individually_reviewed")
    if mode not in ("individual_reference","automated"): raise ValueError("unknown_mode")
    if mode=="automated" and not source.get("automated"): raise ValueError("automated_source_not_authorised")
    if row.get("acquisitionMode")!="individual_reference": raise ValueError("unreviewed_acquisition")
    if not row.get("sourceUrl","").startswith("https://"): raise ValueError("source_url_missing")

def unify(observations, baseline, sources, mode="individual_reference"):
    groups=defaultdict(list); held=[]
    for r in observations:
        try:
            validate_observation(r,baseline,sources,mode)
            groups[key(r)].append(r)
        except (ValueError,TypeError,KeyError) as e:
            held.append({"observationId":r.get("observationId"),"reason":str(e)})
    slots=defaultdict(set)
    for k in groups: slots[k[:2]].add(k[2])
    known={key(p):p for p in baseline["programs"]}
    known_slots=defaultdict(set)
    for k in known: known_slots[k[:2]].add(k[2])
    result=[]
    for k, group in groups.items():
        ends={dt(r["end"]).isoformat() for r in group if r.get("end")}
        if len(slots[k[:2]])>1 or len(ends)>1 or (known_slots[k[:2]] and k[2] not in known_slots[k[:2]]):
            held.extend({"observationId":r["observationId"],"reason":"conflicting_slot_facts"} for r in group)
            continue
        old=known.get(k)
        identity="shadow-"+hashlib.sha256("|".join(k).encode()).hexdigest()[:24]
        result.append(dict(id=old["id"] if old else identity,seriesId=old.get("seriesId") if old else None,
            title=group[0]["title"],stationId=k[0],start=k[1],end=next(iter(ends),None),
            sourceUrls=sorted({r["sourceUrl"] for r in group}),checkedAt=max(r["checkedAt"] for r in group),
            observationIds=[r["observationId"] for r in group],genreIds=[],verificationStatus="facts_confirmed",
            classificationStatus="pending",publicationApproved=False,productionHandoffEnabled=False))
    return result,held

def classify(rows, annotations, genres):
    # This is an evidence gate, not a keyword classifier or an unattended AI.
    byid={}
    for a in annotations:
        if a["observationId"] in byid and byid[a["observationId"]]!=a: raise ValueError("conflicting_annotations")
        byid[a["observationId"]]=a
    for row in rows:
        found=[byid[i] for i in row["observationIds"] if i in byid]
        if not found: continue
        tags=set(); bases=[]; rejected=False
        for a in found:
            if (not a.get("reviewer") or a.get("derivedFromTitleOnly") is not False
                or not a.get("basis") or not set(a.get("genreIds",[]))<=set(genres)
                or not a.get("contentSourceUrls") or not set(a["contentSourceUrls"])<=set(row["sourceUrls"])):
                rejected=True; continue
            if a.get("decision")=="supported" and a.get("genreIds"):
                tags.update(a["genreIds"]);bases.append(a["basis"])
            elif a.get("decision")!="no_supported_genre":
                rejected=True
        if rejected:
            row["classificationStatus"]="pending"; continue
        row["genreIds"]=sorted(tags);row["genreBasis"]=bases
        row["classificationStatus"]="supported" if tags else "no_supported_genre"
    return rows

def compare(baseline, observations, annotations, sources, reference, regular):
    ids=[g["id"] for g in baseline["genres"]]
    rows,held=unify(observations,baseline,sources)
    rows=classify(rows,annotations,ids)
    eligible=[r for r in rows if r["classificationStatus"]=="supported"]
    a={key(p):p for p in baseline["programs"]}
    b={key(p):p for p in eligible}
    only=[p for k,p in b.items() if k not in a]
    checklist=[]
    for r in reference["records"]:
        k=key(r);checklist.append(dict(title=r["title"],genreIds=r["genreIds"],
            a=k in a and set(r["genreIds"])<=set(a[k]["genreIds"]),
            b=k in b and set(r["genreIds"])<=set(b[k]["genreIds"])))
    coverage=[]
    for g in baseline["genres"]:
        gid=g["id"];n=sum(gid in r["genreIds"] for r in eligible)
        anchors=[r for r in checklist if gid in r["genreIds"]]
        coverage.append(dict(**g,a=sum(gid in r["genreIds"] for r in a.values()),b=n,
            bOnly=sum(gid in r["genreIds"] for r in only),
            checklist=len(anchors),aChecklistHits=sum(r["a"] for r in anchors),bChecklistHits=sum(r["b"] for r in anchors),
            fallbackRequired=n<2 or any(not r["b"] for r in anchors),
            regularReferenceIds=[r["id"] for r in regular["entries"] if gid in r["genreIds"]]))
    return dict(schemaVersion=1,windowStart=baseline["windowStart"],windowEnd=baseline["windowEnd"],
        experiment="offline replay of interactive observations, not a deployed collector",
        baselineCommit=baseline["baselineCommit"],aTotal=len(a),bObserved=len(observations),
        bFactsConfirmed=len(rows),bClassified=len(eligible),bUnclassifiedOrOutOfGenre=len(rows)-len(eligible),
        bHeld=len(held),bOnly=len(only),shared=len(set(a)&set(b)),
        genreCoverage=coverage,checklist=checklist,checklistLimitations=reference["selection"],
        globalRecall=None,statisticalPrecision=None,equalEffortComparison=False,
        records=rows,held=held,bOnlyPrograms=only,productionHandoffEnabled=False,
        recommendation="Keep A and anime pipeline. Evaluate station/date discovery as a complementary Work task; no full switch or broad automatic scraping.")

def write_output(path,value):
    target=Path(path).resolve()
    # Even CLI output cannot touch the active data/public/config directories.
    if target!=ROOT/"comparison.json": raise ValueError("output_must_be_experiment_comparison_json")
    tmp=target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(target)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",default=str(ROOT/"comparison.json"))
    args=parser.parse_args()
    v=compare(read("baseline-a.json"),read("observations-b.json")["observations"],
        read("classifications.json")["annotations"],read("source-feasibility.json")["sources"],
        read("reference-checklist.json"),read("regular-reference.json"))
    write_output(args.output,v)
    print(json.dumps({k:v[k] for k in ("aTotal","bObserved","bFactsConfirmed","bClassified","bHeld","bOnly","shared","productionHandoffEnabled")}))
if __name__=="__main__": main()
