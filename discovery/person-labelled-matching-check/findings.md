# Person-labelled matching check: which way of matching holds up when a person judges its pairs

**Kind of hop: a measurement with an instrument for people.** It runs six ways of proposing quote-to-priority pairings over real San Francisco captions and donor priorities, builds a blind sheet of the pairs they propose, and scores the ways against what people label. It makes no decisions. **No person has labelled a pair yet, so no figure in this repository is a person's judgement.** What exists is the method, the blind sheet and labelling page that a person works through, and a script that turns their files into every figure the charter asks for. The measured results are not typed here: `python method/run.py` writes them, with the same inputs and seed, to `results.md` (tables), `results.json` (the same figures as data, the comparable output) and `matches-that-stand-out.md` (the instances the proof point asks for). Read `results.md` first; this file says what is measured, how, and how far it can be trusted.

Builds on `../matching-methods-comparison/findings.md` (the six methods, their inputs and the language model's labels; its figures were never saved, which is why this hop's script writes them down), `../matching-trial-run/findings.md` (the chance model and the first lexical figures), `../donor-priorities-survey/findings.md`, `../quote-attribution-check/findings.md` (the caption text carries no speaker) and `../campaign-finance-survey/findings.md`.

## Where things are

| What | Where |
|---|---|
| Measured results, chance count at every setting of every method | `results.md`, `results.json` (written by the run) |
| Pairs that meet every condition of the proof point | `matches-that-stand-out.md` (written by the run; zero instances until a person labels) |
| The page a person labels in (self-contained HTML, times each label) | `labelling/label.html` |
| The blind sheet it shows, and the key saying which method each pair came from (labelers must not open the key) | `labelling/blind-sheet.json`, `labelling/sheet-key.json` |
| Where people's label files go, and their format | `labelling/person_labels/` |
| Scripts, tests and the snapshot of the sources | `method/` (`run.py` drives; `check_lib.py` holds the arithmetic) |

The sheet and its key are written once, by the first run, and never rebuilt unless `REBUILD_SHEET=1` is set, so labels already given stay valid.

## What was run

**Inputs, the same as the earlier comparison** (`method/data/`, copied so this directory builds on its own): 3,065 substantive passages cut from the Legistar caption transcripts of 11 Board and committee meetings (January to July 2026), raw and in capitals, each with its caption stamp and transcript link; 133 class-A priority statements in the donors' own words from six organisations, each with its URL, section and retrieval date. 407,645 pairs. A speaker is never given: the captions do not name one.

