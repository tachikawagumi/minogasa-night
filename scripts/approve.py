"""Explicit human approval: validate the draft and atomically merge into manual DB."""
import argparse
from feed import *

def approve(draft, existing, now):
    rows = draft["records"]
    if not rows:
        raise ValueError("下書きが空です")
    prepared = []
    for source in rows:
        row = dict(source)
        if row.get("status") != "official_confirmed":
            raise ValueError("公式日時と分類を確認してから承認してください")
        row["publicationApproved"] = True
        row["origin"] = "manual_official_facts"
        if not row.get("genreBasis"):
            raise ValueError("ジャンル根拠が必要")
        prepared.append(row)
    if len(merge_rows(prepared, now)) != len(prepared):
        raise ValueError("過去・期間外・重複の下書きが含まれています")
    by_id = {row["id"]: row for row in existing["records"]}
    by_id.update({row["id"]: row for row in prepared})
    return {"reviewedAt": iso(now), "records": list(by_id.values())}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--approve", action="store_true", required=True)
    p.parse_args()
    path = ROOT / "data/manual-approved.json"
    result = approve(read_json(ROOT / "data/manual-draft.json"), read_json(path, {"records": []}), datetime.now(JST))
    atomic_json(path, result)
    print("APPROVED", len(result["records"]))
