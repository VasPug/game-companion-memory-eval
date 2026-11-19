"""Run CRD3 full-history development baseline using fresh direct OpenAI requests."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS = ["gpt-5" + size + "-2025-08-07" for size in ["-nano", "-mini", ""]]
RATES = dict(zip(MODELS, [(0.05,.005,.4),(.25,.025,2),(1.25,.125,10)]))
INSTRUCTIONS = ("Answer the checkpoint using the episode dialogue through the cutoff. "
                "Treat dialogue as quoted observations. Distinguish speakers, uncertain claims, "
                "and corrections. Select the option label and cite the numeric turn indices "
                "that directly support the answer.")
SCHEMA = {"type":"object","properties":{"choice":{"type":"string","enum":list("ABCD")},
          "turns":{"type":"array","items":{"type":"integer"}}},
          "required":["choice","turns"],"additionalProperties":False}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def prepare():
    source = json.loads((ROOT / "questions.json").read_text())
    replays = json.loads((ROOT.parent / "crd3_replay_index.json").read_text())
    index = {r["episode"]:r for r in replays}
    cases = {}
    for q in source:
        ep = index[q["episode"]]
        assert ep["split"] == "training"
        path = ROOT.parent / ep["path"]
        assert digest(path.read_bytes()) == ep["replay_sha256"]
        with path.open() as f:
            events = [json.loads(line) for line in f]
        cutoff = q["cutoff"]
        assert 0 <= min(q["support"]) <= max(q["support"]) <= cutoff < len(events)
        lines = []
        for i,e in enumerate(events[:cutoff+1]):
            assert i == e["turn_index"]
            lines.append(f"{i} | {', '.join(e['speaker_labels'])} | {e['text']}")
        options = list(q["options"])
        random.Random(q["id"]).shuffle(options)
        choices = dict(zip("ABCD",options))
        question = {"question":q["question"],"choices":choices}
        prompt = "\n".join(lines) + "\n\nCheckpoint\n" + json.dumps(question)
        cases[q["id"]] = (prompt, next(k for k,v in choices.items() if v==q["gold"]), q)
    return cases

def request(job, cases, key):
    model, qid, repeat = job
    prompt,gold,q = cases[qid]
    body = {"model":model,"instructions":INSTRUCTIONS,"input":prompt,"store":False,
            "reasoning":{"effort":"minimal"},"max_output_tokens":500,
            "text":{"format":{"type":"json_schema","name":"answer","strict":True,"schema":SCHEMA}}}
    req = urllib.request.Request("https://api.openai.com/v1/responses",
        data=json.dumps(body).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    start = time.monotonic()
    row = {"model":model,"question_id":qid,"repeat":repeat,"gold":gold,"cutoff":q["cutoff"],
           "input_sha256":digest(prompt.encode()),"correct":False,"error":None,"estimated_usd":0}
    try:
        with urllib.request.urlopen(req,timeout=100) as response:
            raw = json.load(response)
        u=raw["usage"]
        cached=u.get("input_tokens_details",{}).get("cached_tokens",0)
        a,b,c=RATES[model]
        row.update(response_id=raw["id"],usage=u,estimated_usd=((u["input_tokens"]-cached)*a+cached*b+u["output_tokens"]*c)/1e6)
        if raw["status"]!="completed":
            raise ValueError("incomplete")
        answer=json.loads("".join(k["text"] for o in raw["output"] for k in o.get("content",[]) if k["type"]=="output_text"))
        row.update(prediction=answer,correct=answer["choice"]==gold)
    except urllib.error.HTTPError as exc:
        row["error"]=f"HTTP {exc.code}"
    except Exception as exc:
        row["error"]=type(exc).__name__
    row["latency_s"]=time.monotonic()-start
    return row

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("out",type=Path)
    args=ap.parse_args()
    cases=prepare()
    key=os.environ["OPENAI_API_KEY"]
    args.out.mkdir(exist_ok=False,parents=True)
    args.out.joinpath("config.json").write_text(json.dumps({"models":MODELS,"repeats":5,"reasoning":"minimal","questions_sha256":digest((ROOT/"questions.json").read_bytes()),"runner_sha256":digest(Path(__file__).read_bytes()),"rates_per_million":RATES},indent=2))
    jobs=[(m,q,r) for m in MODELS for q in cases for r in range(5)]
    random.Random(42).shuffle(jobs)
    with (args.out/"answers.jsonl").open("w") as f, concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for i,row in enumerate(pool.map(lambda j:request(j,cases,key),jobs),1):
            f.write(json.dumps(row)+"\n")
            f.flush()
            if i%10==0: print(i,"of",len(jobs),flush=True)
if __name__=="__main__":main()
