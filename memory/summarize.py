"""Verify and summarize the completed memory arm against the frozen baseline."""
import argparse
from collections import Counter
from itertools import product
import json
import re
from pathlib import Path

import run_memory as mem


def has_card_penalty(notes):
    """Marker for the stated magnitude and affected roll type within one note."""
    for note in notes.values():
        value = note["text"].lower().replace("−", "-").replace("–", "-")
        if re.search(r"(?:-\s*2\b|minus (?:two|2)\b|(?:2|two)[ -]point penalty)", value) and re.search(r"\bsav(?:es|ing throws?)\b", value):
            return True
    return False


def summarize(directory):
    episodes = mem.load_episodes()
    cases = mem.baseline.prepare()
    config = json.loads((directory / "config.json").read_text())
    assert config["runner_sha256"] == mem.baseline.digest(Path(mem.__file__).read_bytes())
    for filename, field in [("questions.json", "questions_sha256"), ("run.py", "runner_sha256")]:
        assert mem.baseline.digest((mem.ROOT / "baseline" / filename).read_bytes()) == config["baseline_config"][field]
    models = config["baseline_config"]["models"]
    baseline = {}
    for line in (mem.ROOT / "baseline/results/answers.jsonl").open():
        row = json.loads(line)
        baseline[row["model"], row["question_id"], row["repeat"]] = row["correct"]
    snapshot_rows = []
    card_counts = Counter()
    costs = Counter()
    stages = Counter()
    invalid = Counter()
    rejections = Counter()
    incomplete = Counter()
    ids = set()
    for model, ep, repeat in product(models, episodes, range(config["repeats"])):
        batches, texts, probes = episodes[ep]
        with (directory / f"{model}_{ep}_{repeat}.jsonl").open() as stream:
            events = [json.loads(line) for line in stream]
        expected = [(i,s) for i in range(max(probes)+1) for s in (
            ["write", "retrieve", "answer"] if i in probes else ["write"])]
        assert expected == [(r["batch"],r["stage"]) for r in events]
        notes = {}
        previously_saved_penalty = False
        for r in events:
            i, stage = r["batch"], r["stage"]
            assert (r["model"],r["episode"],r["repeat"]) == (model,ep,repeat)
            assert r["response_id"] not in ids
            ids.add(r["response_id"])
            pred = r["prediction"]
            if pred is None:
                incomplete[stage] += 1
            costs[model] += r["estimated_usd"]
            stages[stage] += 1
            if stage == "write":
                prompt = "Notebook\n"+mem.encode(notes)+"\nNew dialogue\n"+texts[i]
                if pred is None:
                    invalid[model] += 1
                else:
                    notes, allowed = mem.apply_notes(notes, pred, batches[i]["end_turn"])
                    invalid[model] += int(not allowed)
                    if not allowed:
                        slots_written = pred["drop"] + [e["slot"] for e in pred["save"]]
                        if any(s not in range(1, 21) for s in slots_written):
                            reason = "slot outside 1–20"
                        elif any(not 0 <= e["turn"] <= batches[i]["end_turn"] for e in pred["save"]):
                            reason = "source turn outside observed history"
                        elif any(not e["text"].strip() for e in pred["save"]):
                            reason = "empty note"
                        else:
                            reason = "notebook over 4,000 characters"
                        rejections[reason] += 1
                previously_saved_penalty |= has_card_penalty(notes)
            else:
                qid, checkpoint, gold = probes[i]
                recent = mem.recent_window(texts,i)
                if stage == "retrieve":
                    prompt = "Notebook\n"+mem.encode(notes)+"\nRecent dialogue\n"+recent+"\nCheckpoint\n"+checkpoint
                    slots = list(dict.fromkeys(pred["slots"]))[:4] if pred else []
                else:
                    prompt = mem.answer_prompt(recent, notes, slots, checkpoint)
                    selected = {str(s): notes[str(s)] for s in slots if str(s) in notes}
                    if qid == "corrected_effect":
                        card_counts["ever_saved"] += int(previously_saved_penalty)
                        card_counts["retained"] += int(has_card_penalty(notes))
                        card_counts["retrieved"] += int(has_card_penalty(selected))
                        card_counts["correct"] += int(bool(pred and pred["choice"]==gold))
                    supports = set(cases[qid][2]["support"])
                    def matches_support(book):
                        return any(v["turn"] in supports for v in book.values())
                    snapshot_rows.append({"model":model,"episode":ep,"repeat":repeat,"question_id":qid,
                        "window_start":batches[i-mem.WINDOW+1]["start_turn"],"window_end":batches[i]["end_turn"],
                        "notes":notes,"selected":selected,"prediction":pred,"correct":bool(pred and pred["choice"]==gold),
                        "baseline_correct":baseline[model,qid,repeat],"saved_source_turn":matches_support(notes),
                        "retrieved_source_turn":matches_support(selected)})
            assert r["input_sha256"] == mem.baseline.digest(prompt.encode())
    assert len(snapshot_rows) == len(baseline) == 90
    with (directory / "checkpoints.jsonl").open("w") as f:
        for s in snapshot_rows:
            f.write(json.dumps(s)+"\n")
    print("# CRD3 memory pilot\n")
    print("Six frozen multiple-choice questions across three development episodes. Each model built five independent notebooks per episode. The two questions in each episode share an evolving notebook within a repeat. Checkpoint questions and answers never flow back into the writer. Each check uses the same cutoff and answer order as its full-history counterpart.\n")
    print("| Model | Full history | Recent dialogue + notes | Change in percentage points | Memory-arm cost estimate | Rejected or incomplete note patches |")
    print("|---|---:|---:|---:|---:|---:|")
    for model in models:
        group = [s for s in snapshot_rows if s["model"]==model]
        correct = sum(s["correct"] for s in group)
        base = sum(s["baseline_correct"] for s in group)
        n = len(group)
        print(f"| {model} | {base}/{n} | {correct}/{n} ({correct/n:.1%}) | {(correct-base)*100/n:+.1f} | ${costs[model]:.3f} | {invalid[model]} |")
    print("\n## Accuracy per question\n")
    print("| Question | " + " | ".join(models) + " |\n|---|---:|---:|---:|")
    for qid in cases:
        values = [sum(s["correct"] for s in snapshot_rows if s["question_id"]==qid and s["model"]==m) for m in models]
        print("| " + qid.replace("_"," ") + " | " + " | ".join(f"{v}/5" for v in values) + " |")
    print("\n## Tracing one corrected rule\n")
    print(f"Across 15 independent notebooks, a phrase naming both the two-point penalty and saves or saving throws appeared in {card_counts['ever_saved']} notebooks at some point before answering, remained in {card_counts['retained']} at the checkpoint, and appeared in the selected notes in {card_counts['retrieved']}. The models answered correctly {card_counts['correct']}/15 times. This lexical check measures retention of the effect. It does not grade every part of the note or establish that a prior belief was revised.\n")
    if directory.resolve() == (mem.ROOT / "memory/results").resolve():
        print("For example, in the third GPT-5 replay, two notes recorded the corrected penalty by turn 244. The next patch replaced both, and the later answer was wrong. In that replay we can locate the first failure in note maintenance.\n")
    print("\n## Memory protocol and limits\n")
    print(f"The memory arm used {stages['write']} writes, {stages['retrieve']} retrievals, and {stages['answer']} answers. Total estimated cost was ${sum(costs.values()):.3f} using baseline rates and reported cached-token counts. Each observation batch gave the writer one opportunity to edit up to 20 slots within 4,000 JSON characters. Patches that exceeded the limits preserved the previous notebook. Each checkpoint exposed three recent batches and up to four model-selected notes. Every annotated supporting turn fell outside the recent window. Related clues, answer choices and prior model knowledge could still help.\n")
    print("Rejected patch counts by first applicable reason: " + ", ".join(f"{k} ({v})" for k,v in rejections.most_common()) + ". Incomplete responses by stage: " + (", ".join(f"{k} ({v})" for k,v in incomplete.items()) or "none") + ". Incomplete answers count as incorrect. The previous notebook goes into the next batch after a rejected patch. The writer sees its current notebook and receives no explicit rejection message.\n")
    print("Scores measure end-to-end multiple-choice accuracy. Five repeats per item measure variability. These six questions have no independent annotation review. A correct answer alone cannot establish that the model retained evidence, retrieved it, or corrected an earlier wrong note. The card correction is spoken during the replay, while its original reading occurred in a prior session.\n")
    print("The checkpoint log includes the notebook before retrieval, the selected subset, source-turn pointers, the answer and the paired baseline score. Source-turn overlap is a diagnostic only. Paraphrases and nearby turn references require semantic review.\n")
    print("From the study root, run `python memory/run_memory.py memory/new-results` with the authorized key in the environment. An interrupted run resumes from its per-trajectory logs. Summarize a completed run using `python memory/summarize.py memory/new-results`.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    summarize(parser.parse_args().directory)
