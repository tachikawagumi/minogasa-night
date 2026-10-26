"""Verify exact Pages contents; acknowledge only a verified deployment."""
import argparse, hashlib, json, time, urllib.request
from datetime import datetime
from feed import ROOT, JST, UA, read_json, atomic_json, validate_public, iso

URL="https://tachikawagumi.github.io/minogasa-night/v1/programs.json"
def verify(expected, url=URL, attempts=8, delay=10):
    validate_public(expected)
    digest=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    last=None
    for attempt in range(attempts):
        try:
            request=urllib.request.Request(url+"?revision="+expected["generatedAt"].replace("+","%2B"),headers={"User-Agent":UA,"Accept":"application/json","Cache-Control":"no-cache"})
            with urllib.request.urlopen(request,timeout=25) as response:
                if response.status!=200: raise ValueError("HTTP status")
                received=json.loads(response.read(2000001))
            validate_public(received)
            if digest(received)!=digest(expected): raise ValueError("公開JSONが今回の検証済み版と不一致")
            return {"verifiedAt":iso(datetime.now(JST)),"url":url,"httpStatus":200,"semanticSha256":digest(received),"programs":len(received["programs"])}
        except Exception as exc:
            last=exc
            if attempt+1<attempts: time.sleep(delay)
    raise RuntimeError("Pages公開確認に失敗: "+str(last))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--ack",action="store_true");p.add_argument("--attempts",type=int,default=8);args=p.parse_args()
    expected=read_json(ROOT/"public/v1/programs.json")
    evidence=verify(expected,attempts=args.attempts)
    if args.ack:
        result=read_json(ROOT/"data/update-result.json",{})
        result.update(status="published",publicationVerified=True,verification=evidence)
        atomic_json(ROOT/"data/update-result.json",result)
        history=read_json(ROOT/"data/update-history.json",[])
        atomic_json(ROOT/"data/update-history.json",(history+[result])[-50:])
        atomic_json(ROOT/"data/last-published.json",expected)
        atomic_json(ROOT/"data/publication.json",evidence)
    print(json.dumps(evidence,ensure_ascii=False))
