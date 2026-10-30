# Worked pairing examples: six San Francisco pairings of an official's exact words, a donor's own priority and the money, and where each broke

**Kind of hop: a survey** of real sources outside the project (the city's caption transcripts, donors' own published statements, the Ethics Commission's campaign finance data and a few news and election pages), written as **findings**. It assembles worked examples and records every point where one could not be completed. It makes no decisions.

**The pairings themselves are in `pairings.md`** (written by `python build_pairings.py`; method, snapshot and inputs sit beside it in this directory). This file says what they show, how far each part can be trusted, and what the Hops after this one should take from them. **The money sections of `pairings.md` are produced by the script** from the Ethics Commission's DataSF dataset (retrieved 30 October 2026; the raw rows are in `data/money_snapshot.json`). Every pairing has a money section read from the dataset. This file states only the amounts it needs, each with the line of `pairings.md` that holds the rows and the query that produced them.

Builds on `../matching-methods-comparison/findings.md` (the comparison of ways of matching; its code and snapshot are copied here), `../quote-attribution-check/findings.md` (speaker is not in the caption text), `../campaign-finance-survey/findings.md` (committees tied to officials; 24-hour reports; amendments) and `../donor-priorities-survey/findings.md` (donor statements).

## Summary by charter question

1. **Can every part of a pairing be filled, and where does it break?** Partly, and the break points are specific. In all six pairings the official's exact caption words, the meeting, the date and the transcript stamp, the donor's own words with a link and retrieval date, and the list of committees tied to the official are filled from the sources. Three parts break or need a person: (a) the **speaker**, which the transcript text alone gives with low doubt in two of six pairings, medium in two and high in two, and which needed an outside page (a sponsor record) in three; (b) the **link from the transcript stamp to the recording**, which no source here resolves, so a quote cannot yet be offered as "play this moment"; (c) **whether the donor's sentence is a position** on what the official said (one candidate, the Chamber's Prop J statement, turned out to say the Chamber abstained). The money was read for all six, and it divides the set: **one pairing (3, GrowSF and Bilal Mahmood) has money beside it, and it is money the donor's own committees spent on independent expenditure reports naming Mahmood, not money given to his committees; the other five have no row at all** under either reading (section "What the money shows"). The break is therefore in the data, not in the retrieval: in the six donor and official combinations, the donors' committees are not recorded as giving to the officials' committees.
2. **Which money should stand beside a pairing?** Two kinds, each in its own part and never added to the other: (a) Schedule A rows (monetary contributions) from contributors named like the donor to the official's own candidate and officeholder committees, by committee and filing; (b) independent expenditure reports (24-hour reports, form 496) filed by committees named like the donor that name the official as supported or opposed, by committee, office and filing. Kind (b) is the only kind that exists in this set (pairing 3), so a first site needs both parts, and a way to say "no row found" with the control that the committees hold other contributions. Committees formed to support or oppose the official, and ballot-measure committees, are shown apart and labelled; 24-hour contribution reports are listed apart and never added to Schedule A. The rules and the reasons are in "Which money stands beside a pairing" below.
3. **How is each quote credited to an official from the transcript text alone, and how often is that credit in doubt?** By a spoken cue (the chair or clerk calling a member, or the member's own words such as "District Ten"), read by a person. The comparison's automatic cue rule agrees with that credit in **one of six** pairings: it names nobody for one, and a wrong member for four. Credit was in doubt (medium or high) in four of the six. Across the 3,065 substantive passages the rule proposes any speaker for 247 (8%), and for 4 of the 19 passages the trial's model labelled meaningful. Details in "Speaker credit".
4. **How much needed a person's judgement, and at which step?** Of six steps per pairing, two are done by rule (finding the pair by shared named things; listing the committees tied to the official). Of the other four, two needed a person every time (where the quote begins and ends; whether the donor's sentence is a position) and the speaker credit needed one in five of six. The fourth, whether the names the money search returns are the donor, was read against the contributor and committee names in the dataset: the only rows returned (pairing 3) carry committee names that hold the donor's own name, and the names the search does not catch are listed for a person (section "Names read in the filings" of `pairings.md`). Table in "Judgement".

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

