"""Verify a completed CRD3 baseline run and print its Markdown report."""
import argparse
from collections import Counter
from itertools import product
import json
from pathlib import Path
from statistics import median

from run import ROOT, digest, prepare


def report(directory):
    config = json.loads((directory / "config.json").read_text())
    for name, key in [("run.py", "runner_sha256"), ("questions.json", "questions_sha256")]:
        assert digest((ROOT / name).read_bytes()) == config[key], f"{name} changed"

    cases = prepare()
    rows = [json.loads(line) for line in (directory / "answers.jsonl").read_text().splitlines()]
    models = config["models"]
    repeats = config["repeats"]
    keys = [(r["model"], r["question_id"], r["repeat"]) for r in rows]
    assert Counter(keys) == Counter(product(models, cases, range(repeats))), "Incomplete or duplicated trial"
    assert len({r["response_id"] for r in rows}) == len(rows), "Missing or repeated API response"
    for row in rows:
        prompt, gold, case = cases[row["question_id"]]
        assert row["input_sha256"] == digest(prompt.encode())
        assert row["error"] is None and row["cutoff"] == case["cutoff"]
        assert row["gold"] == gold and row["correct"] == (row["prediction"]["choice"] == gold)
        assert all(0 <= turn <= case["cutoff"] for turn in row["prediction"]["turns"])

    print("# CRD3 full-history baseline pilot\n")
    print(f"{len(cases)} development questions across three training episodes, {repeats} requests per question per model. Each request receives the speaker-labelled transcript from the first turn through the question cutoff and four shuffled answer options. The option order is fixed per question across trials. Each request starts fresh and has no external notes. The primary score is exact option accuracy.\n")
    print("| Model snapshot | Correct | Accuracy | Questions correct on every repeat | Median response time | Estimated cost |")
    print("|---|---:|---:|---:|---:|---:|")
    for model in models:
        group = [r for r in rows if r["model"] == model]
        correct = sum(r["correct"] for r in group)
        consistent = len(cases) - len({r["question_id"] for r in group if not r["correct"]})
        print(f"| {model} | {correct}/{len(group)} | {correct / len(group):.1%} | {consistent}/{len(cases)} | {median(r['latency_s'] for r in group):.1f} s | ${sum(r['estimated_usd'] for r in group):.4f} |")

    print("\n## Checkpoint scores\n")
    print("| Question | " + " | ".join(models) + " |")
    print("|---|" + "---:|" * len(models))
    for key, (_, _, case) in cases.items():
        counts = [sum(r["correct"] for r in rows if r["model"] == model and r["question_id"] == key) for model in models]
        print(f"| {case['episode']} · {key.replace('_',' ')} | " + " | ".join(f"{n}/{repeats}" for n in counts) + " |")

    tokens = [r["usage"]["input_tokens"] for r in rows]
    print(f"\nReported inputs ranged from {min(tokens):,} to {max(tokens):,} tokens. Total estimated API usage cost was ${sum(r['estimated_usd'] for r in rows):.4f}, using the rates in the saved configuration and the reported cached-token counts.\n")
    misses = [r for r in rows if not r["correct"]]
    for row in misses:
        key = row["question_id"]
        cited = set(row["prediction"]["turns"])
        overlap = sorted(cited.intersection(cases[key][2]["support"]))
        print(f"Missed answer on {key.replace('_', ' ')} by {row['model']}. Annotated supporting turns cited in the response: {overlap}.\n")
    print("Citation indices were checked for range. Citation quality needs an independent grade.\n")
    print("These six multiple-choice questions were authored for development and checked against their cited turns. They have no independent annotation review. Repeats measure consistency on the same questions. This run does not establish a model ranking, long-range memory performance, or the accuracy of external memory writes and retrieval.\n")
    print("Run a fresh baseline with an authorized OPENAI_API_KEY in the environment using `python baseline/run.py baseline/new-results` from the project root. Verify and summarize the saved pilot with `python baseline/summarize.py baseline/results`.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    report(parser.parse_args().directory)