**Methods** (`method/run.py`, `method/stages.py`): keyword overlap (TF-IDF cosine), keyword overlap with a shared rare phrase, a shared named thing, embedding similarity (`BAAI/bge-small-en-v1.5` by `fastembed`, no account), an AI judge, and an embedding shortlist (top 100 pairs) confirmed by the AI judge. The first four each propose every pair at **their setting: the loosest level at which random-word quotes give fewer than one pair per run on average** (the earlier trial's definition; 15 draws per chance model for the lexical methods, the worse of the pooled and within-meeting models; 8 draws of 500 random-word quotes, scaled up, for the embedding). The AI judge (`claude-haiku-5-5`, one call per pair, overlap real/loose/none, speaker type, stance) cannot read all 407,645 pairs, so it reads a **pool**: every lexical proposal, the top 300 embedding proposals, the shortlist and 150 random pairs. Its proposals are the pool pairs it reads as a real overlap by a speaker who may be an official. Consequences, all printed in `results.md`:
- The AI judge's chance count at a setting cannot be shown under one per run by sampling: it is reported as the number of random-word passages it flags (of 100) and marked "not established". A pair proposed only by the AI judge therefore cannot count toward the proof point.
- The shortlist's chance count is bounded above by the embedding's chance count at the shortlist's lowest score; it counts toward the proof point only when that bound is under one.
- Misses by the AI judge outside its pool are not measured.

**The blind sheet.** For each method up to 12 of its proposals, 5 pairs just below each lexical method's and the embedding's setting (the next looser level, which show what loosening buys), and 12 random pairs, in a hash order, as one deduplicated list (about 70 to 110 pairs). A pair shows the exact caption words with meeting, date, stamp and transcript link, the caption words just before it (a speaker's cue may be there), and the donor's exact statement with donor, section, source link and retrieval date. It shows no method, score, setting or reading. `check_lib.leaks_method` is asserted over every entry when the sheet is built, and the sheet's HTML does not contain the key.

**What a labeler gives** (`labelling/label.html`): overlap (real: the same specific measure, program, proposal or stated position; loose: the same broad subject; none), whether the passage and the priority take the **same side, opposite sides, or neither or unclear**, and who seems to be speaking (an official for themselves, someone else, can't tell). Side and speaker are asked only where overlap is real or loose. Each label is timed from the pair appearing to Next (wall-clock, plus the time the page spent in a background tab, since opening a transcript is part of judging). The order differs by labeler name. The file states `blind: true`, a statement that the labeler is a person and saw no output; `run.py` does not count a file without it.

**What `run.py` reports from labels** (`method/check_lib.py`, tested in `method/tests/`): per method, the share of labelled proposals judged real with a 95% Wilson range, an estimate scaled to all its proposals, and the real overlaps it misses among those people judged real; the share of labelled proposals that take the opposite side; labelled pairs at or above each setting beside the corpus count and the chance count; the AI judge's reading against people; time per label (median, quartiles, 90th percentile, a projection for 10 to 100 pairs, by overlap given and by labeler, labels over five minutes set aside as idle and counted); and for two or more labelers, agreement and Cohen's kappa on overlap and side with the pairs where they differ. Where labelers differ the lower middle overlap level is the label and any "opposite" counts as opposite, so the figures lean against a pair.

## What the findings say about the charter questions

1. **Share of proposals a person judges real, and misses.** Not measured: no person has labelled. The instrument that measures it is built and tested; `results.md` section 2 holds the table once `labelling/person_labels/` has a file. Until then it holds the AI judge's reading of every proposal it read (labelled MACHINE), which is a language model's and not independent evidence for the AI methods.
2. **Real overlaps found at the setting where chance is under one per run.** Partly. Each method's setting, its corpus count and its chance count at every level are written by the run (`results.md` section 1), and need no person. The count of real overlaps at that setting needs a person's labels (`results.md` section 3). The earlier trial's lexical figures, against a model's and the trial author's labels and not a blind person's, are in `../matching-trial-run/findings.md`.
3. **Opposite sides on real quotes.** Not measured by a person. The page asks it of every real or loose pair. `results.md` section 4 shows the AI judge's stance reading on each method's proposals as a MACHINE row. The earlier comparison's opposing-side count used 14 hand-written probes, not real quotes.
4. **Time per label, and where labelers disagree.** Not measured: no timed label and no second labeler exist. The page records the time of each label and the script reports medians, a projection for a night's candidates and the pairs where two people differ.

## What this hop must show: matches that stand out

Not shown. An instance needs a method's proposal, a person who is not the run labelling it blind as a real overlap on the same side, a real caption, and the method's chance count under one at that setting. The first, third and fifth are produced by the run; the second is not available, and nothing else stands in for it: the earlier trial's reader labels were reconciled with the model's and were not blind, and an AI judge's reading is the run. `matches-that-stand-out.md` is written by the run: it lists instances as soon as label files exist (with the quote, stamp and link, the priority and its source, the proposing methods with their chance counts, the labelers, their side and speaker readings and label times), and until then says "None" and lists candidates (proposed by a method whose chance is under one, read by the AI judge as a real, same-side overlap by an official or an unclear speaker) for whoever labels next. A labeler should label before opening that file.

## What drowns a match, from what is already known

Carried from the earlier trial and comparison, not re-measured here: a clerk reading a measure's title matches every statement about the measure and is not an official's statement; public comment, applicants and presentations look like speech on the issue; names collide ("Prop C", "Great Highway"); broad priorities attract passages about the subject with no shared position; and a low chance count does not mean a reader finds the pair meaningful. The labeler's speaker question measures how much of this a person sees.

## Open questions

**Looked for and not found**
- Any label by a person who is not the run. Looked at: `../matching-methods-comparison/data/`, `../matching-trial-run/data/labels.json` and `labels_model.json`, and the other discovery directories. The only labels are a language model's and the trial author's, reconciled with each other.
- Any timing of a person judging a pair, in any earlier findings.
- Any person's reading of whether a quote and a priority take the same side.
- The measured results of the earlier comparison (it saved none); this hop's run is the first to write them.

**Who must supply what**
- Maintainer, or one to three people they name (a reporter, a resident, a civic-group member): open `labelling/label.html`, label the sheet without opening `results.md`, `matches-that-stand-out.md` or `labelling/sheet-key.json`, and put the downloaded file in `labelling/person_labels/`. About 70 to 110 pairs; the page saves progress and its order is random, so a part-finished file is still an unbiased sample. Two labelers are what measure where people differ; the proof point needs ten labelled pairs that meet every condition.
- Maintainer: whether a clerk's, a staff member's or a commenter's passage can count as "what an official said". The page records the speaker so either reading can be computed; which one counts is theirs to say.
- Maintainer: a cap on the AI cost per night; `results.md` gives the cost and time per pair read.

**Claims not verified**
- That `claude-haiku-5-5` and its price (from $0.10 per million input tokens and $0.50 per million output tokens) are current when a later run happens: read on Anthropic's models overview on the day of writing, which lists it as current (Claude API ID `claude-haiku-5-5`); models are retired on a schedule. The name is in one place (`judge.DEFAULT_MODEL`, override `MATCH_JUDGE_MODEL`). A retired model, a missing key or an unreadable reply is reported in `results.md` and makes the run exit 1; nothing substitutes for it.
- That `fastembed==0.9.1` is the latest release (PyPI listed it as latest on the day of writing) and that `BAAI/bge-small-en-v1.5` suits captions in capitals once lower-cased (recalled that its tokenizer is uncased).
- The embedding stage and the shortlist have been exercised in this repository only with a stand-in embedder for the mechanics (sets, thresholds, tables); no figure for them from the real model is quoted in this file, and the first record of them is the run's `results.md`.
- That the lexical chance counts reproduce the earlier trial's (the chance draws differ in number: 15 here against 20 there, so a setting near one pair per run can move one level).
- That the 133 priorities are each exactly the donor's page text (the earlier comparison checked one against its source).

## Sources used

- Anthropic, Models overview (`https://platform.claude.com/docs/en/about-claude/models/overview`, canonical `https://platform.claude.com/docs/en/models/overview`) for the current model id and price.
- `fastembed` on PyPI (`https://pypi.org/pypi/fastembed/json`) for the pinned version.
- The earlier findings in this repository, linked at the top, and their data, copied to `method/data/`.
