# Donor priorities survey: where San Francisco's biggest political donors state their own priorities

**Kind of hop: a survey** of sources outside the project (the websites, filings and other material that the largest donors to San Francisco political committees publish themselves). These are findings, not a design; they make no decisions. Where the findings say what the evidence "points to", that is a reading for the next Hop to weigh, not a choice. The sample is 34 donors (16 individuals or couples, 18 organisations): every donor named in the Ethics Commission's top-contributor tables for the 2026 elections as reproduced in section 1, plus a few long-standing committee funders named in the press. It is chosen by prominence, not at random, so every share below is an estimate with a wide range, given with its range.

## Summary by charter question

1. **Where do the largest donors publish their own stated priorities?** Mostly on **their own websites**, and mostly **organisations** do. The places found, from most to least useful for a pairing:
   - A *per-election voter guide or endorsement page* on the organisation's own site (GrowSF's voter guide, the SF Chamber of Commerce's November 2026 voter guide, Blueprint's November 2026 voter guide, SEIU 1021's and IFPTE Local 21's endorsement pages). These tie a position to a named contest and a date.
   - An *issue or agenda page* on the organisation's own site (SF Chamber "Legislative Agenda", Blueprint's three "What We Believe" pillars, SEIU 1021 "Issues & Legislation").
   - An *own-voice article feed* (the SF Police Officers Association's home page carries president's columns on Prop I and AB 1383; the SEIU 1021 issues page is a dated article list).
   - A *company statement about San Francisco* on its own newsroom (Airbnb's 2019 post on home-sharing rules; Visa's older San Francisco community releases). Dated, and not tied to a current measure.
   - A *mission or "focus areas" page* of a foundation or firm (Emerson Collective; PG&E's public-policy-engagement page). These state what the donor cares about in general, not what it wants from City Hall.
   - A *personal social-media profile or post* (Jeremy Stoppelman's X profile). Short and in the donor's own words, but on a platform that is awkward to cite and fetch.
   - A *book or personal site* (John Doerr's climate plan, "Speed & Scale"): first-party, but about climate, not local government.
   - *Official filings*: the Ethics Commission's committee pages carry a one-line "Purpose" (for example "organized regarding Measure C,D"); nonprofits' IRS-filed mission statements appear on GuideStar. Stable and citable, but they say only support/oppose or a generic mission.
   - **Most of the largest individual donors have no page of their own that states a priority.** What is known about them comes from news interviews and profiles, which the project's rule (donor's own published material only) excludes.
2. **What share has a priority stated clearly enough to cite?** Using one rubric (section 2): *first-party, about a local-government issue, with a stable URL* ("class A"):
   - **Individuals: 1 of 16 (about 6%, 95% range 1-28%).** Any first-party statement at all, including general philanthropy, climate or a federal campaign platform: 4 of 16 (25%, 10-49%). Any statement from any source, including news: 12 of 16 (75%, 51-90%); 4 of 16 had none found.
   - **Organisations: 7 of 18 (about 39%, 20-61%).** Any first-party statement: 11 of 18 (61%, 39-80%). Any statement from any source: 12 of 18 (67%, 44-84%); 6 of 18 had none found.
   - **The largest by listed dollars** (donors whose listed contributions in the frame sum to $500K or more: 9 individuals, 9 organisations; table in section 2) give the same picture: 1 of 9 individuals (11%, 2-44%) and 4 of 9 organisations (44%, 19-73%) in class A.
   - Reading: for the next Hop, organisations are roughly six times as likely as individuals to have a citable stated priority, and an individual donor will most often appear in a pairing with **no** stated priority unless sources beyond the donor's own pages are allowed. Companies that give through a chief executive or a sponsored committee (Visa, Google, PG&E, Williams-Sonoma, Anthropic, OpenAI, Ripple) mostly have only generic or no first-party material.
3. **Can these statements be fetched and watched automatically?** Partly. A general-purpose fetcher retrieved clean text from all six class-A pages opened (SF Chamber agenda, GrowSF voter guide, SEIU 1021 issues page, Airbnb newsroom post, Blueprint home page, and the Neighbors release on Yahoo Finance): server-rendered, no login, no script wall. Three of the six expose a change signal (a page-modified meta tag on the Chamber agenda, a visible "Updated" date on the GrowSF guide, a dated article list on SEIU 1021). Against that: (a) no feed, API or change log was seen on any of them; (b) `robots.txt` and terms of use were not read for any donor site, so whether automated fetching is permitted is unknown; (c) a page change says nothing about which sentence is the priority, so a person must pick and confirm the exact words each time; (d) most individuals have nothing to poll. The evidence points to a split: **polling can cover a minority of donors (organisations that publish agendas, voter guides or endorsement lists); the rest would have to be entered by a person**, with the exact quote, URL and date retrieved. Details in section 4.

## 1. How the sample was chosen

"Largest donors to San Francisco officials" was not ranked by dollars across all years in this Hop (the campaign finance survey in `../campaign-finance-survey/` covers how to compute that from the DataSF Transactions dataset). Instead the sample is the **top-contributor tables the Ethics Commission publishes for the 2026 elections** (`campaign.sfethics.org`), widened with donors named in Mission Local, San Francisco Chronicle and SF Standard reporting on the biggest donors. The tables list *measure and committee* money, and the Mayor's own committees are ballot-measure committees, so "donors to officials" here means donors to the Mayor's measure committees and to the committees around the other officials. Every donor listed in the frame below is assessed in section 2.

| Source of the frame | What it lists |
|---|---|
| Measures D, E, F (Mayor's charter measures), Nov 2026 | Michael Moritz $2.59M; Christian Larsen $1.49M; Lyna Lam $1.0M; John Pritzker $1.0M; Emerson Collective LLC $550K; L. John Doerr III $500K; Dagmar Dolby $500K; John Wolthuis $500K; Michael Seibel $450K; Jean-Pierre Conte $250K |
| Measure H (Muni parcel tax), Nov 2026 | Anthropic, Openai, Ripple Labs, Visa (each $500K); a committee sponsored by Airbnb ($500K); SF Forward, sponsored by the SF Chamber of Commerce ($499K); Jeffrey Lawson $350K; Emerson Collective $200K |
| Measures C and D, June 2026 | Neighbors for a Better San Francisco Advocacy $860K; Moritz $625K; Sergey Brin $500K; Chris Larsen $500K; SF Forward $350K; Williams-Sonoma; Visa; Google; PG&E; Tony Xu ($250K per the Institute for Policy Studies and SF Public Press) |
| Measure D (June 2026, executive pay tax) | Saikat Chakrabarti $600K in the Ethics table (the Chronicle's report of his gift says $500,000; the difference is not resolved); SEIU Local 1021 Issues PAC $600K; SEIU 2015 committees; IFPTE Local 21 committees |
| Measure G (Great Highway), Nov 2026 | Jeremy Stoppelman $750K; Laura Yakovenko $250K; Emmett Shear $75K |
| Press | Jan Koum ($250K to SF Believes, Mission Local); GrowSF, SF Police Officers Association, SF Labor Council, SF Realtors as long-standing committee funders and endorsers |

Frame notes that matter for pairing:

- **The same donor appears under several names.** The Ethics tables show "Christian Larsen" and "Chris Larsen", "Emerson Collective Llc(diedra Nelson)", and a committee "Sponsored by Airbnb, Inc.". For priorities, the *sponsor* (Airbnb, the Chamber) is the entity that publishes, so a sponsor link must be resolved before a priority can be attached. This is the same name problem the campaign finance survey found.
- **Neighbors for a Better San Francisco is two entities.** The $860K donor is "Neighbors for a Better San Francisco Advocacy", a 501(c)(4); the group that publishes (Blueprint for a Better San Francisco, sfblueprint.org) describes itself as a project of Neighbors for a Better San Francisco, a linked 501(c)(3) with the same executive director (Ethics Commission settlement excerpt). Blueprint's "Donate" button points to a fundraising page in the Advocacy entity's name, which is the evidence that ties the site to the donor.
- **Couples and holding companies.** Larsen and Lam, and Moritz with Harriet Heyman, are reported together by the press and separately in filings. The sample counts a couple once.
- **Individuals who are also candidates** (Chakrabarti, a 2026 congressional candidate) publish campaign platforms, which are first-party but mostly not about city government.

## 2. The sample, donor by donor

Class key (the rubric, applied identically to individuals and organisations):

- **A** = the donor's own published statement of a priority about a **local-government issue** (a policy, a measure, a kind of candidate), at a stable URL.
- **B** = the donor's own published statement of general priorities that is **not about local government** (philanthropic focus areas, climate, federal platform, corporate public-policy engagement), or a first-party source the research could only see through a third party's description.
- **C** = what the donor cares about is known **only from third-party material** (news, profiles, grant databases).
- **D** = **nothing found** in this research (the search was shallow; this is not proof none exists).

"Opened" means the page was fetched and read in full; "excerpt" means only a search-result excerpt of the page was seen.

### Individuals and couples (16)

| Donor | Where their own words would be | Class | Evidence and how citable |
|---|---|---|---|
| Jeremy Stoppelman (Yelp co-founder) | X profile and posts | **A** | Profile bio gives a stance ("YIMBY. Pro pedestrians, bikes, and transit.", excerpt) and posts on pedestrian safety and streets; the measure he funded (Prop G, $750K) is on the same topic. Short and exact, dated posts, but a social platform: fragile to fetch and archive. |
| John Doerr | Own book and plan "Speed & Scale" | **B** | A published climate plan in his name; nothing about San Francisco government. |
| Michael Moritz (with Harriet Heyman) | Crankstart foundation; interviews | **B** | Foundation's focus areas (education, housing security, economic mobility, social welfare) are described by Inside Philanthropy and a profile site; Crankstart's own site (crankstart.org) did not come back in any search and was not opened. His aims for City Hall are stated in interviews quoted by Mission Local and the Examiner (third party). |
| Saikat Chakrabarti | Campaign website (cited by Ballotpedia) | **B** | Candidate platform (Medicare for All, affordable housing, political reform, clean energy; a plan for a public financing entity for housing) is seen only through Ballotpedia, BallotReady and KALW; his reason for the Prop D gift is quoted by the Chronicle and Mission Local. The campaign site itself was not opened, and the platform is for Congress. |
| Chris Larsen and Lyna Lam | Interviews; community foundation profile | **C** | Aims (police "force multiplier", cameras, safety ambassadors, downtown revival) come from news interviews and a 2025-26 Silicon Valley Community Foundation donor story. No page of their own was found. |
| John Pritzker | None found | **C** | Giving described in news (UCSF psychiatry building, a park). The Pritzker Pucker Family Foundation that comes up in searches belongs to a different branch of the family, and was not taken as his. |
| Dagmar Dolby | Family fund | **C** | Philanthropy (mood disorders, dementia) reported by UCSF, the Alzheimer's Association and the Chronicle. Nothing political. |
| Jean-Pierre Conte | Self-written bio pages | **C** | Bio pages say healthcare, education and scientific research philanthropy and call him a "policy advocate"; no statement tied to a San Francisco issue. |
| Jan Koum | None found | **C** | Reported as a $250K donor to a pro-Mayor PAC and as a large hospital donor in Jerusalem (news). No local statement. |
| Sergey Brin | None found | **C** | Reported by the Chronicle, Fox Business and Mission Local as giving $500K to the campaign opposing the Overpaid CEO tax and backing a counter-measure. No statement of his own found. |
| Tony Xu (DoorDash CEO) | None found | **C** | Reported as a $250K donor; SF Public Press ties it to DoorDash's earlier disputes with the city over fees and labour classification. No statement of his own found. |
| Jeffrey Lawson | None found | **C** | Known locally for homelessness giving and for defending the city (Chronicle, Fast Company, both older). No current statement of his own found. |
| John Wolthuis | None found | **D** | Only appears as a $500K listing. |
| Michael Seibel | None found | **D** | Only appears as a listing and in a donor roll-call. |
| Laura Yakovenko | None found | **D** | Named as the main funder of the No on G campaign and an earlier Great Highway donor; the only characterisation of her motives is a third-party opinion column. No statement of her own found. |
| Emmett Shear | None found | **D** | Named as a donor on the Great Highway measures; no statement of his own found. |

Tally: A 1, B 3, C 8, D 4.

### Organisations (18)

| Donor | Where it publishes | Class | Evidence and how citable |
|---|---|---|---|
| GrowSF | Voter guide, per election (`growsf.org/voter-guide/`), plus "about" page | **A** | Opened. The hub page is overwritten for each election (it now carries the November 3, 2026 guide, "Updated: October 22, 2026") while earlier and per-measure pages keep their own addresses (for example `.../san-francisco-voter-guide-november-2026-election/measures/prop-h/legal-text/`, `.../san-francisco-voter-guide-june-2026-election/`). Names priorities in its own words (housing, safe streets and fully staffed police, treatment, a more transparent City Hall) and a yes/no position with reasons on every measure. Long and opinionated, so the exact sentence must be picked; the hub URL must be archived per election to stay citable. |
| San Francisco Chamber of Commerce (SF Forward) | "Legislative Agenda" (`sfchamber.com/agenda/`, earlier address `/advocacy/agenda/`); "November 2026 Voter Guide" (`sfchamber.com/november-2026-voter-guide/`, plus a PDF) | **A** | Agenda opened. Current: page-modified tag 2026-09-10; headings "Build the Foundations for San Francisco's Future" (housing and homelessness, transit, human infrastructure, resilience and public safety including the ESER 2026 bond), "Keep San Francisco and California Competitive", "Energize Civic Life, Culture, and Community Vibrancy". The page itself shows no date, so the modified tag is the only date. The voter guide gives per-measure positions (supports Props D and H, seen as excerpt). Money flows through "SF Forward, sponsored by" the Chamber. |
| SEIU Local 1021 | "Issues & Legislation" (`seiu1021.org/issues-legislation`); endorsement pages (`/post/election-endorsements-nov-3-2026`, `/2026endorsements`) | **A** | Issues page opened: a four-page, dated list of the union's own articles (latest 2026-08-31) on ballot measures, state bills and rallies, including the Overpaid CEO Act. Endorsement pages (excerpts) give a slate and positions on measures per election. Statements are in the union's own words and dated; the issues page is a news list, not a statement of priorities, so the quote must come from the individual article. |
| San Francisco Police Officers Association | Home page and president's columns (`sfpoa.org`) | **A** | Excerpts of the home page show own-voice items dated 2026-09-01 (opposition to Proposition I, with the Mayor and firefighters) and 2026-10-01 (urging the Governor to sign AB 1383), under a mission line about officers' work environment and quality of life. The site itself was not opened in full. |
| IFPTE Local 21 | Endorsements and past-endorsements pages (`ifpte21.org/endorsements-archive`) | **A** | Excerpts show positions on city ballot measures per election (2026 primary, and earlier years such as Prop I in 2020) with the union's reasons. Pages not opened in full. |
| Airbnb | Newsroom post "An Update About Our Community in San Francisco" | **A** | Opened. First-party, dated February 24, 2019, about the 2017 agreement and San Francisco's home-sharing rules ("clear, fair and workable" rules are its stated aim). Company-level and seven years old; no Airbnb statement about the Muni measure it funded through a sponsored committee was found, and the committee has no page of its own. |
| Neighbors for a Better San Francisco | Blueprint for a Better San Francisco (`sfblueprint.org`): home page, three issue pages, November 2026 voter guide; launch release (June 18, 2025) | **A** | The home page (opened) states three pillars, "Road to Recovery" (clean, safe streets, mental health and addiction crises, public safety agencies), "Good Government" and "Vision of Vibrancy", links to pages for each, and a "Full Voter Guide" at `sfblueprint.org/advocacy/november-2026-voter-guide` (dated per election; the June 2026 guide is a blog post). The June 18, 2025 launch release (opened on Yahoo Finance, a PR Newswire distribution; original on prnewswire.com) lists concrete positions: fully staffed public safety agencies, drug-free permanent supportive housing, court-mandated treatment, a balanced budget, a stronger Mayor, fewer commissions. The parent organisation's own site (`neighborsbettersf.com`) was not opened. The money has largely moved to other vehicles (Mission Local, Oct 2026). |
| Emerson Collective (Laurene Powell Jobs) | "About us" page (`emersoncollective.com`) | **B** | Mission page names education, immigration reform, environment, health. Stable and citable, but nothing about San Francisco government. |
| Visa | Newsroom (`usa.visa.com/about-visa/newsroom`) | **B** | First-party releases about its San Francisco community partnerships and its new headquarters at Mission Rock (excerpts; search-index ages of roughly seven to twelve years). Corporate community commitment, no position on a local measure; nothing found about its Muni measure gift. |
| PG&E | "Public policy engagement" page of its sustainability report; corporate contribution disclosures (`pgecorp.com`) | **B** | First-party and stable, but state-wide climate and utility policy and a list of who was funded; no San Francisco priority (excerpts). |
| San Francisco Labor Council | `sflaborcouncil.org` (an FAQ on its structure and mission); X account @sflabor | **B** | First-party self-description and posts (for example on Medicaid cuts), none about a 2026 city measure that was found. Its endorsement list was not found on its own site. The committee page on the Ethics site holds only the contributor list. |
| Ripple Labs | None found | **C** | Company gifts follow Larsen's causes in the press; no company statement on Prop H or the charter found. |
| Anthropic | None found | **D** | $500K to the Muni measure committee is in the Ethics tables; no company statement about the measure found. |
| OpenAI | None found | **D** | As Anthropic. |
| Google | None found | **D** | Listed on the June 2026 measures table; no company statement about the measures found. |
| Williams-Sonoma | None found | **D** | Named only in advocacy reports and the Ethics table as a donor to the campaign against the Overpaid CEO tax; no statement of its own found. |
| SEIU 2015 | None found | **D** | Committees appear in the Ethics tables; no page of its own was reached. |
| San Francisco Association of Realtors | `sfrealtors.com` home page | **D** | Home page (excerpt) describes the association's history and role; no priorities or advocacy page was found in two searches. |

Tally: A 7, B 4, C 1, D 6.

### Largest donors by listed dollars (indicative)

No ranking by dollars across all years was computed. This table orders the donors whose figures in the frame (section 1) sum to $500K or more, using only those listed figures (SEIU Local 1021's, Larsen's with Lam's, and the others as listed); donors whose amounts the frame does not give (Visa's June 2026 gift, Google, PG&E, Williams-Sonoma, SEIU 2015, IFPTE Local 21) are not in it.

| Rank by listed sum | Donor | Listed sum | Class |
|---|---|---|---|
| 1 | Michael Moritz (with Heyman) | $3.2M | B |
| 2 | Chris Larsen and Lyna Lam | $3.0M | C |
| 3 | John Pritzker | $1.0M | C |
| 4 | Neighbors for a Better San Francisco Advocacy | $860K | A |
| 5 | SF Chamber (SF Forward) | $849K | A |
| 6 | Emerson Collective | $750K | B |
| 7 | Jeremy Stoppelman | $750K | A |
| 8 | Saikat Chakrabarti | $600K | B |
| 9 | SEIU Local 1021 Issues PAC | $600K | A |
| 10-18 | Doerr, Dolby, Wolthuis, Brin (individuals); Anthropic, OpenAI, Ripple, Visa, Airbnb-sponsored committee (organisations), each $500K | $500K | B, C, D, C; D, D, C, B, A |

Of the 9 individuals in this table, 1 is class A, 3 class B, 4 class C, 1 class D; of the 9 organisations, 4 are class A, 2 class B, 1 class C, 2 class D.

### Shares (estimates; Wilson 95% range)

| Group | A: first-party, local issue | A+B: any first-party | A+B+C: any source | D: none found |
|---|---|---|---|---|
| Individuals (n=16) | 1 (6%, 1-28%) | 4 (25%, 10-49%) | 12 (75%, 51-90%) | 4 (25%, 10-49%) |
| Organisations (n=18) | 7 (39%, 20-61%) | 11 (61%, 39-80%) | 12 (67%, 44-84%) | 6 (33%, 16-56%) |
| Both (n=34) | 8 (24%, 12-40%) | 15 (44%, 29-61%) | 24 (71%, 54-83%) | 10 (29%, 17-46%) |
| Individuals, listed sum ≥ $500K (n=9) | 1 (11%, 2-44%) | 4 (44%, 19-73%) | 8 (89%, 56-98%) | 1 (11%, 2-44%) |
| Organisations, listed sum ≥ $500K (n=9) | 4 (44%, 19-73%) | 6 (67%, 35-88%) | 7 (78%, 45-94%) | 2 (22%, 6-55%) |

Why these are rough: the sample is not random; six of the seven class-A organisations (GrowSF, Chamber, SEIU 1021, SFPOA, IFPTE Local 21, Blueprint) are advocacy groups, unions or trade bodies whose business is publishing positions, so a sample weighted to companies would score lower (the seven companies in the sample, Airbnb aside, are all B, C or D); "none found" reflects a search of the donor's name plus a topic, not a crawl of the donor's site; three class-A rows (SFPOA, IFPTE Local 21, SEIU endorsement pages) rest partly on search excerpts; and class A/B boundaries (is a philanthropic focus a "priority"?) are a judgement the maintainer has not yet made.

## 3. How citable each kind of source is

What a reporter needs to check a pairing in minutes: the exact words, at a URL that still shows them, with a date.

| Kind of source | Exact words? | Stable URL? | Dated? | Notes |
|---|---|---|---|---|
| Per-election voter guide (GrowSF, Chamber, Blueprint) | Yes | Per-election pages and per-measure pages, yes; the GrowSF hub address is overwritten each election | Yes (election named; GrowSF shows "Updated") | Best fit seen: a statement tied to a named contest. |
| Endorsement page (SEIU 1021, IFPTE Local 21) | Yes | Per election | Yes | Positions only; reasons are short. |
| Agenda / issues page (Chamber, Blueprint pillars) | Yes | Yes (Chamber agenda moved from `/advocacy/agenda/` to `/agenda/`) | Page shows no date; Chamber exposes a modified tag | Page is edited in place; keep a dated copy. |
| Own-voice article feed (SFPOA, SEIU 1021) | Yes | Per article | Yes | Many items, few of them priorities. |
| Newsroom post (Airbnb, Visa) | Yes | Yes | Yes | Company-wide, not tied to a measure; can be years old. |
| Foundation or firm "about" page (Emerson, PG&E) | Yes | Yes | No | General mission; shows an interest area, not a local position. |
| Social post or bio (Stoppelman, Labor Council) | Yes | Per post | Yes | Platform may block or alter access; terms not read. |
| Ethics Commission committee "Purpose" | Yes | Yes | Per election | Only "supports/opposes X"; a registered position, not a priority. |
| IRS mission statement (GuideStar) | Yes | Yes | By tax year | Generic; useful only for nonprofits. |
| News interview or profile | Quote only | Yes | Yes | Third party; outside the project's own-material rule. |

## 4. Can the statements be fetched and watched?

What the evidence supports, by source:

- **Public organisation pages (class A).** Six pages were opened by a general-purpose fetcher and each returned readable text without login:
  - *SF Chamber agenda* (WordPress): the page carries a page-modified tag (2026-09-10), a link to a sitemap page, and its own Terms of Service link (`sfchamber.com/terms-of-service/`, not read). The page opens with the 2026 content (ESER 2026 bond), with no COVID-19 section.
  - *GrowSF voter guide* (Next.js): one long page with a visible "Updated: October 22, 2026" date, a table of contents and links to per-measure pages; the page replaces the previous election's guide at the same address, so a poller must also watch for new per-election addresses and keep a copy of what it replaced.
  - *SEIU 1021 issues page* (Drupal): a paginated, dated list of article links; changes show as new items at the top. The page also carries a log-in form, which the fetcher ignored.
  - *Airbnb newsroom post* (WordPress): static, dated 2019; a change is unlikely.
  - *Blueprint home page* (Webflow): links to a per-election voter guide, blog posts and three issue pages.
  - *Neighbors launch release on Yahoo Finance*: a paid press release distributed by PR Newswire, static; the original is on prnewswire.com.
  A poller could fetch each page, keep the main text with a content hash and retrieval date, and flag a change for a person to read. What was **not** tested: whether these pages answer a poller's own user agent (the fetcher used here is a different client), whether any rate limit or bot protection applies, and whether any site publishes an RSS feed or XML sitemap (a sitemap link exists on the Chamber site only). **No `robots.txt` was read for any donor site** (none could be opened) and only the Chamber's terms link was seen; whether automated fetching is permitted is therefore unknown.
- **Freshness varies.** GrowSF, Blueprint and the Chamber publish new election-specific material (GrowSF's June and November 2026 guides have separate per-measure pages; Blueprint's June 2026 guide is a blog post and its November guide a separate page; the Chamber's November 2026 voter guide is a page and a PDF), which suggests watching an *index* for new addresses rather than one page. SEIU 1021 and IFPTE Local 21 post endorsement pages per election. The Chamber agenda was modified on 2026-09-10, so it is maintained. Airbnb's post is a fixed 2019 statement.
- **Social profiles.** An X profile is the only individual-donor source of class A; fetching it automatically depends on a platform's access rules that were not examined. Treat as manual.
- **Official records.** DataSF's description of the Campaign Finance - Transactions dataset states that a script runs each night from midnight Pacific time to add transactions from new filings; its State Filer Data dataset is rewritten nightly. The Ethics Commission's election and committee pages (`campaign.sfethics.org`) were seen only as search excerpts. They show a committee ID (for example 1431167 for Neighbors for a Better San Francisco Advocacy, matching the `CA1431167` address), a list of the committee's Forms 460, 496 and 497 by filing date, and a note that summary figures use only the latest version of each form, which is the same latest-version rule DataSF describes. Nothing read says how those pages are generated, whether they come from the same data as DataSF, or how often they refresh, so nightly comparison between the two is a possibility, not an established fact. The pages hold no priorities beyond support/oppose and a "Purpose" line.
- **What a watcher cannot do.** It cannot tell which sentence is the "priority", whether a new sentence replaces an old one, or whether a donor's silence means no priority. The project's rule against paraphrase means every stored statement needs a person-confirmed exact quote.
- **For individuals** there is mostly nothing to watch, so a way to enter a statement by hand (quote, URL, date, who confirmed) would be needed for any individual who is to appear with a priority.

Points for Pairing site first version, stated as evidence and not as a choice: a poller alongside speech and filings would cover a minority of donors (the organisations that publish agendas, voter guides or endorsement lists), at the cost of a review step for each change; an entry screen would cover the rest; the evidence does not say which alone is enough. If the first version includes only class-A donors, the evidence suggests most top individual donors would appear without a priority.

## 5. How this serves the objectives

- **Let a reporter check any pairing in minutes.** Class-A statements with an exact quote, URL and date can be checked in about the time it takes to open the page and find the sentence; class B/C cannot meet that bar with the donor's own words. No timing was done in this Hop. A candidate key result that could be written from these findings: *of the top N donors by dollars to a given official's committees, how many have a class-A statement, and how long does a local reporter take to confirm each pairing's quote and amount*. This needs the dollar ranking for the officials (campaign finance survey data) joined to the class table above; the 34-donor sample is the first rows of that table (`donor-sample.json`), and the indicative ranking in section 2 shows the shape (1 of 9 top individuals and 4 of 9 top organisations in class A).
- **Everything shown is current and correct.** Pages that edit in place (Chamber agenda, Blueprint pillars) can change without notice; a retrieval date and content hash would show when a quoted statement was last seen on the donor's page. Dated per-election pages and the Chamber's modified tag are the best available currency signals; the Airbnb post shows how a first-party statement can be a fixed seven-year-old position.

## 6. Sources used

Pages opened in full: SF Chamber of Commerce Legislative Agenda (https://sfchamber.com/advocacy/agenda/, canonical https://sfchamber.com/agenda/); GrowSF Voter Guide (https://growsf.org/voter-guide/); SEIU 1021 Issues & Legislation (https://www.seiu1021.org/issues-legislation); Airbnb Newsroom, "An Update About Our Community in San Francisco" (https://news.airbnb.com/an-update-about-our-community-in-san-francisco); Neighbors for a Better San Francisco launch release on Yahoo Finance (https://finance.yahoo.com/news/neighbors-better-san-francisco-launches-140200587.html); Blueprint for a Better San Francisco home page (http://sfblueprint.org, canonical https://www.sfblueprint.org); Mission Local, "BigMoneySF: How Mayor Lurie's efforts to reshape City Hall brought in a new donor class" (2026-10-20, https://missionlocal.org/2026/10/big-money-san-francisco-lurie-charter-reform-labor-moderates-billionaires-democrats-election/); Mission Local, "Who's bankrolling San Francisco's coming election? These 16 donors." (2026-09-11, https://missionlocal.org/2026/09/san-francisco-november-election-top-donors/); DataSF dataset description for Transactions (https://data.sf.gov/api/views/pitq-e56w.json).

Pages seen only as search-result excerpts (the excerpt, not the full page, is what the assessments rest on):

- Ethics Commission pages: https://campaign.sfethics.org/elections/2026-11-03/measures/measuredef.html ; .../measureh.html ; .../measureg.html ; .../2026-06-02/measures/measurecd.html ; .../2026-06-02/committees/CA1431167.html (Neighbors for a Better San Francisco Advocacy) ; .../2026-06-02/committees/CA1485633 ; .../2026-11-03/committees/CA970630.html (Labor Council committee); also CA1479782 (Muni measure committee), CA1433436 (GrowSF Voter Guide). Ethics Commission settlement with Neighbors Advocacy and Jay Cheng (https://sfethics.org/wp-content/uploads/2024/08/2024.08.09-Agenda-Item-5-SFEC-Case-2223-484-Neighbors-Advocacy-and-Cheng-Signed-Stipulated-Settlement_Redacted.pdf).
- DataSF: https://data.sf.gov/City-Management-and-Ethics/Campaign-Finance-Transactions/pitq-e56w ; https://data.sf.gov/City-Management-and-Ethics/Campaign-Finance-State-Filer-Data/3n88-2rrb ; https://catalog.data.gov/dataset/campaign-finance-transactions
- GrowSF: https://growsf.org/about/ ; https://growsf.org/voter-guide/san-francisco-voter-guide-november-2026-election/measures/prop-h/legal-text/
- SF Chamber of Commerce: https://sfchamber.com/november-2026-voter-guide/ ; https://sfchamber.com/wp-content/uploads/2026/10/SFCC-Voter-Guide-2026-VERTICAL.pdf
- SEIU 1021: https://www.seiu1021.org/post/election-endorsements-nov-3-2026 ; https://www.seiu1021.org/2026endorsements
- SFPOA: https://sfpoa.org/ ; https://sfpoa.org/a-message-of-gratitude-and-commitment-for-the-new-year/
- IFPTE Local 21: https://ifpte21.org/endorsements-archive
- SF Labor Council: https://www.sflaborcouncil.org/en/news-details/webview/faq/single/19358 ; https://x.com/sflabor
- SF Realtors: https://sfrealtors.com/
- Emerson Collective: https://www.emersoncollective.com/index.php?p=about-us
- Neighbors for a Better San Francisco: https://www.guidestar.org/profile/86-2339545
- Visa: https://usa.visa.com/about-visa/newsroom/press-releases.releaseId.16691.html ; https://usa.visa.com/about-visa/newsroom/press-releases.releaseId.9971.html
- PG&E: https://www.pgecorp.com/sustainability/corporate-sustainability/corporate_sustainability_report_2024/performance/public_policy_engagement.html ; https://pgecorp.com/aboutus/corp_gov/political_engagement/2022/2022_campaign_contributions_jan_jun.shtml
- Jeremy Stoppelman: https://x.com/jeremys
- Crankstart (third-party descriptions): https://www.insidephilanthropy.com/find-a-grant/grants-c/crankstart-foundation
- Chakrabarti: https://ballotpedia.org/Saikat_Chakrabarti ; https://www.kalw.org/show/your-call/2026-05-14/what-questions-do-you-have-for-sf-candidate-saikat-chakrabarti ; https://www.sfchronicle.com/sf/article/saikat-chakrabarti-sergey-brin-donations-22272950.php ; https://missionlocal.org/2026/05/saikat-chakrabarti-sergey-brin-google-overpaid-ceo-tax-proposition-d/
- Brin, Xu, Williams-Sonoma, Lawson, Yakovenko and Shear (third party): https://www.yahoo.com/news/articles/sergey-brin-pours-500-000-015505748.html ; https://www.foxbusiness.com/politics/sergey-brin-spends-500k-fight-tax-targeting-companies-high-paid-executives ; https://ips-dc.org/the-corporate-and-billionaire-opponents-of-san-franciscos-overpaid-executive-tax/ ; https://www.sfpublicpress.org/proposition-c-would-cut-taxes-and-city-revenue/ ; https://www.sfchronicle.com/bayarea/article/onion-infowars-jeff-lawson-19916380.php ; https://sfstandard.com/opinion/2025/01/02/k-is-for-katastrophe-how-sf-centrists-wasted-a-golden-opportunity/ ; https://missionlocal.org/2026/09/sf-sunset-prop-g-great-highway-campaign-finance/
- Larsen and Lam: https://www.svcf.org/annual-reports/donor-2025/donor-stories-2025-26-larsenlam ; https://missionlocal.org/2024/02/prop-e-police-surveillance-sf/
- San Francisco Chronicle, "These are the wealthy people trying to reshape S.F. politics" (top-ten donors this decade): https://www.sfchronicle.com/projects/2026/san-francisco-election-donors/ (excerpts only)
- Others: Mission Local on Jan Koum (https://missionlocal.org/2026/04/sf-jan-koum-daniel-lurie-campaign-finance/); Chronicle on Pritzker's UCSF gift; SF Standard on Lurie's donors (https://sfstandard.com/2026/10/28/san-francisco-mayor-daniel-lurie-money-campaign-election-2026/); Department of Elections voter guide PDF (https://media.api.sf.gov/documents/N26_EN_VIP.pdf).

## Open questions

### What was looked for and not found

- **Own pages of the individual megadonors.** Searched by name plus topic for Moritz, Larsen/Lam, Pritzker, Dolby, Wolthuis, Seibel, Conte, Koum, Brin, Xu, Lawson, Yakovenko, Shear. No own site or statement about local priorities found for any except Stoppelman's X profile (class A) and Doerr's climate book. Crankstart's own site and the Larsen/Lam foundation pages were not opened.
- **Own pages of Anthropic, OpenAI, Ripple, Google, Williams-Sonoma, SEIU 2015 and SF Realtors.** Searched; only third-party or committee-filing pages came back (and the Realtors home page). The SF Realtors site beyond its home page and the SF Labor Council site beyond one FAQ page were not opened.
- **A feed, API or change log on any donor page.** None seen on the pages opened; RSS and sitemap presence was not tested beyond a sitemap link on the Chamber site.
- **robots.txt and terms of use** of every donor site and of the social platform: not read. The Chamber's terms link exists and was not opened.
- **Whether the Voter Information Pamphlet's ballot arguments are a source of donor-signed statements.** The pamphlet PDF appeared in search, but its arguments were not read; that proponents' paid arguments carry named signers is recalled, not read here (recalled).
- **Whether San Francisco lobbyist or behested-payment filings state the issues a donor cares about.** Behested payments are mentioned in SF Standard's reporting on the Mayor's donors; the issue fields of lobbyist filings were not looked at (recalled that lobbyist reports list the matters lobbied).
- **A ranking by dollars of the officials' largest donors across all years.** The sample frame is the 2026 Ethics Commission tables, not a computed ranking from the Transactions dataset; the table in section 2 orders only the figures listed in the frame.
- **How the Ethics Commission's campaign pages are generated and how often they refresh.** Not stated in any excerpt read; a full committee page was not opened.

### Claims not verified

- That the Ethics Commission pages draw on the same data as DataSF, and that they refresh nightly (unverified); only DataSF's own nightly update description was read.
- That Crankstart's focus areas are as Inside Philanthropy and a profile site describe them, since its own pages were not opened (unverified).
- That the John Pritzker in the Ethics tables is the Hyatt heir whose UCSF gift the Chronicle describes; Mission Local and the Chronicle both say so, but no filing was checked (unverified).
- That Stoppelman's X profile text is current; the page was seen only as an indexed excerpt, and the posts quoted from it are undated in the excerpt (unverified).
- The class-A ratings of SFPOA and IFPTE Local 21 rest on excerpts of their own pages; the pages were not opened in full (unverified).
- That Blueprint (sfblueprint.org) speaks for the $860K donor "Neighbors for a Better San Francisco Advocacy": the site names the parent, and its donate link points to the Advocacy entity's fundraising page, but no filing linking the two was read (unverified).
- Chakrabarti's gift: $600K in the Ethics table as reproduced here, $500,000 in the Chronicle's report; not reconciled (unverified).
- Shares and ranges are computed on 34 donors chosen by prominence; they are not estimates for all large donors.

### Questions for the maintainer

- Does a donor's **philanthropic or general focus** (an Emerson or Crankstart mission page) count as a "stated priority" for a pairing, or only a statement about a local-government issue? This moves individuals from 6% to 25% and organisations from 39% to 61%.
- Should a **sponsored committee's money** (a committee "sponsored by" Airbnb or the Chamber) be paired with the sponsor's statements?
- Should an individual with **no first-party statement** appear in pairings with the priority left blank, or be left out until one is found?
- Is a **statement made through a company** (a CEO's company page) the donor's own, when the donor is the CEO?
- Is a **years-old first-party statement** (Airbnb's 2019 post) citable as a current priority, or should a statement need to be from the current election cycle?

### What would turn this into a measurable key result

- The dollar ranking of each official's largest donors (from the campaign finance survey's data), joined to the class table here, to give "share of top-N donors by dollars with a class-A statement".
- Timing two or three local reporters as they verify a handful of real pairings built from class-A rows, as the objective's note describes.
