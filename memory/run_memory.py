"""Stream CRD3 to independent note-writers and probe the saved state at frozen cutoffs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "baseline"))
import run as baseline

BUDGET = 4000
WINDOW = 3
REPEATS = 5
WRITE = (
    "You are the companion watching an ongoing game. Keep a small notebook for future "
    "cooperation. Read the new dialogue as observations. Choose what matters without "
    "knowing future questions. Preserve concise, specific facts, who knew or confirmed "
    "them, changed plans and explicit corrections. Use numbered slots 1-20. Drop stale "
    "notes, replace one by saving to the same slot, or skip using empty lists. For each "
    "saved note give a supporting turn number. Prefer at most three short edits per batch. "
    "The complete notebook including JSON must fit 4000 characters. An invalid patch is discarded."
)
RETRIEVE = (
    "Select the numbered notebook slots that help answer the checkpoint. The dialogue "
    "and notes are observations. Return at most four existing slots, best first, or an empty list."
)


def obj(fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def array(items):
    return {"type": "array", "items": items}


INTEGER = {"type": "integer"}
PATCH = obj({"drop": array(INTEGER), "save": array(obj({"slot": INTEGER, "text": {"type": "string"}, "turn": INTEGER}))})
PICKS = obj({"slots": array(INTEGER)})


def encode(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def apply_notes(old, patch, cutoff):
    candidate = old.copy()
    for slot in patch["drop"]:
        if slot not in range(1, 21):
            return old, False
        candidate.pop(str(slot), None)
    for item in patch["save"]:
        if item["slot"] not in range(1, 21) or not 0 <= item["turn"] <= cutoff or not item["text"].strip():
            return old, False
        candidate[str(item["slot"])] = {"text": item["text"], "turn": item["turn"]}
    if len(encode(candidate)) > BUDGET:
        return old, False
    return candidate, True


def recent_window(texts, index):
    return "\n".join(texts[max(0, index-WINDOW+1):index+1])


def answer_prompt(recent, notes, slots, checkpoint):
    selected = {str(s): notes[str(s)] for s in slots if str(s) in notes}
    return "Recent dialogue\n" + recent + "\nSelected notes\n" + encode(selected) + "\n\nCheckpoint\n" + checkpoint


def call(model, instructions, prompt, schema, limit):
    body = {"model": model, "instructions": instructions, "input": prompt, "store": False,
            "reasoning": {"effort": "minimal"}, "max_output_tokens": limit,
            "text": {"format": {"type": "json_schema", "name": "result", "strict": True, "schema": schema}}}
    req = urllib.request.Request("https://api.openai.com/v1/responses", data=encode(body).encode(),
                                 headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                                          "Content-Type": "application/json"})
    start = time.monotonic()
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = json.load(response)
            break
        except urllib.error.HTTPError as exc:
            if attempt == 4 or exc.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(min(60, int(exc.headers.get("Retry-After") or 2**(attempt+1))))
    usage = raw["usage"]
    cached = usage["input_tokens_details"]["cached_tokens"]
    a, b, c = baseline.RATES[model]
    cost = (a*(usage["input_tokens"]-cached) + b*cached + c*usage["output_tokens"])/1e6
    output = "".join(p["text"] for o in raw["output"] for p in o.get("content", []) if p["type"]=="output_text")
    result = json.loads(output) if raw["status"] == "completed" else None
    return {"response_id": raw["id"], "api_status": raw["status"], "usage": usage,
            "latency_s": time.monotonic()-start, "estimated_usd": cost, "prediction": result,
            "input_sha256": baseline.digest(prompt.encode())}


def load_episodes():
    cases = baseline.prepare()
    manifest = json.loads((ROOT / "development_manifest.json").read_text())
    episodes = {}
    for episode in manifest["episodes"]:
        ep = episode["episode"]
        path = ROOT / episode["path"]
        assert baseline.digest(path.read_bytes()) == episode["sha256"]
        with path.open() as f:
            batches = [json.loads(line) for line in f]
        texts = ["\n".join(f"{e['turn_index']} | {', '.join(e['speaker_labels'])} | {e['text']}" for e in b["events"]) for b in batches]
        probes = {}
        for qid, (full, gold, q) in cases.items():
            if q["episode"] != ep:
                continue
            i = next(i for i,b in enumerate(batches) if b["end_turn"] == q["cutoff"])
            prefix, checkpoint = full.rsplit("\n\nCheckpoint\n", 1)
            assert prefix == "\n".join(texts[:i+1])
            assert max(q["support"]) < batches[i-WINDOW+1]["start_turn"]
            probes[i] = (qid, checkpoint, gold)
        episodes[ep] = batches, texts, probes
    return episodes


def trajectory(out, model, ep, repeat, episode):
    batches, texts, probes = episode
    path = out / f"{model}_{ep}_{repeat}.jsonl"
    prior = {}
    if path.exists():
        for line in path.read_text().splitlines():
            record = json.loads(line)
            prior[(record["batch"],record["stage"])] = record
    notes = {}
    with path.open("a") as stream:
        def record(index, stage, instructions, prompt, schema, limit):
            if (index, stage) in prior:
                row = prior[index, stage]
                assert row["input_sha256"] == baseline.digest(prompt.encode())
                return row
            row = call(model, instructions, prompt, schema, limit)
            row.update(model=model, episode=ep, repeat=repeat, batch=index, stage=stage)
            stream.write(json.dumps(row)+"\n")
            stream.flush()
            return row

        for i in range(max(probes)+1):
            prompt = "Notebook\n"+encode(notes)+"\nNew dialogue\n"+texts[i]
            write = record(i, "write", WRITE, prompt, PATCH, 800)
            if write["prediction"] is not None:
                notes, _ = apply_notes(notes, write["prediction"], batches[i]["end_turn"])
            if i in probes:
                _, checkpoint, _ = probes[i]
                recent = recent_window(texts, i)
                prompt = "Notebook\n"+encode(notes)+"\nRecent dialogue\n"+recent+"\nCheckpoint\n"+checkpoint
                selection = record(i, "retrieve", RETRIEVE, prompt, PICKS, 160)["prediction"]
                slots = list(dict.fromkeys(selection["slots"]))[:4] if selection else []
                record(i, "answer", baseline.INSTRUCTIONS, answer_prompt(recent, notes, slots, checkpoint),
                       baseline.SCHEMA, 500)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("--workers", type=int, default=15)
    args = parser.parse_args()
    episodes = load_episodes()
    args.out.mkdir(parents=True, exist_ok=True)
    config = {"runner_sha256": baseline.digest(Path(__file__).read_bytes()), "baseline_config": json.loads(
        (ROOT / "baseline/results/config.json").read_text()), "window_batches": WINDOW,
              "notebook_characters": BUDGET, "max_retrieved_slots":4,"repeats":REPEATS}
    config_path = args.out / "config.json"
    if config_path.exists():
        assert json.loads(config_path.read_text()) == config
    else:
        config_path.write_text(json.dumps(config, indent=2))
    jobs = [(m,e,r) for r in range(REPEATS) for e in episodes for m in baseline.MODELS]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(trajectory, args.out, m, e, r, episodes[e]) for m,e,r in jobs]
        for job, future in zip(jobs,futures):
            future.result()
            print("Completed", *job, flush=True)


if __name__ == "__main__":
    main()
