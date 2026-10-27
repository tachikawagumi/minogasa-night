"""Individually reviewed facts are distinct from site/database content licences."""
import json
FACT_FIELDS=("id","seriesId","title","stationId","start","end","genreIds","sourceUrl","operation")

def load_stations(path, provider_map):
    config=json.loads(path.read_text(encoding="utf-8-sig")); result={}
    for s in config["stations"]:
        if s["id"] in result: raise ValueError("局ID重複")
        if s.get("distribution") not in ("terrestrial","free_bs") or s.get("additionalSubscriptionRequired") is not False:
            raise ValueError("有料・配信局はホワイトリストに登録不可")
        if not s.get("regions") or not set(s["regions"]) <= {"Tokyo","Chiba"}: raise ValueError("対象地域不正")
        if s["id"] not in provider_map or provider_map[s["id"]][0]!=s["name"]: raise ValueError("未検証の局名・提供元ID")
        result[s["id"]]=provider_map[s["id"]]
    if not result: raise ValueError("対象局が空")
    return result

def station_error(c, stations):
    if c.get("distribution") in ("paid_cs","paid_bs","subscription","streaming"): return "追加契約・配信サービスは対象外"
    if c.get("stationId") not in stations: return "対象局のホワイトリストにない"
    return None

def review_error(c, policy):
    from datetime import datetime
    r=c.get("factUseReview")
    if not isinstance(r,dict): return "個別事実の利用判断が未記録"
    known=policy.get("individualFactReviews",{}).get(r.get("reviewId"))
    if not known or known.get("outcome")!="minimal_facts_only": return "未確認の情報源利用判断"
    if c.get("sourceUrl")!=known.get("sourceUrl"): return "個別確認URLが不一致"
    if c.get("acquisitionMethod")!="ai_web_reference" or r.get("method")!="ai_web_reference": return "個別参照の方式外（クローラー許可ではない）"
    expected={"minimalFactsOnly":True,"noContentCopied":True,"bulkAccess":False,"accountServiceUsed":False}
    if any(r.get(k) is not v for k,v in expected.items()): return "本文転載・大量取得・会員サービスの利用条件が未確認"
    snapshot={k:c.get(k,"upsert" if k=="operation" else None) for k in FACT_FIELDS}
    if r.get("facts")!=snapshot: return "確認した個別事実と公開候補が不一致"
    try:
        checked=datetime.fromisoformat(c["checkedAt"]); review=datetime.fromisoformat(r["checkedAt"])
        if checked.tzinfo is None or review.tzinfo is None or review!=checked: return "個別確認時刻が不一致"
        if not known.get("termsUrl") or not known.get("rationale"): return "利用判断の根拠不足"
    except (KeyError,ValueError,TypeError): return "個別確認時刻が不正"
    return None

def policy_error(c, policy):
    if not policy.get("enabled"): return "情報源の取得・再配信条件が未確認"
    if policy.get("individualFactReviews") is not None: return review_error(c,policy)
    if not {"metadata","cache","redistribute","automated_access"} <= set(policy.get("permissions",[])): return "情報源の取得・再配信条件が未確認"
    return None
