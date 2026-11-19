# CRD3 companion memory

Can a game companion retain a correction until a player needs it? This repository contains a small replay-based evaluation on dialogue from *Critical Role*. Three GPT-5 models answered the same six multiple-choice questions using either the full episode prefix or three recent dialogue batches and a notebook they maintained while reading.

| Model | Full history | Recent dialogue + notes |
| --- | ---: | ---: |
| GPT-5 nano | 29/30 | 14/30 |
| GPT-5 mini | 30/30 | 20/30 |
| GPT-5 | 30/30 | 19/30 |

Each condition used five repeats per question across three development episodes. Questions stayed hidden during note writing. One API answer was incomplete and counted as incorrect. The pilot measures replay question accuracy. The six questions have no independent annotation review, and the experiment has no recent-dialogue-only control. See the [per-question scores and correction trace](memory/results/report.md), [baseline scores](baseline/results/report.md), and [questions with evidence turns](baseline/questions.json).

## Reproduce the published scores

Use Python 3.10 or newer. The experiment code uses the standard library. These commands download the three pinned CRD3 source episodes, verify the transcript hashes, and replay the saved model outputs locally. No API key is needed.

```sh
python prepare_data.py
python -m unittest discover -s memory
python baseline/summarize.py baseline/results
python memory/summarize.py memory/results
```

The last command also writes `memory/results/checkpoints.jsonl`, containing the full notebook, selected notes, and scored answer at each checkpoint. The published logs use pseudonymous response IDs. The prompts, predictions, and scoring inputs are unchanged. The pinned source files can also be supplied with `python prepare_data.py --source-dir "/path/to/cleaned data"`.

## Run new model trials

With the study data prepared, set `OPENAI_API_KEY` in your environment. These commands make billable requests to the OpenAI Responses API. New model outputs can differ from the recorded runs. The memory comparison script always uses the published baseline as its reference.

```sh
python baseline/run.py baseline/new-results
python baseline/summarize.py baseline/new-results
python memory/run_memory.py memory/new-results
python memory/summarize.py memory/new-results
```

Each memory run starts with an empty notebook per model, episode, and repeat. After each batch the writer can add, replace, delete, or skip notes within 20 slots and 4,000 JSON characters. At a checkpoint a separate call selects up to four notes. The answerer sees those notes and three recent batches. Invalid edits leave the prior notebook in place. The saved configurations identify the exact model snapshots and runner hashes.

## Data and attribution

Transcript source: Revanth Rameshkumar and Peter Bailey, *Storytelling with Dialogue: A Critical Role Dungeons and Dragons Dataset* (ACL 2020), based on Critical Role and the CRTranscript community. The preparation script joins utterances into speaker-labelled turns and groups turns into batches. Episode transcripts are downloaded on demand. CRD3 and the transcript-derived material distributed here are covered by [CC BY-SA 4.0](data/CRD3-LICENSE.txt). [Pinned CRD3 source](https://github.com/RevanthRameshkumar/CRD3/tree/7fd4515eea411f0f9c5d0a03a8b6b8b2da464e81)
