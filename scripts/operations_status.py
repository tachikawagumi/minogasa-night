"""Internal-only update status. No changes to the public feed or Android UI."""
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import json, os

ROOT = Path(__file__).resolve().parents[1]
JST = ZoneInfo("Asia/Tokyo")

def read(root, name, default):
    path = root / name
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default

def stamp(value):
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timezone required")
    return dt.astimezone(JST)

def latest_due(now):
    due = now.astimezone(JST).replace(hour=9, minute=0, second=0, microsecond=0)
    while due.weekday() not in (0, 3) or due > now:
        due -= timedelta(days=1)
    return due

def build_status(root=ROOT, now=None, environ=None):
    now = now or datetime.now(JST)
    env = os.environ if environ is None else environ
    feed = read(root, "public/v1/programs.json", {})
    batch = read(root, "data/ai-candidates.json", {})
    result = read(root, "data/update-result.json", {})
    publication = read(root, "data/publication.json", {})
    cache = read(root, "data/anime-cache.json", {})
    runs = read(root, "data/ai-research-runs.json", {}).get("runs", [])
    due = latest_due(now)
    relevant = [r for r in runs if r.get("executionContext") == "scheduled_heartbeat"
                and r.get("scheduledFor") and stamp(r["scheduledFor"]) == due]
    scheduled = sorted(relevant, key=lambda r: r.get("triggerReceivedAt", ""))[-1] if relevant else None
    verification = result.get("verification", {})
    research_logs = [r for r in batch.get("research", []) if r.get("checkedAt") == batch.get("researchedAt") and r.get("status") == "executed"]
    logs = [r for r in research_logs if r.get("windowStart") == feed.get("windowStart") and r.get("windowEnd") == feed.get("windowEnd")]
    run = next((r for r in reversed(runs) if batch.get("batchId") and r.get("runId") == batch["batchId"]), {})
    matching_update = bool(batch.get("batchId")) and result.get("batchId") == batch["batchId"]
    checked = stamp(batch.get("researchedAt"))
    age = (now - checked).total_seconds() / 3600 if checked else None
    if age is not None and age < -5/60:
        raise ValueError("AI research time is in the future")
    coverage = []
    for genre in feed.get("genres", []):
        rows = [r for r in feed.get("programs", []) if genre["id"] in r.get("genreIds", [])]
        coverage.append(dict(genreId=genre["id"], name=genre["name"], programs=len(rows),
                             lastStart=max((r["start"] for r in rows), default=None)))
    return dict(schemaVersion=1, observedAt=now.isoformat(), targetWindow=dict(start=feed.get("windowStart"), endExclusive=feed.get("windowEnd")),
        lastAIResearch=dict(at=batch.get("researchedAt"), executionContext=batch.get("executionContext", "unknown"),
            batchId=batch.get("batchId"), genresSearched=len({r["genreId"] for r in research_logs if r.get("genreId")}),
            queries=len(research_logs), currentWindowQueries=len(logs),
            searchResult="executed_search_logs" if research_logs else "not_confirmed",
            newCandidates=run.get("newCandidates", run.get("eligibleNew")),
            newPublic=result.get("counts", {}).get("added") if matching_update and result.get("publicationVerified") is True else None,
            publicationStatus=result.get("status") if matching_update else run.get("status"),
            hoursSinceResearch=round(age, 2) if age is not None else None,
            targetWindowStart=batch.get("windowStart"), targetWindowEndExclusive=batch.get("windowEnd"),
            evidence="candidate search logs; does not establish scheduler timing"),
        latestScheduledSlot=dict(expectedAt=due.isoformat(), heartbeatObserved=scheduled is not None,
            triggerReceivedAt=scheduled.get("triggerReceivedAt") if scheduled else None,
            onTime=scheduled.get("onTime") if scheduled else None,
            status="late_observed" if scheduled and scheduled.get("onTime") is False else
                   "observed_timing_unverified" if scheduled else "not_observed",
            platformExecutionId=scheduled.get("platformExecutionId") if scheduled else None),
        lastAnimeSuccessAt=cache.get("checkedAt"),
        lastUpdate=dict(status=result.get("status"), at=result.get("at"), counts=result.get("counts", {})),
        lastActions=dict(runId=env.get("GITHUB_RUN_ID"), event=env.get("GITHUB_EVENT_NAME"),
            observedAt=now.isoformat(), startTime=None, note="observation time is not workflow start time"),
        lastPages=dict(verifiedAt=verification.get("verifiedAt") or publication.get("verifiedAt"),
            verified=result.get("publicationVerified") is True, url=verification.get("url") or publication.get("url"),
            semanticSha256=verification.get("semanticSha256") or publication.get("semanticSha256")),
        genreCoverage=coverage, publicPrograms=len(feed.get("programs", [])),
        limitations=["GitHub Actions does not perform AI Web search.",
            "No observed heartbeat is not proof of why it did not start.",
            "No slots in a genre does not prove there are no broadcasts."])

if __name__ == "__main__":
    target = ROOT / "data/operations-status.json"
    value = build_status()
    temp = target.with_suffix(".json.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)
    print(json.dumps(dict(ai=value["lastAIResearch"], scheduled=value["latestScheduledSlot"],
                          pages=value["lastPages"], programs=value["publicPrograms"]), ensure_ascii=False))
