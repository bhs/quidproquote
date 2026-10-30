# Method: scripts, tests and the snapshot of the sources

Run from the directory above (`discovery/person-labelled-matching-check/`): `python method/run.py` (needs `ANTHROPIC_API_KEY`
and network; the embedding model downloads on first use). Tests: `python -m unittest discover -s method/tests`.

- `run.py` drives every stage and writes `results.md`, `results.json`, `matches-that-stand-out.md` to the working
  directory and, when no sheet exists, `labelling/`.
- `check_lib.py` (sheet sampling, reading and scoring people's labels, timing, disagreement, instances), `stages.py`
  (lexical and embedding scoring with chance counts), `render_check.py` (markdown), `labeller.py` (the labelling page).
- `trial_lib.py`, `compare_lib.py`, `embed.py`, `judge.py` are copied unchanged from `../../matching-methods-comparison/`.
- `data/` is the snapshot of the sources: 11 caption transcripts (`transcripts/`, `meetings.json`) retrieved 29 October
  2026 and 133 donor priority statements (`priorities.json`) with their URLs and retrieval dates.

Settings are environment variables with defaults in `run.py` (`SHEET_PER_METHOD`, `EMB_POOL_CAP`, `NULL_DRAWS`, ...); the AI
judge's model is `MATCH_JUDGE_MODEL`. The AI judge's answers are cached in the system temporary directory
(`CHECK_JUDGE_CACHE`), never in the repository.
