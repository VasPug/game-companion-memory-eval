"""Rebuild the three pinned CRD3 transcripts using only the Python standard library."""
from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent


def verified(data, expected):
    if sha256(data).hexdigest() != expected:
        raise ValueError("Data digest differs from the frozen pilot")
    return data


def write_rows(rows, path, digest):
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode()
    verified(payload, digest)
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(payload)


def prepare(source_dir):
    manifests = json.loads((ROOT / "development_manifest.json").read_text())["episodes"]
    layout = json.loads((ROOT / "data/batch_layout.json").read_text())
    for source in json.loads((ROOT / "crd3_replay_index.json").read_text()):
        ep = source["episode"]
        manifest = next(m for m in manifests if m["episode"] == ep)
        if source_dir:
            raw = (source_dir / f"{ep}.json").read_bytes()
        else:
            url = source["source_url"].replace("github.com/", "raw.githubusercontent.com/").replace("/blob/", "/")
            with urlopen(url, timeout=60) as response:
                raw = response.read()
        turns = json.loads(verified(raw, source["source_sha256"]))["TURNS"]
        events = [{"id": f"{ep}:t{i:05d}", "turn_index": i, "speaker_labels": t["NAMES"],
                   "text": " ".join(t["UTTERANCES"]), "source_turn_number": t["NUMBER"]}
                  for i, t in enumerate(turns)]
        write_rows(events, ROOT / source["path"], source["replay_sha256"])
        batches = []
        start = 0
        for end, tokens in layout[ep]:
            chunk = events[start:end + 1]
            text = "\n".join(f"{e['id']} {','.join(e['speaker_labels'])}: {e['text']}" for e in chunk)
            batches.append({"episode": ep, "batch_index": len(batches), "start_turn": start,
                            "end_turn": end, "text": text, "events": chunk, "text_tokens": tokens})
            start = end + 1
        write_rows(batches, ROOT / manifest["path"], manifest["sha256"])
        print(f"Verified {ep}: {len(events)} turns, {len(batches)} batches")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, help="Local directory of original cleaned episode JSONs")
    prepare(parser.parse_args().source_dir)
