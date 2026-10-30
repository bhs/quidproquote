# Matching methods comparison: which way of pairing a quote with a donor priority to propose pairings for review

**Kind of hop: a survey with a measurement.** It builds a repeatable comparison of six ways of proposing quote-to-priority pairings on identical inputs and scores them against labelled pairs. It makes no decisions. **The numbers are not in this file**: `python compare.py` writes them, with the same inputs and seed, into `results.md` (tables), `results.json` (the same figures as data), `pairs-review.md` (the pairs, readable) and `labelling-sheet.json` (the pairs for people to label). Read `results.md` first for the figures behind the five charter questions; this file says what is measured, on what, and how far it can be trusted. **The standard the figures are measured against is a language model's labels, not people's**, so every precision, miss and threshold figure is agreement with a model's reading until people fill `data/person_labels/`.

Builds on `../matching-trial-run/findings.md` (the lexical ways, chance model and two judges' labels, whose data and code are copied here so this directory builds on its own), `../donor-priorities-survey/findings.md` (class-A donors), `../quote-attribution-check/findings.md` (speaker is not in the caption text) and `../campaign-finance-survey/findings.md` (committees tied to officials; the source of `data/committees.json`).

## What was run

**Inputs, the same for every method.**
- **Quotes: raw captions, not confirmed quotes.** 3,065 substantive passages cut from the Legistar caption transcripts of 11 Board and committee meetings (January to July 2026), all capitals, with the caption stamp and transcript link. Nothing was confirmed against a recording. Every speaker is a *proposal*: `compare_lib.propose_speaker` reads a spoken cue ("District 7 Supervisor X") near the passage, matches the garbled name to the roster by spelling and reports basis and caution; roll calls and ambiguous spellings propose nobody.
- **Priorities: class-A donors in their exact words.** 133 statements from six donors' own pages, each with its URL, section and retrieval date (`data/priorities.json`, 29 October 2026; see *Source of the priority wording* below): Chamber of Commerce, GrowSF, Blueprint (Neighbors for a Better San Francisco), SEIU Local 1021, the Police Officers Association and Airbnb. All are organisations; no individual donor has a fetchable class-A page.
- **Items scored** (`compare.make_items`): the 135 labelled pairs; 150 random quote-priority pairs (fixed seed, unlabelled, almost all unrelated, a measure of false alarms); 14 synthetic probes (seven measure statements, a passage on the priority's side and one on the other side, both in its words); and, for every labelled pair and probe, a twin with caption errors injected in names, numbers and vote words (rate 0.5 of eligible words; the real rate is not known).

**Methods** (`compare.METHODS`).
1. *Keyword overlap*: TF-IDF cosine over stemmed content words; the cut is the lowest level at which random-word quotes give fewer than one pair per run (the trial's definition).
2. *Keyword overlap, tighter*: that cosine together with a shared rare two-word phrase.
3. *Shared named thing* (measure, name, acronym): added because the trial found it the most selective lexical way.
4. *Embedding similarity*: cosine of sentence embeddings from a local open-weights model (default `BAAI/bge-small-en-v1.5`, run with the `fastembed` library, no account); the cut is chosen the same way against random-word quotes.
5. *AI judge*: one model call per pair returns overlap (real / loose / none), speaker type, stance against the priority and a one-line reason. A pair is *proposed* when overlap is real and the speaker may be an official (a clerk, commenter or staff passage is not).
6. *Embedding shortlist confirmed by the AI*: the top 100 pairs by embedding over all 407,645, each read by the same judge.

**Scoring.** Against the labels, in two views: *review-ready* (a clerk's or commenter's passage counts as no overlap) and *overlap* (those pairs left out). Per method: precision for real overlap with a 95% range, real overlaps missed, flags among random pairs, candidates over all pairs, cost and time per pair, the AI judge's stance on what each method proposes, how many opposite-side probes each proposes, a threshold sweep against chance, and how proposals change under caption errors.

**Labels.** No person has labelled a pair. The labels are the earlier trial's: a language model's for all 135 pairs (used as gold) and one reader's for 95. They map meaningful→real, topical→loose, coincidental→none, not a quote→none or left out. Two limits matter. The AI judge is also a language model, so agreement with these labels is not independent evidence. The labelled pairs were drawn from lexical methods' candidates, so a miss by the embedding or AI methods anywhere else is not measured; `labelling-sheet.json` queues the shortlist's new finds, and `data/person_labels/` takes people's labels (the run then uses them as gold and reports where labelers differ).

**What is shown per pair** (`pairs-review.md`): the exact caption, its meeting, date and stamp with link; the cited priority with donor, section, link, retrieval date and page date; each method's decision; the label; the AI's reading and reason; the proposed speaker; and the donor's reported Schedule A money by committee (the proposed official's committees when a speaker is proposed, else the largest). Money is queried from the Ethics Commission's Transactions dataset on DataSF by contributor name (there is no donor identifier), per committee, never added across committees, with no statement about cause.

**Source of the priority wording.** Each statement is the text of the donor's own page as retrieved. One was checked against the published source after copying: the Chamber's Proposition 43 statement (P048, `https://sfchamber.com/november-2026-voter-guide/`). The page's text layer prints the fraction in two places as a bare "3" ("require 3 voter approval", "require 3 approval"); the Chamber's voter guide PDF it links (`https://sfchamber.com/wp-content/uploads/2026/10/SFCc-November-2026-General-Election-Voter-Guide.pdf`, page 3), read on the page image, prints "⅔" in both, and the same statement's first sentence says "two-thirds vote". `data/priorities.json` carries "⅔" in both places, so P048 matches the published wording. The same loss of a fraction glyph can affect any statement copied from a page's text layer; a scan of the other 132 for a stray single digit found no further lost fraction (P035's "first 3 years" is the page's own wording, confirmed in the same PDF), but the statements were not each re-read against their pages. `../matching-trial-run/data/priorities.json` is the earlier copy and still has the bare "3".

## Settings and dependencies

- Judge model `claude-haiku-5-5`, named in one place (`judge.DEFAULT_MODEL`, override `MATCH_JUDGE_MODEL`); Anthropic's models overview listed it as current when this was written, with an API id of that name and prices from $0.10 per million input and $0.50 per million output tokens (the cost lines use those; override with `MATCH_JUDGE_PRICE_*`). API version header `2026-10-21` (the latest on the versions page; override `ANTHROPIC_API_VERSION`). A retired model, a missing key or an unreadable reply is reported as NOT RUN or an error in `results.md` and makes the run exit 1; nothing substitutes for it.
- Embedding library `fastembed==0.9.1` (Apache-2.0, ONNX, CPU; the release listing read on libraries.io showed it as the latest). The embedding model is a choice later Hops may compare; it is configurable (`EMBEDDING_MODEL`).
- Run time: the run must finish in minutes on a CPU, so the embedding method's chance level is drawn from a random sample of 500 chance quotes per draw (`EMB_NULL_QUOTES`), counts scaled up to the full corpus; the AI judge stops starting new calls after 600 s (`MATCH_JUDGE_TIME_BUDGET_S`).
- `ANTHROPIC_API_KEY` is the only secret (results runs only).

## What this says about the charter questions

The figures are in `results.md` and `results.json`, written by each run of `compare.py`; they depend on a live AI judge and the embedding model, so they are produced by running it, not typed here. What each question reads, and its limit:
1. **Precision, misses, cost, time.** `results.md` section 1 and its cost table. Precision and misses are against the model's labels (the gold), not people's; the 95% ranges are Wilson ranges over 135 labelled pairs, wide for any method with few proposals. Misses are counted only among the labelled pairs, which came from the lexical methods' candidates. Cost and time per pair for the AI judge are measured from calls; a full run of the AI judge over every pair is projected from the per-call figures, not run.
2. **Opposing positions that share topic words.** Section 2 counts them two ways: the AI's stance reading on each method's proposals, and the synthetic probes. The probes are 14 hand-written statements (for each of seven measures, one passage on the priority's side and one on the other side, both in its words), so they show whether a method can tell sides apart, not how often opposed pairs occur in real captions. Stance is the AI's reading, not a person's. The trial's labels did not judge stance (its rubric ignored it), so no human stance label exists.
3. **Real overlaps against chance, and the threshold.** Section 3: per method a sweep with gold-real, other labelled, random and random-word counts at each level, plus AUCs. The chance model is random words, which the trial showed removes only pairs needing no real shared content. The chosen threshold is the lowest level at which random-word quotes give fewer than one pair per run; the real-overlap counts at that level are those the model labelled real.
4. **Where labelers disagree.** Between the trial's reader and model on the 95 shared pairs, 4 differ, on 2 passages, each between neighbouring classes (topical against meaningful three times, coincidental against topical once); three are one passage against three Prop J statements, where the passage is about the measure's revenue and the priorities take positions on the measure. That is an upper bound on agreement because the reader's file was reconciled with the model's. Disagreement between people is not measured. Section 4 also lists where the AI judge departs from the labels, with its stated reason.
5. **Caption errors.** Section 5: with injected errors, how many proposals each method loses or gains, how many lost ones were gold-real, and how often the AI's stance changes. The injected rate (half of eligible words) is a stress setting, not a measured rate; the observed rate of caption errors per quote is not known, so the figures show how sensitive each method is, not how often it is affected.

## Open questions

**Looked for and not found**
- Any label by a person, so precision against human labels is not measured. A model's labels stand in as the gold. Looked at: `data/`, the earlier findings. `data/person_labels/` and `labelling-sheet.json` are the route.
- A human reading of stance for any pair. None exists in the repository.
- A rate of caption error per quote against a recording (the earlier surveys had no audio). The injected-error figures show sensitivity, not frequency.
- A reviewer's timing of a check. Still none.
- Donor-name variants beyond those in `money.DONOR_NAME_WORDS`; money by committee is a name match and can include other organisations with the same words or miss spellings.

**Claims not verified**
- That the model and prices named above are current at the time of any later run (read from Anthropic's models overview on the day of writing; models are retired on a schedule).
- That the DataSF query returns what the campaign finance survey's profile reports for the same committees (no cross-check was made).
- That the proposed-speaker rule is accurate: it is the spoken-cue route from `../quote-attribution-check/findings.md`, untested here against a labelled transcript.
- That `BAAI/bge-small-en-v1.5` suits captions in capitals once lower-cased (recalled that its tokenizer is uncased).

**Questions for people**
- Maintainer: is a clerk's reading of a measure's title ever quotable as "what an official said", and does a department head's or applicant's statement count as an official's quote? These decide whether the review-ready view (clerk and staff passages as no overlap) or the overlap view is the one that counts.
- Two or three reporters or residents: label `labelling-sheet.json` without seeing any output and time a verification of ten kept pairs; that would give the first independent test of these figures and the key results waiting on timing and on what stands out from chance.
- Maintainer: a cap on the AI cost per night, since the AI judge over every pair is far costlier than a shortlist.

## Sources used

- Anthropic, Models overview (`https://platform.claude.com/docs/en/about-claude/models/overview`) for current model ids and prices; Versions (`https://platform.claude.com/docs/en/api/versioning`) for the API version header.
- `fastembed` release listing and README as shown at `https://libraries.io/pypi/fastembed` (version 0.9.1, default model BAAI/bge-small-en-v1.5).
- Ethics Commission Transactions dataset on DataSF (`https://data.sf.gov/resource/pitq-e56w.json`, queried by `money.py`).
- Earlier findings in this repository, linked at the top.
