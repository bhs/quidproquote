# Worked pairing examples: six San Francisco pairings of an official's exact words, a donor's own priority and the money, and where each broke

**Kind of hop: a survey** of real sources outside the project (the city's caption transcripts, donors' own published statements, the Ethics Commission's campaign finance data and a few news and election pages), written as **findings**. It assembles worked examples and records every point where one could not be completed. It makes no decisions.

**The pairings themselves are in `pairings.md`** (written by `python build_pairings.py`; method, snapshot and inputs sit beside it in this directory). This file says what they show, how far each part can be trusted, and what the Hops after this one should take from them. **No money figure is typed in this file**: the money sections of `pairings.md` are produced by the script from the Ethics Commission's DataSF dataset, and a section that reads "Not retrieved in this build" has not been filled yet.

Builds on `../matching-methods-comparison/findings.md` (the comparison of ways of matching; its code and snapshot are copied here), `../quote-attribution-check/findings.md` (speaker is not in the caption text), `../campaign-finance-survey/findings.md` (committees tied to officials; 24-hour reports; amendments) and `../donor-priorities-survey/findings.md` (donor statements).

## Summary by charter question

1. **Can every part of a pairing be filled, and where does it break?** Partly, and the break points are specific. In all six pairings the official's exact caption words, the meeting, the date and the transcript stamp, the donor's own words with a link and retrieval date, and the list of committees tied to the official are filled from the sources. Three parts break or need a person: (a) the **speaker**, which the transcript text alone gives with low doubt in two of six pairings, medium in two and high in two, and which needed an outside page (a sponsor record) in three; (b) the **link from the transcript stamp to the recording**, which no source here resolves, so a quote cannot yet be offered as "play this moment"; (c) **whether the donor's sentence is a position** on what the official said (one candidate, the Chamber's Prop J statement, turned out to say the Chamber abstained). The money by committee and filing is queried by the script; its figures are not in this file (see "Money" below).
2. **Which money should stand beside a pairing?** Schedule A rows (monetary contributions) of the donor, listed by committee and filing and never added across committees, filings or forms; the official's own candidate and officeholder committees as the headline; committees formed to support or oppose the official, and ballot-measure committees, shown apart and labelled; 24-hour reports listed apart and never added to Schedule A. The rules and the reasons are in "Which money stands beside a pairing" below.
3. **How is each quote credited to an official from the transcript text alone, and how often is that credit in doubt?** By a spoken cue (the chair or clerk calling a member, or the member's own words such as "District Ten"), read by a person. The comparison's automatic cue rule agrees with that credit in **one of six** pairings: it names nobody for one, and a wrong member for four. Credit was in doubt (medium or high) in four of the six. Across the 3,065 substantive passages the rule proposes any speaker for 247 (8%), and for 4 of the 19 passages the trial's model labelled meaningful. Details in "Speaker credit".
4. **How much needed a person's judgement, and at which step?** Of six steps per pairing, two are done by rule (finding the pair by shared named things; listing the committees tied to the official). Of the other four, three needed a person every time (where the quote begins and ends; whether the donor's sentence is a position; whether the names the money query returns are the donor) and the speaker credit needed one in five of six. Table in "Judgement".

## What was put together

| # | Official | Words (meeting, transcript stamp) | Donor and statement | Doubt in speaker credit | In `pairings.md` |
|---|---|---|---|---|---|
| 1 | Myrna Melgar (Supervisor, D7) | Board of Supervisors, 14 July 2026, 01:07:48 | San Francisco Chamber of Commerce, Prop C (P036) | low | line 16 |
| 2 | Chyanne Chen (Supervisor, D11) | Board of Supervisors, 7 July 2026, 00:15:56 | Neighbors for a Better San Francisco (Blueprint), Prop B (P055) | medium | line 69 |
| 3 | Bilal Mahmood (Supervisor, D5) | Budget and Finance Committee, 15 July 2026, 02:52:31 | GrowSF, Prop J (P107) | high | line 124 |
| 4 | Bilal Mahmood (Supervisor, D5) | Budget and Finance Committee, 15 July 2026, 02:53:29 | Neighbors for a Better San Francisco (Blueprint), Prop J (P063) | high | line 179 |
| 5 | Shamann Walton (Supervisor, D10) | Board of Supervisors, 14 July 2026, 02:39:58 | San Francisco Chamber of Commerce, Prop E (P038) | low | line 233 |
| 6 | Chyanne Chen (Supervisor, D11) | Board of Supervisors, 14 July 2026, 02:57:26 | GrowSF, Prop C and the inclusionary fee cut (P083) | medium | line 291 |

