# CRD3 full-history baseline pilot

6 development questions across three training episodes, 5 requests per question per model. Each request receives the speaker-labelled transcript from the first turn through the question cutoff and four shuffled answer options. The option order is fixed per question across trials. Each request starts fresh and has no external notes. The primary score is exact option accuracy.

| Model snapshot | Correct | Accuracy | Questions correct on every repeat | Median response time | Estimated cost |
|---|---:|---:|---:|---:|---:|
| gpt-5-nano-2025-08-07 | 29/30 | 96.7% | 5/6 | 1.0 s | $0.0130 |
| gpt-5-mini-2025-08-07 | 30/30 | 100.0% | 6/6 | 1.2 s | $0.0475 |
| gpt-5-2025-08-07 | 30/30 | 100.0% | 6/6 | 1.3 s | $0.2663 |

## Checkpoint scores

| Question | gpt-5-nano-2025-08-07 | gpt-5-mini-2025-08-07 | gpt-5-2025-08-07 |
|---|---:|---:|---:|
| C1E016 · robes remaining | 4/5 | 5/5 | 5/5 |
| C1E016 · box recollection | 5/5 | 5/5 | 5/5 |
| C1E047 · flight offer | 5/5 | 5/5 | 5/5 |
| C1E047 · headmaster uncertainty | 5/5 | 5/5 | 5/5 |
| C1E082 · corrected effect | 5/5 | 5/5 | 5/5 |
| C1E082 · chamber layout | 5/5 | 5/5 | 5/5 |

Reported inputs ranged from 21,086 to 41,336 tokens. Total estimated API usage cost was $0.3269, using the rates in the saved configuration and the reported cached-token counts.

Missed answer on robes remaining by gpt-5-nano-2025-08-07. Annotated supporting turns cited in the response: [521].

Citation indices were checked for range. Citation quality needs an independent grade.

These six multiple-choice questions were authored for development and checked against their cited turns. They have no independent annotation review. Repeats measure consistency on the same questions. This run does not establish a model ranking, long-range memory performance, or the accuracy of external memory writes and retrieval.

Run a fresh baseline with an authorized OPENAI_API_KEY in the environment using `python baseline/run.py baseline/new-results` from the project root. Verify and summarize the saved pilot with `python baseline/summarize.py baseline/results`.
