# CRD3 companion memory

How well can a small game companion remember what a player said earlier in a session? I tested two open-weight models (1.7B and 4B parameters) and three lower-cost GPT models. Each model answered the same six questions about three *Critical Role* sessions. It could either read the entire dialogue up to the question or use the three latest dialogue batches and up to four notes it had written before seeing the question.

| Model | Full history | Pass⁵ | Recent dialogue + notes | Pass⁵ |
| --- | ---: | ---: | ---: | ---: |
| GPT-5 nano | 29/30 | 5/6 | 14/30 | 2/6 |
| GPT-4o mini | 26/30 | 5/6 | 20/30 | 2/6 |
| GPT-5.4 nano | 26/30 | 5/6 | 14/30 | 1/6 |
| Liquid LFM3 1.7B | 1/30 | 0/6 | 0/30 | 0/6 |
| Gemma 3 4B | 20/30 | 4/6 | 9/30 | 1/6 |

Accuracy is the number of correct answers out of 30 trials per condition. Pass⁵ counts how many of the six questions the model answered correctly on all five attempts. A missing or cut-off answer earns zero. [Per-question scores for all five models](small-model-results.csv)

All five models answered more questions correctly with full history. Gemma identified the game master’s corrected ruling in five of five full-history trials and one of five with notes. Gemma hit its output limit on 209 of 315 notebook writes, and Liquid did so on all 315. The result measures the whole process of writing, selecting and using notes under these limits. With six questions, no independent annotation review and no recent-dialogue-only control, the pilot cannot establish a general model ranking or isolate the benefit of adding notes to recent dialogue.

## Reproduce the original GPT pilot

The archived trial logs and replay commands below cover the original GPT pilot. The expanded comparison above includes additional OpenAI and OpenRouter trials; the CSV provides their per-question counts. [Original notebook analysis](memory/results/report.md) · [Original baseline](baseline/results/report.md) · [Questions and supporting turns](baseline/questions.json)

Use Python 3.10 or newer. The experiment code uses the standard library. These commands download the three pinned CRD3 source episodes, verify the transcript hashes, and replay the saved model outputs locally. No API key is needed.

```sh
python prepare_data.py
python -m unittest discover -s memory
python baseline/summarize.py baseline/results
python memory/summarize.py memory/results
```

The last command also writes `memory/results/checkpoints.jsonl`, containing the full notebook, selected notes, and scored answer at each checkpoint. The published logs use pseudonymous response IDs. The prompts, predictions, and scoring inputs are unchanged. The pinned source files can also be supplied with `python prepare_data.py --source-dir "/path/to/cleaned data"`.

## Run new trials with the original GPT runner

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