Each pairing section holds, in order: a lead for a reporter's look, the exact words, the meeting, date, stamp and transcript link, the speaker credit and how the text supports it, the donor's words with the source link and retrieval date, why the two sit side by side, where a person's judgement was needed, and what a reporter could check next. The money sits in `pairings.md` under "Money" (one section per pairing, after the six pairings, so the pairings keep their place when the money rows change).

Positions as read (my reading, and shown as such in the file): pairings 1 and 3 are on the same side on the text (the donor's page supports the measure the official is presenting); pairings 2, 4, 5 and 6 are on different sides. Two pairings (3 and 4) put two donors on opposite sides of the same measure beside the same sponsor's speech.

**How each came by.** Pairings 1, 2, 5 and 6 are passages the earlier trial's model labelled meaningful against the donor statement, found by the lexical ways (shared named things, shared phrases). Pairings 3 and 4 are not: the trial's labelled Prop J passages were Assessor-Recorder data and an analyst's estimate with no speaker cue found, so the sponsor's own sentences were found by reading the transcript around the sponsor's introduction. Under the trial's calibrated lexical settings, four of the six pairs clear at least one (pairs 1, 2, 5 and 6; pairs 3 and 4 clear none), so a purely lexical nightly run would have surfaced four of these six.

### The matching used, and its limit

The comparison's figures (`results.md` of `../matching-methods-comparison/`) are not in the repository, and its findings name no favoured way. The pairings therefore use the route the earlier findings describe as most selective: candidates from shared named things and phrases, each then read by a person for real overlap and for whether an official is speaking (the role the comparison gives to an AI judge). The reader here is the author of the pairings, a language model, so these reads are not independent of the earlier trial's model labels; no pairing was read by a person outside the work (see Open questions). Scores of each pair under the trial's three lexical ways are shown in section N.4 of each pairing.

## Speaker credit

All six credits are a person's reading of the caption text, as the earlier survey found necessary (the transcript has no speaker names). What each rests on:

| # | What the text shows | Automatic cue rule | Outside the transcript |
|---|---|---|---|
| 1 | The row opening the turn is "SUPERVISOR MELGAR THANK YOU MR. PRESIDENT." | Melgar (agrees) | Two pages say Melgar introduced the measure; corroboration only |
| 2 | "SUPERVISOR CHEN THANK YOU FOR PRESENT" opens the turn, and the speaker says "my charter amendment ... public bank". Chen and Chan differ by one letter | Nobody (the cue is further back than the 40 words it reads) | Three pages name Supervisor Chyanne Chen as the sponsor; **needed** |
| 3 | The chair is told "today we have Supervisor" and the next row reads "BALA MAMU HERE"; the speaker then thanks his co-sponsors by name | Connie Chan, from the chair's name (wrong) | The Department of Elections' legal text and a news report name Supervisor Mahmood as sponsor; **needed** |
| 4 | Same turn, 40 seconds on, with a ">>" mark before the passage | Matt Dorsey, from the thanks to co-sponsors (wrong) | As 3; **needed** |
| 5 | Called by name three minutes earlier; says "District Ten" and thanks Chen and Fielder; the chair moves on after "the rest I submit" | Jackie Fielder, from the thanks (wrong) | None used |
| 6 | A member asks who moved to rescind ("a Supervisor Chen"), then "if she chooses a Supervisor Chance to answer", and the passage answers in the first person | Connie Chan, from "CHANCE" (wrong) | None used; the minutes were not read |

What this says:
- **Name garbling decides the credit.** The captions render the same officials as CHEN, CHIN, CHANCE and CHAN, and Mahmood as "BALA MAMU". The earlier survey's table of renderings predicted this; here it decided four of six credits (pairings 2, 3, 4 and 6). The rule named a wrong member in four cases: two by fuzzy-matching a garbled name to the roster (pairings 3 and 6) and two from the names of colleagues being thanked (pairings 4 and 5).
- **Names near a passage are often not the speaker.** Thanks to colleagues (pairings 4 and 5) and the chair's name (pairing 3) sit in the 40 words before a passage and read as cues.
- **Where the rule speaks, it is mostly wrong in this set.** Of the four of the trial's 19 meaningful passages for which it proposes a speaker, it is right for the Melgar opening used in pairing 1 and wrong for the Chen passages at 7 July 00:16:27 (the speech of pairing 2, which thanks Melgar by name) and 14 July 02:57:26 (pairing 6); the fourth (14 July 01:40:34, Melgar) was not read for correctness (unverified). No claim of a rate follows from six hand-chosen pairs; the figure is that the rule agreed with a careful reading in one of six.
- **What this shows for a first site:** a displayed speaker that came from the cue rule alone would have been wrong in four of six pairings here, and absent in one.

## Which money stands beside a pairing

The money sections follow rules taken from `../campaign-finance-survey/findings.md` (sections 3 and 4) and applied by `pairing_lib.summarise_money`:

- **Schedule A only, per committee.** Monetary contributions (Schedule A rows) of contributors whose name contains the donor's name words, listed one row per contribution with committee, filing id, filing date, the version of the filing, the contribution date, the amount and the contributor name as filed. Never added across committees, filings or forms; the only totals are per committee, over Schedule A.
- **The official's own committees are the headline.** `data/committees.json` ties committees to each official; `Candidate or Officeholder` and `470 [Officeholder]` committees are treated as the official's own. Committees formed to *support* or *oppose* an official are third-party money about the official, not to the official (the survey's example is a GrowSF committee opposing Chan), so they are labelled in the money section and never merged into a headline. Ballot-measure committees naming an official (the Mayor's) are a third kind and likewise labelled. For the officials in the six pairings only own committees and one supporting committee (Walton) exist; the labels are in place for the others.
- **24-hour reports (Form 497 part 1) never add to Schedule A.** The survey found 2,865 of 4,470 such rows since 2022 have a matching Schedule A row (same committee, date, amount). A row repeating a Schedule A row is listed as a repeat and not counted; a 24-hour row with no Schedule A counterpart yet (a contribution not yet in a periodic report) is listed apart with its own total, not in the committee's Schedule A total.
- **Amendments.** The Transactions dataset keeps only the latest submission of each report, so one reported contribution is one row and the filing's version is shown so a reader can see it was amended. There is no change history, so "what the donor was recorded as giving on date X" cannot be reconstructed from this dataset.
- **Memo rows** are listed and not summed, since a memo entry is information inside another entry (recalled from how Form 460 treats memo items; not checked against the Commission's instructions in this work).
- **A match is by name words** (no donor identifier exists): the contributor name as filed is shown on every row, and a sponsored committee (such as a political committee that carries the Chamber's name) matches the same words and is a different filer from the Chamber; whether it counts as the same donor is a policy choice the sheet leaves to the reader.
- **Zero rows is an answer, with its limits stated**: unitemized contributions carry no name, other spellings are missed, and committees outside the snapshot of committees are not searched. The snapshot lists one terminated committee for Chen and only terminated committees for Walton, so money to either official's current committee, if one exists, would not appear. Whether newer committees exist was not checked (unverified).

## Where each part broke, and what filled the gap

| Part | Result | What filled it, or what is left |
|---|---|---|
| Exact words | Filled for all six | Verbatim from the Legistar caption text; `build_pairings.py` refuses to build if a quote is not found word for word. The wording is caption-grade (for example "ONE OF THOSE STRATEGY THAT IS NEEDED"); not checked against the recording, as the approach sets out |
| Meeting, date, stamp | Filled | Meeting body and date from the snapshot; stamp is the caption row's |
| Link to the recording at the stamp | **Not filled** | The earlier survey found no source linking a transcript stamp to the archived video; the pairing shows the transcript link and stamp only |
| Speaker as an official | Filled, with doubt | See "Speaker credit"; outside pages needed for 3 of 6 |
| Priority in the donor's words with link and date | Filled | `data/priorities.json` (retrieved 29 October 2026); six statements from three of the six donors. A fraction glyph lost from a page's text layer can affect a copied statement (the comparison found one); these six contain none |
| Whether the donor's sentence is a position | Needed a person | A candidate pairing with the Chamber's Prop J statement was dropped because that statement says the Chamber abstained |
| Committees tied to the official | Filled, with a limit | Snapshot of committees, which can be out of date for current-cycle committees |
| Money by committee and filing | Produced by the script at run time | Not typed here; see `pairings.md`. A query failure is printed in place of the figures and makes the run exit 1 |
| Priority for an individual donor | Not attempted | No individual donor has a fetchable class-A page (comparison findings); all three donors here are organisations |
| Donor coverage | Three of six | No pairing uses SEIU Local 1021, the Police Officers Association or Airbnb: none of the earlier labelled passages for them was about an official's stated position on a named measure. Mahmood's sentence thanking "SEIU 2015 and SEIU 1021" at 02:53:21 to 02:53:29 names a donor directly; no priority was paired with it |

Candidates looked at and not used are listed in `pairings.md` ("Candidates looked at and not used"): a public commenter's Great Highway remark (not an official), the Prop J passages paired with an abstaining statement or relaying an analyst's estimate, two speeches with no speaker cue, and two spare pairings from speeches already used.

## Judgement

| Step | By | Where it needed a person |
|---|---|---|
| Finding the pair | Rule | Four of six clear a calibrated lexical setting; pairs 3 and 4 were found by a person reading around the sponsor's introduction |
| Quote boundaries (where a quote starts and ends) | Person, every time | The passage cuts of the earlier trial are fixed-length; a quotable unit needed choosing |
| Speaker credit | Rule in one of six; person in five | Garbled or ambiguous names (pairings 2, 3, 4 and 6), cues that are not the speaker (3, 4, 5 and 6), no cue near the passage (2 and 5) |
| Is the donor's sentence a position | Person, every time | One candidate dropped; one pairing's quote describes the official's authorship without stating how the speaker will vote |
| Committees tied to the official | Rule | A person decides whether a committee formed to support or oppose an official stays out of the headline; the rule here does so by name |
| Donor name variants | Person, at review | Names returned by the query have to be read; not done until the money sections are filled |

For the review screen of a first site, what a reviewer is shown before a pairing appears should include: the quote with its rows, the cue rows and the doubt, the outside page where one was used, the donor's sentence and link, and the money rows with the contributor name as filed.

## How this serves the objectives

- *Everything shown is current and correct*: quotes are verified verbatim against the snapshot by the script; the priority dates and the transcript retrieval dates are on every pairing; money is timestamped by the script with the dataset's last load date.
- *Let a reporter quickly understand pay-to-play speech*: each pairing is a one-screen lead with its own checks. The key result that waits on timing reporters is not met here: nobody was timed.
- *Only surface things that are meaningful*: two of the six pairs would not have cleared a calibrated lexical setting, and a dropped candidate had lexical overlap and the wrong kind of speaker, so lexical scores alone do not decide what stands out. How many pairs look alike by chance is the trial's figure and was not re-measured.

## How to regenerate

`python build_pairings.py` (network needed for the money; reads `picks.json` and the snapshot in `data/`), `--no-money` to build without the network, `--from-snapshot` to re-render from `data/money_snapshot.json`. `python -m unittest discover -s tests` checks that every quote is verbatim, that every pairing is complete, and that no lead uses a causal word. Dependencies: the Python standard library only.

## Open questions

**Looked for and not found**
- The comparison's own results (`results.md`, which way it favours): not in the repository; looked in `../matching-methods-comparison/` and its history.
- Any link from a transcript stamp to the same moment in the archived video: not in any source read here or in the earlier surveys.
- A rate of caption error per quote against the recording: still none.
- Minutes of 14 July 2026 and 15 July 2026 (who moved, who spoke): not read; would settle pairing 6 and could confirm 3 and 4.
- Money figures: the script queries DataSF; none was read when this was written, so the amounts, the number of rows and whether any donor appears at all in a given official's committees are unknown to this file.
- Current-cycle committees for Chen, Mahmood and Walton beyond the snapshot of committees: not checked.

**Claims not verified**
- That the sponsor pages named as outside sources say what the file attributes to them was read from search extracts, not the full pages (unverified).
- That the Department of Elections' legal text for the Prop J measure (file 260692) lists Mandelman as a sponsor while the sponsor's spoken thanks omit him is a reading of caption text that may be garbled (unverified).
- That memo rows are not part of Form 460 totals (recalled).
- That 14 July 01:40:34 is Melgar speaking (unverified).
- That the stamp-to-speech lag of live captions is small enough for a stamp to find a quote (published figures of 4 to 8 seconds are in the earlier survey; none measured on this recording).

**Questions for people**
- Two or three reporters or watchdogs: verify these six pairings from the files alone, with the clock running, and say which step took longest. That is the timing the key result waits for.
- Maintainer: should a pairing whose speaker credit rests on an outside sponsor record (pairings 2, 3 and 4) appear on a first site, or only those a reader can confirm from the transcript alone (1, 5 and with doubt 6)?
- Maintainer: is a committee formed to support an official (not the official's own) ever "money given through committees tied to that official", or only shown apart as here?

## Sources used

- Legistar caption transcripts of the Board of Supervisors (7 and 14 July 2026) and the Budget and Finance Committee (15 July 2026), as copied in `data/transcripts/`, retrieved 29 October 2026.
- Donors' own pages, as copied in `data/priorities.json`: `https://sfchamber.com/november-2026-voter-guide/`, `https://sfblueprint.org/advocacy/november-2026-voter-guide`, `https://growsf.org/voter-guide/san-francisco-voter-guide-november-2026-election/measures/` (pages for Props B, C and J).
- San Francisco Ethics Commission campaign finance Transactions dataset on DataSF, `https://data.sf.gov/d/pitq-e56w` (queried by `build_pairings.py`).
- Speaker corroboration, read 30 October 2026 as search extracts: SPUR's Prop C guide, the San Francisco Examiner (Melgar; Mahmood), the San Francisco Chronicle and KALW (Chen), the Department of Elections' legal text for the Prop J measure, GrowSF's Prop B page. Full addresses are in the pairings.
