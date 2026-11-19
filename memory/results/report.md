# CRD3 memory pilot

Six frozen multiple-choice questions across three development episodes. Each model built five independent notebooks per episode. The two questions in each episode share an evolving notebook within a repeat. Checkpoint questions and answers never flow back into the writer. Each check uses the same cutoff and answer order as its full-history counterpart.

| Model | Full history | Recent dialogue + notes | Change in percentage points | Memory-arm cost estimate | Rejected or incomplete note patches |
|---|---:|---:|---:|---:|---:|
| gpt-5-nano-2025-08-07 | 29/30 | 14/30 (46.7%) | -50.0 | $0.067 | 15 |
| gpt-5-mini-2025-08-07 | 30/30 | 20/30 (66.7%) | -33.3 | $0.384 | 87 |
| gpt-5-2025-08-07 | 30/30 | 19/30 (63.3%) | -36.7 | $1.634 | 0 |

## Accuracy per question

| Question | gpt-5-nano-2025-08-07 | gpt-5-mini-2025-08-07 | gpt-5-2025-08-07 |
|---|---:|---:|---:|
| robes remaining | 1/5 | 0/5 | 2/5 |
| box recollection | 0/5 | 1/5 | 0/5 |
| flight offer | 3/5 | 5/5 | 3/5 |
| headmaster uncertainty | 5/5 | 5/5 | 5/5 |
| corrected effect | 0/5 | 4/5 | 4/5 |
| chamber layout | 5/5 | 5/5 | 5/5 |

## Tracing one corrected rule

Across 15 independent notebooks, a phrase naming both the two-point penalty and saves or saving throws appeared in 13 notebooks at some point before answering, remained in 6 at the checkpoint, and appeared in the selected notes in 6. The models answered correctly 8/15 times. This lexical check measures retention of the effect. It does not grade every part of the note or establish that a prior belief was revised.

For example, in the third GPT-5 replay, two notes recorded the corrected penalty by turn 244. The next patch replaced both, and the later answer was wrong. In that replay we can locate the first failure in note maintenance.


## Memory protocol and limits

The memory arm used 945 writes, 90 retrievals, and 90 answers. Total estimated cost was $2.085 using baseline rates and reported cached-token counts. Each observation batch gave the writer one opportunity to edit up to 20 slots within 4,000 JSON characters. Patches that exceeded the limits preserved the previous notebook. Each checkpoint exposed three recent batches and up to four model-selected notes. Every annotated supporting turn fell outside the recent window. Related clues, answer choices and prior model knowledge could still help.

Rejected patch counts by first applicable reason: slot outside 1–20 (74), notebook over 4,000 characters (27), source turn outside observed history (1). Incomplete responses by stage: answer (1). Incomplete answers count as incorrect. The previous notebook goes into the next batch after a rejected patch. The writer sees its current notebook and receives no explicit rejection message.

Scores measure end-to-end multiple-choice accuracy. Five repeats per item measure variability. These six questions have no independent annotation review. A correct answer alone cannot establish that the model retained evidence, retrieved it, or corrected an earlier wrong note. The card correction is spoken during the replay, while its original reading occurred in a prior session.

The checkpoint log includes the notebook before retrieval, the selected subset, source-turn pointers, the answer and the paired baseline score. Source-turn overlap is a diagnostic only. Paraphrases and nearby turn references require semantic review.

From the study root, run `python memory/run_memory.py memory/new-results` with the authorized key in the environment. An interrupted run resumes from its per-trajectory logs. Summarize a completed run using `python memory/summarize.py memory/new-results`.