## What the money shows

Read from the Ethics Commission's Transactions dataset on DataSF on 30 October 2026 (`data/money_snapshot.json`; sections "Money 1" to "Money 6" of `pairings.md`, from line 349).

| # | Official and donor | Contributions to the official's committees (Schedule A and 24-hour rows) | Independent expenditure reports naming the official, filed by the donor's committees | In `pairings.md` |
|---|---|---|---|---|
| 1 | Myrna Melgar, San Francisco Chamber of Commerce | none | none | line 349 |
| 2 | Chyanne Chen, Neighbors for a Better San Francisco (Blueprint) | none | none | line 380 |
| 3 | Bilal Mahmood, GrowSF | none | **Yes**: three committee and office groups, all reporting spending that supports Mahmood, in 2024 (below) | line 408 |
| 4 | Bilal Mahmood, Neighbors for a Better San Francisco (Blueprint) | none | none | line 488 |
| 5 | Shamann Walton, San Francisco Chamber of Commerce | none | none | line 517 |
| 6 | Chyanne Chen, GrowSF | none | none (rows naming "Mike Chen", another candidate, are left out) | line 550 |

**Pairing 3, as filed** (24-hour independent expenditure reports, form 496; the dataset keeps each report's latest version; amounts are per committee and office and are not added across the groups):
- Coalition to Grow San Francisco - Grow SF PAC Opposing Preston for Supervisor 2024 (filer 205575753), candidate for Supervisor, District 5: 17 rows, $131,170.23, expenditure dates 5 September to 20 October 2024, filings 212128086, 212139607 (version 6), 212242874, 212249096, 212255368, 212271053 and 212343992. The committee's name is about another candidate; the reports name Mahmood as supported.
- Coalition to Grow San Francisco - Grow SF PAC (filer 201619433), candidate for Supervisor, District 5: 9 rows, $14,939.79, expenditure dates 29 September to 28 October 2024, filings 212211516, 212232415, 212259496 (version 2) and 212453813.
- The same committee (filer 201619433), candidate for Board Member, District 17 (office "Board Member", which is probably the Democratic County Central Committee seat for which the snapshot lists a Mahmood committee, filer 208655996) (my reading): 6 rows, $2,379.28, January 2024, filing 209989944. A different office from the one in the pairing.

**What the zeros are worth.** Each contribution search ran over committees that hold Schedule A rows (the control line of each section: for example 922 rows for Mahmood's 2024 Supervisor committee, 678 for Chen's, 635 for Melgar's 2024 committee, 472 for Walton's 2022 committee), so "none" is not an empty read. Searching the same committees with the looser name patterns (see below) also finds no contribution row for any of the six, and finds no independent expenditure row beyond the 32 rows of pairing 3. Not captured by any of this: unitemized contributions (no name), contributions by the donors' officers or members as individuals, and spending that names no candidate (for example slate or ballot-measure spending), none of which can be tied to an official by name.

## Which money stands beside a pairing

The money sections follow rules taken from `../campaign-finance-survey/findings.md` (sections 3 and 4) and applied by `pairing_lib.summarise_money` and `pairing_lib.summarise_independent`:

- **Schedule A only, per committee.** Monetary contributions (Schedule A rows) of contributors whose name contains the donor's name words (the words are checked against names read in the filings; see "A match is by name words" below), listed one row per contribution with committee, filing id, filing date, the version of the filing, the contribution date, the amount and the contributor name as filed. Never added across committees, filings or forms; the only totals are per committee, over Schedule A.
- **The official's own committees are the headline.** `data/committees.json` ties committees to each official; `Candidate or Officeholder` and `470 [Officeholder]` committees are treated as the official's own. Committees formed to *support* or *oppose* an official are third-party money about the official, not to the official (the survey's example is a GrowSF committee opposing Chan), so they are labelled in the money section and never merged into a headline. Ballot-measure committees naming an official (the Mayor's) are a third kind and likewise labelled. For the officials in the six pairings only own committees and one supporting committee (Walton) exist; the labels are in place for the others.
- **24-hour reports (Form 497 part 1) never add to Schedule A.** The survey found 2,865 of 4,470 such rows since 2022 have a matching Schedule A row (same committee, date, amount). A row repeating a Schedule A row is listed as a repeat and not counted; a 24-hour row with no Schedule A counterpart yet (a contribution not yet in a periodic report) is listed apart with its own total, not in the committee's Schedule A total.
- **Amendments.** The Transactions dataset keeps only the latest submission of each report, so one reported contribution is one row and the filing's version is shown so a reader can see it was amended. There is no change history, so "what the donor was recorded as giving on date X" cannot be reconstructed from this dataset.
- **Memo rows** are listed and not summed, since a memo entry is information inside another entry (recalled from how Form 460 treats memo items; not checked against the Commission's instructions in this work).
- **Independent expenditure reports are a second kind of money, apart from contributions.** A committee named like the donor that reports spending to support or oppose the official (form 496, with the candidate's name, office and district as filed) has spent its own money about the official; it has not given it to the official's committees. They are listed by committee and office, never added to the contributions, and the periodic-report copies of the same payments (Schedule E) carry no candidate field and are not read. A supplemental pre-election row (form 465 part 3) with the same committee, date and amount as a 24-hour row is a repeat and is listed apart. Candidates with the official's surname and another given name are excluded (the GrowSF committee also reported spending for "Mike Chen", a different candidate).
- **A match is by name words** (no donor identifier exists): the contributor name as filed is shown on every row. The name words in `money.py` were checked against the names the dataset holds (section "Names read in the filings" of `pairings.md`, from line 578). For the three donors in the pairings: every spelling of Neighbors for a Better San Francisco read (four contributor names, six committee names as filed) is caught; the Chamber and GrowSF are caught under their own and their sponsored-committee names, and some names that look related are not caught and are left for a person: "SAN FRANCISCO FORWARD" without the Chamber's name (10 Schedule A rows and 3 24-hour rows as contributor, and a ballot committee whose name mentions it) and a GrowSF-sponsored committee, "Yes In My Backyard Political Action Committee Sponsored by Grow San Francisco" (filer 160122595). Names caught that are not the donor itself are sponsored or ballot committees carrying its name (for the Chamber, "No on I, sponsored by the San Francisco Chamber of Commerce", and a Yes on Q committee funded in part by "SF Forward"), which stay visible on every row for a person to read. Whether a sponsored committee counts as the same donor is a policy choice the sheet leaves to the reader. Loosening the patterns to take in the unmatched names changes no result for the six pairings (0 contribution rows in all six; independent expenditure rows only for pairing 3, the same 32).
- **Zero rows is an answer, with its limits stated**: unitemized contributions carry no name, other spellings are missed, and committees outside the snapshot of committees are not searched. The snapshot lists one terminated committee for Chen and only terminated committees for Walton. A search of every committee name in the dataset for each surname finds no committee of Melgar, Mahmood or Walton beyond the snapshot (for Walton only a major-donor filer of another person) and none of Chen's beyond the snapshot (the other committees with that surname belong to other people); committees whose names do not hold the surname would not appear.

## Where each part broke, and what filled the gap

| Part | Result | What filled it, or what is left |
|---|---|---|
| Exact words | Filled for all six | Verbatim from the Legistar caption text; `build_pairings.py` refuses to build if a quote is not found word for word. The wording is caption-grade (for example "ONE OF THOSE STRATEGY THAT IS NEEDED"); not checked against the recording, as the approach sets out |
| Meeting, date, stamp | Filled | Meeting body and date from the snapshot; stamp is the caption row's |
| Link to the recording at the stamp | **Not filled** | The earlier survey found no source linking a transcript stamp to the archived video; the pairing shows the transcript link and stamp only |
| Speaker as an official | Filled, with doubt | See "Speaker credit"; outside pages needed for 3 of 6 |
| Priority in the donor's words with link and date | Filled | `data/priorities.json` (retrieved 29 October 2026); six statements from three of the six donors. A fraction glyph lost from a page's text layer can affect a copied statement (the comparison found one); these six contain none |
| Whether the donor's sentence is a position | Needed a person | A candidate pairing with the Chamber's Prop J statement was dropped because that statement says the Chamber abstained |
| Committees tied to the official | Filled | Snapshot of committees; a search of committee names for each surname finds nothing beyond it for the four officials |
| Money by committee and filing | Filled for one of six; confirmed absent for five | Pairing 3 has independent expenditure rows (see "What the money shows"); in pairings 1, 2, 4, 5 and 6 neither contributions nor independent expenditure reports exist for the donor's names. A query failure is printed in place of the figures and makes the run exit 1 |
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
| Donor name variants | Person, at review | The names the search returns, and the near names it does not (listed in "Names read in the filings"), have to be read; for these six the only returned rows are the GrowSF committee's own |

For the review screen of a first site, what a reviewer is shown before a pairing appears should include: the quote with its rows, the cue rows and the doubt, the outside page where one was used, the donor's sentence and link, and the money rows with the contributor name as filed.

## How this serves the objectives

- *Everything shown is current and correct*: quotes are verified verbatim against the snapshot by the script; the priority dates and the transcript retrieval dates are on every pairing; money is stamped by the script with its retrieval date and, where rows were returned, the dataset's last load date.
- *Let a reporter quickly understand pay-to-play speech*: each pairing is a one-screen lead with its own checks. The key result that waits on timing reporters is not met here: nobody was timed.
- *Only surface things that are meaningful*: two of the six pairs would not have cleared a calibrated lexical setting, and a dropped candidate had lexical overlap and the wrong kind of speaker, so lexical scores alone do not decide what stands out. How many pairs look alike by chance is the trial's figure and was not re-measured.

## How to regenerate

`python build_pairings.py` (network needed for the money; reads `picks.json` and the snapshot in `data/`; it runs, for each pairing, the contribution search, the independent expenditure search, the control count, the looser-pattern count and the committee-name search, and, for each donor, the census of names, and exits 1 if any fails), `--no-money` to build without the network, `--from-snapshot` to re-render from `data/money_snapshot.json`. `python -m unittest discover -s tests` checks that every quote is verbatim, that every pairing is complete, and that no lead uses a causal word. Dependencies: the Python standard library only.

## Open questions

**Looked for and not found**
- The comparison's own results (`results.md`, which way it favours): not in the repository; looked in `../matching-methods-comparison/` and its history.
- Any link from a transcript stamp to the same moment in the archived video: not in any source read here or in the earlier surveys.
- A rate of caption error per quote against the recording: still none.
- Minutes of 14 July 2026 and 15 July 2026 (who moved, who spoke): not read; would settle pairing 6 and could confirm 3 and 4.
- Any contribution from these donors' committees to the four officials' committees: none in the dataset under any name read. Whether the donors' officers or members gave as individuals was not looked for.
- A pairing of an official and a donor where the donor gave or spent money about that official and the official said something on the donor's subject: only pairing 3 is one. Which officials each donor funded was not surveyed beyond the four in the pairings, so a first site's list of pairings may need to start from the money (officials a donor funded) and then look for words.
- Whether the Chamber's committee named "San Francisco Forward" without the Chamber's name, and the GrowSF-sponsored "Yes In My Backyard Political Action Committee", are the donors: the filings do not say in the name; no source was read that does.

**Claims not verified**
- That the sponsor pages named as outside sources say what the file attributes to them was read from search extracts, not the full pages (unverified).
- That the Department of Elections' legal text for the Prop J measure (file 260692) lists Mandelman as a sponsor while the sponsor's spoken thanks omit him is a reading of caption text that may be garbled (unverified).
- That memo rows are not part of Form 460 totals (recalled).
- That the 24-hour independent expenditure rows of the GrowSF committees are not also counted in a periodic report of the same committee (Schedule E carries no candidate field, so this could not be matched row by row) (unverified).
- That form 496 is the 24-hour independent expenditure report and form 465 part 3 its supplemental pre-election counterpart is taken from the dataset's own form codes and the field `support_oppose_code`, not from the Commission's instructions (unverified).
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
