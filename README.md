# CRD3 companion memory

How well can a game companion remember what a player said earlier in a session? I tested two small open-weight models (1.7B and 4B parameters), GPT-5 nano, and a larger low-cost comparison, DeepSeek V4.1 Flash. Each model answered the same six questions about three *Critical Role* sessions. It could either read the entire dialogue up to the question or use the three latest dialogue batches and up to four notes it had written before seeing the question.

In each condition, each model answered the same six questions five times each (6 × 5 = 30 answers). Accuracy counts correct answers out of 30. Pass^5 counts questions answered correctly on all five tries, out of six. For example, with full history Gemma got four questions right every time and missed the other two every time. That gave it 20/30 for accuracy and 4/6 for Pass^5.

| Model | Full history: correct answers | Pass^5 | Recent dialogue + notes: correct answers | Pass^5 |
| --- | ---: | ---: | ---: | ---: |
| GPT-5 nano | 29/30 | 5/6 | 14/30 | 2/6 |
| Liquid LFM3 1.7B | 1/30 | 0/6 | 0/30 | 0/6 |
| Gemma 3 4B | 20/30 | 4/6 | 9/30 | 1/6 |
| DeepSeek V4.1 Flash | 30/30 | 6/6 | 10/30 | 1/6 |

DeepSeek used the V4.1 Flash 1017 snapshot on OpenRouter (DeepInfra) with provider-default reasoning and the same output limits as the other models. A missing or cut-off answer earns zero. [Per-question scores for all four models](small-model-results.csv)

DeepSeek answered 30/30 trials correctly with full history and 10/30 with notes. It hit the output limit on 306 of 315 notebook writes. Gemma identified the game master’s corrected ruling in five of five full-history trials and one of five with notes. Gemma hit its output limit on 209 of 315 notebook writes, and Liquid did so on all 315. The result measures the whole process of writing, selecting and using notes under these limits. With six questions, no independent annotation review and no recent-dialogue-only control, the pilot cannot establish a general model ranking or isolate the benefit of adding notes to recent dialogue.

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
