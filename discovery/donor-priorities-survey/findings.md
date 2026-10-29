# Donor priorities survey: where San Francisco's biggest political donors state their own priorities

**Kind of hop: a survey** of sources outside the project (the websites, filings and other material that the largest donors to San Francisco political committees publish themselves). These are findings, not a design; they make no decisions. Where the findings say what the evidence "points to", that is a reading for the next Hop to weigh, not a choice. The sample is 22 donors (10 individuals or couples, 12 organisations) taken from the Ethics Commission's own top-contributor tables for the 2026 elections; it is small and chosen by prominence, so every share below is an estimate with a wide range, given with its range.

## Summary by charter question

1. **Where do the largest donors publish their own stated priorities?** Mostly on **their own websites**, and mostly **organisations** do. The places found, from most to least useful for a pairing:
   - An *issue or agenda page* on the organisation's own site (SF Chamber of Commerce "Legislative Agenda", SEIU 1021 "Issues & Legislation", GrowSF's voter guide and "about" page).
   - A *company or group statement about San Francisco* on its own newsroom (Airbnb) or a launch release (Neighbors for a Better San Francisco's "Blueprint").
   - A *mission or "focus areas" page* of a foundation or investment-and-philanthropy firm (Emerson Collective; the Crankstart foundation of Michael Moritz and Harriet Heyman, whose own site was not opened). These state what the donor cares about in general, not what it wants from City Hall.
   - A *personal social-media profile or post* (Jeremy Stoppelman's X profile and posts on Great Highway and housing). Short and in the donor's own words, but on a platform that is awkward to cite and fetch.
   - A *book or personal site* (John Doerr's climate plan, "Speed & Scale"): first-party, but about climate, not local government.
   - *Official filings*: the Ethics Commission's committee pages carry a one-line "Purpose" (for example "organized to support Measure H"); nonprofits' IRS-filed mission statements appear on GuideStar. These are stable and citable but say only support/oppose or a generic mission.
   - **Most of the largest individual donors have no page of their own that states a priority.** What is known about them comes from news interviews and profiles, which the project's rule (donor's own published material only) excludes.
2. **What share has a priority stated clearly enough to cite?** Using one rubric (section 3): *first-party, about a local-government issue, with a stable URL* ("class A"):
   - **Individuals: 1 of 10 (about 10%, plausible range 2-40%).** Any first-party statement at all, including general philanthropy or climate: 3 of 10 (30%, 11-60%). Any statement from any source, including news: 8 of 10; 2 of 10 had none found.
   - **Organisations: 5 of 12 (about 42%, 19-68%).** Any first-party statement: 6 of 12 (50%, 25-75%). Any statement from any source: 8 of 12; 4 of 12 had none found.
   - Reading: for the next Hop, organisations are roughly four times as likely as individuals to have a citable stated priority, and an individual donor will most often appear in a pairing with **no** stated priority unless sources beyond the donor's own pages are allowed.
3. **Can these statements be fetched and watched automatically?** Partly. The class-A organisation pages are ordinary public web pages that a poller could fetch and compare by content hash. But (a) no feed, API or change log was observed on any of them (feeds and sitemaps were not tested); (b) the pages change irregularly and some look stale (the Chamber's agenda page still opens with the COVID-19 period); (c) a page change says nothing about which sentence is the priority, so a person must pick and confirm the exact words each time; (d) the individuals mostly have nothing to poll. The evidence points to a split: **polling can cover a minority of organisations; the rest would have to be entered by a person**, with the exact quote, URL and date retrieved.

## 1. How the sample was chosen

"Largest donors to San Francisco officials" was not ranked by dollars across all years in this Hop (the campaign finance survey in `../campaign-finance-survey/` covers how to compute that). Instead the sample is the **top-contributor tables the Ethics Commission publishes for the 2026 elections** (`campaign.sfethics.org`), widened with donors named in Mission Local and San Francisco Chronicle reporting on the biggest donors. Note that the tables list *measure and committee* money, and the Mayor's own committees are ballot-measure committees, so "donors to officials" here means donors to the Mayor's measure committees and to the committees around the other officials.

| Source of the frame | What it lists |
|---|---|
| Measures D, E, F (Mayor's charter measures), Nov 2026 | Michael Moritz $2.59M; Christian Larsen $1.49M; Lyna Lam $1.0M; John Pritzker $1.0M; Emerson Collective LLC $550K; L. John Doerr III $500K; Dagmar Dolby $500K; John Wolthuis $500K; Michael Seibel $450K; Jean-Pierre Conte $250K |
| Measure H (Muni parcel tax), Nov 2026 | Anthropic, Openai, Ripple Labs, Visa (each $500K); a committee sponsored by Airbnb ($500K); SF Forward, sponsored by the SF Chamber of Commerce ($499K); Jeffrey Lawson $350K; Emerson Collective $200K |
| Measures C and D, June 2026 | Neighbors for a Better San Francisco Advocacy $860K; Moritz $625K; Sergey Brin $500K; Chris Larsen $500K; SF Forward $350K; Williams-Sonoma; Visa; Google; PG&E; Tony Xu |
| Measure D (June 2026, executive pay tax) | Saikat Chakrabarti $600K; SEIU Local 1021 Issues PAC $600K; SEIU 2015 committees; IFPTE Local 21 committees |
| Measure G (Great Highway), Nov 2026 | Jeremy Stoppelman $750K; Laura Yakovenko $250K; Emmett Shear $75K |
| Press | Jan Koum ($250K to SF Believes, Mission Local); GrowSF, SF Police Officers Association, SF Labor Council, SF Realtors as long-standing committee funders and endorsers |

Frame notes that matter for pairing:

- **The same donor appears under several names.** The Ethics tables show "Christian Larsen" and "Chris Larsen", "Emerson Collective Llc(diedra Nelson)", and a committee "Sponsored by Airbnb, Inc.". For priorities, the *sponsor* (Airbnb, the Chamber) is the entity that publishes, so a sponsor link must be resolved before a priority can be attached. This is the same name problem the campaign finance survey found (section 5 there).
- **Couples and holding companies.** Larsen and Lam, and Moritz with Heyman, are reported together by the press and separately in filings. The sample counts a couple once.
- **Donors listed in the frame but not assessed** (no search was made for their own statements): Visa, Williams-Sonoma, Google, PG&E, Sergey Brin, Tony Xu, Saikat Chakrabarti, Jeffrey Lawson, Laura Yakovenko, Emmett Shear.

## 2. The sample, donor by donor

Class key (the rubric, applied identically to individuals and organisations):

- **A** = the donor's own published statement of a priority about a **local-government issue** (a policy, a measure, a kind of candidate), at a stable URL.
- **B** = the donor's own published statement of general priorities that is **not about local government** (philanthropic focus areas, climate), or a first-party source the research could only see through a third party's description.
- **C** = what the donor cares about is known **only from third-party material** (news, profiles, grant databases).
- **D** = **nothing found** in this research (the search was shallow; this is not proof none exists).

### Individuals and couples (10)

| Donor | Where their own words would be | Class | Evidence and how citable |
|---|---|---|---|
| Jeremy Stoppelman (Yelp co-founder) | X profile and posts | **A** | Profile bio gives a stance ("YIMBY. Pro pedestrians, bikes, and transit.") and a post on the Great Highway question; the measure he funded (Prop G, $750K) is on the same topic. Short and exact, dated posts, but a social platform: fragile to fetch and archive. |
| John Doerr | Own book and plan "Speed & Scale" | **B** | A published climate plan in his name; nothing about San Francisco government. |
| Michael Moritz (with Harriet Heyman) | Crankstart foundation; interviews | **B** | Foundation's focus areas (education, housing security, economic mobility, social welfare) are described by Inside Philanthropy and a profile site; Crankstart's own pages were not opened. His aims for City Hall are stated in interviews quoted by Mission Local and the Examiner (third party). |
| Chris Larsen and Lyna Lam | Interviews; community foundation profile | **C** | Aims (police "force multiplier", cameras, safety ambassadors, downtown revival) come from news interviews and a 2025-26 Silicon Valley Community Foundation donor story. No page of their own was found. |
| John Pritzker | None found | **C** | Giving described in news (UCSF psychiatry building, a park). The Pritzker Pucker Family Foundation that comes up in searches belongs to a different branch of the family, and was not taken as his. No statement of what he wants from City Hall was found. |
| Dagmar Dolby | Family fund | **C** | Philanthropy (mood disorders, dementia) reported by UCSF, the Alzheimer's Association and the Chronicle. Nothing political. |
| Jean-Pierre Conte | Self-written bio pages | **C** | Bio pages say healthcare, education and scientific research philanthropy and call him a "policy advocate"; no statement tied to a San Francisco issue. |
| Jan Koum | None found | **C** | Reported as a $250K donor to a pro-Mayor PAC and as a large hospital donor in Jerusalem (news). No local statement. |
| John Wolthuis | None found | **D** | Only appears as a $500K listing. |
| Michael Seibel | None found | **D** | Only appears as a listing and in a donor roll-call; no local statement found. |

Tally: A 1, B 2, C 5, D 2.

### Organisations (12)

| Donor | Where it publishes | Class | Evidence and how citable |
|---|---|---|---|
| GrowSF | Voter guide, per election, plus "about" page (`growsf.org`) | **A** | Names priorities in its own words per race and per measure (safety, homes, schools; reasons for each endorsement). A new guide page is published for each election, so the URL and date are stable; text is long and opinionated, so the exact sentence must be picked. |
| San Francisco Chamber of Commerce (SF Forward) | "Legislative Agenda" (`sfchamber.com/advocacy/agenda/`) | **A** | Headings (affordability, economic sustainability, mobility) with bullet priorities. Undated; opens with the COVID-19 period, so it may be out of date (search index showed it about 600 days old) (unverified). Money flows through "SF Forward, sponsored by" the Chamber. |
| SEIU Local 1021 | "Issues & Legislation" and election endorsement pages (`seiu1021.org`) | **A** | Positions on measures and candidates in the union's own words, updated per election (June and November 2026 endorsement pages exist). Mixed currency: the issues page still carries older items. |
| Airbnb | Newsroom post "An Update About Our Community in San Francisco" | **A** | First-party statement about San Francisco rules and the company's stance. Old (company-level, not per-measure), and the sponsored committee that gave the money has no page of its own. |
| Neighbors for a Better San Francisco | Launch release for "Blueprint for a Better San Francisco" (carried on Yahoo Finance); IRS mission on GuideStar | **A** | Release names public safety, homelessness, the fentanyl crisis, downtown recovery as focus. Neighbors' own site was not opened; the group's money has largely moved to other vehicles (Mission Local, Oct 2026). |
| Emerson Collective (Laurene Powell Jobs) | "About us" page (`emersoncollective.com`) | **B** | Mission page names education, immigration reform, environment, health. Stable and citable, but nothing about San Francisco government. |
| Ripple Labs | None found | **C** | Company gifts follow Larsen's causes in the press; no company statement on Prop H or the charter found. |
| San Francisco Police Officers Association | Endorsements (Ballotpedia, news) | **C** | Positions known through Ballotpedia's endorsement list and press; the union's own site was not reached. |
| Anthropic | None found | **D** | $500K to the Muni measure committee is in the Ethics tables; no company statement about the measure found. Its state-level giving is reported in the Chronicle. |
| OpenAI | None found | **D** | As Anthropic. |
| San Francisco Association of Realtors | Home page | **D** | Home page says it provides "legislative representation"; no priorities page seen. |
| San Francisco Labor Council | Committee page on the Ethics site | **D** | Only the committee's contributor list was seen; no own-site priorities page found. |

Tally: A 5, B 1, C 2, D 4.

### Shares (estimates; Wilson 95% range)

| Group | A: first-party, local issue | A+B: any first-party | A+B+C: any source | D: none found |
|---|---|---|---|---|
| Individuals (n=10) | 1 (10%, 2-40%) | 3 (30%, 11-60%) | 8 (80%, 49-94%) | 2 (20%, 6-51%) |
| Organisations (n=12) | 5 (42%, 19-68%) | 6 (50%, 25-75%) | 8 (67%, 39-86%) | 4 (33%, 14-61%) |
| Both (n=22) | 6 (27%, 13-48%) | 9 (41%, 23-61%) | 16 (73%, 52-87%) | 6 (27%, 13-48%) |

Why these are rough: the sample is not random; three of the five class-A organisations are advocacy groups whose business is publishing positions, so a sample weighted to companies (Visa, Google, PG&E, Williams-Sonoma, which were not assessed) would likely score lower; "none found" reflects a search of the donor's name plus a topic, not a crawl of the donor's site; and class A/B boundaries (is a philanthropic focus a "priority"?) are a judgement the maintainer has not yet made.

## 3. How citable each kind of source is

What a reporter needs to check a pairing in minutes: the exact words, at a URL that still shows them, with a date.

| Kind of source | Exact words? | Stable URL? | Dated? | Notes |
|---|---|---|---|---|
| Per-election voter guide (GrowSF) | Yes | Yes, one per election | Yes (election named) | Best fit seen: a statement tied to a named contest. |
| Agenda / issues page (Chamber, SEIU 1021) | Yes | Yes | Often not | Page is edited in place; keep a dated copy. |
| Newsroom post (Airbnb) | Yes | Yes | Yes | Company-wide, not tied to a measure. |
| Foundation or firm "about" page (Emerson) | Yes | Yes | No | General mission; shows an interest area, not a local position. |
| Social post or bio (Stoppelman) | Yes | Per-post | Yes | Platform may block or alter access; terms not read. |
| Ethics Commission committee "Purpose" | Yes | Yes | Per election | Only "supports/opposes X"; a registered position, not a priority. |
| IRS mission statement (GuideStar) | Yes | Yes | By tax year | Generic; useful only for nonprofits. |
| News interview or profile | Quote only | Yes | Yes | Third party; outside the project's own-material rule. |

## 4. Can the statements be fetched and watched?

What the evidence supports, by source:

- **Public organisation pages (class A, B).** Ordinary pages. A poller could fetch each page, strip the navigation, keep the main text with a content hash and the retrieval date, and flag a change for a person to read. The Hop did not fetch any of these pages itself in full (they appeared as search excerpts), so whether each returns clean text to an automated client, and whether any is behind scripts or bot protection, is not tested. `robots.txt` and terms of use of the donor sites were not read.
- **Freshness varies.** GrowSF publishes new election-specific pages (the June and November 2026 guides have separate URLs), which suggests watching a *guide index* for new URLs rather than one page. SEIU 1021 posts endorsement pages per election. The Chamber agenda looks static. Airbnb's post is an old statement.
- **Social profiles.** An X profile is the only individual-donor source of class A; fetching it automatically depends on a platform's access rules that were not examined. Treat as manual.
- **Official records.** The Ethics Commission site's pages are generated from the same daily-refreshed data the campaign finance survey describes, so the "Purpose" line and top-contributor tables can be fetched and compared on the same nightly cadence; they hold no priorities beyond support/oppose.
- **What a watcher cannot do.** It cannot tell which sentence is the "priority", whether a new sentence replaces an old one, or whether a donor's silence means no priority. The project's rule against paraphrase means every stored statement needs a person-confirmed exact quote.
- **For individuals** there is mostly nothing to watch, so a way to enter a statement by hand (quote, URL, date, who confirmed) would be needed for any individual who is to appear with a priority.

Points for Pairing site first version, stated as evidence and not as a choice: a poller alongside speech and filings would cover a minority of donors (the organisations that publish agendas or voter guides), at the cost of a review step for each change; an entry screen would cover the rest; the evidence does not say which alone is enough. If the first version includes only class-A donors, the evidence suggests most top individual donors would appear without a priority.

## 5. How this serves the objectives

- **Let a reporter check any pairing in minutes.** Class-A statements with an exact quote, URL and date can be checked in about the time it takes to open the page and find the sentence; class B/C cannot meet that bar with the donor's own words. No timing was done in this Hop. A candidate key result that could be written from these findings: *of the top N donors by dollars to a given official's committees, how many have a class-A statement, and how long does a local reporter take to confirm each pairing's quote and amount*. This needs the dollar ranking for the officials (campaign finance survey data) joined to the class table above; the 22-donor sample is the first rows of that table (`donor-sample.json`).
- **Everything shown is current and correct.** Pages that edit in place (Chamber, SEIU) can go stale without notice; a retrieval date and content hash would show when a quoted statement was last seen on the donor's page. The Chamber agenda is the clearest example of a page that may no longer reflect current priorities.

## 6. Sources used

Pages read in full in this run: Mission Local, "BigMoneySF: How Mayor Lurie's efforts to reshape City Hall brought in a new donor class" (2026-10-20, https://missionlocal.org/2026/10/big-money-san-francisco-lurie-charter-reform-labor-moderates-billionaires-democrats-election/); Mission Local, "Who's bankrolling San Francisco's coming election? These 16 donors." (2026-09-11, https://missionlocal.org/2026/09/san-francisco-november-election-top-donors/); DataSF dataset description for Transactions (https://data.sf.gov/api/views/pitq-e56w.json).

Pages seen only as search-result excerpts (the excerpt, not the full page, is what the assessments rest on):

- Ethics Commission election pages: https://campaign.sfethics.org/elections/2026-11-03/measures/measuredef.html ; .../measureh.html ; .../measureg ; .../2026-06-02/measures/measurecd.html ; .../2026-06-02/measures/measured.html ; .../2026-11-03/contributors ; committee pages CA1479782 (Muni measure committee), CA1433436 (GrowSF Voter Guide), CA970630 (Labor Council committee).
- GrowSF: https://growsf.org/voter-guide/ ; https://growsf.org/about/ ; https://growsf.org/voter-guide/san-francisco-voter-guide-june-2026-election/
- SF Chamber of Commerce: https://sfchamber.com/advocacy/agenda/ ; https://sfchamber.com/advocacy/
- SEIU 1021: https://www.seiu1021.org/issues-legislation ; https://www.seiu1021.org/post/election-endorsements-nov-3-2026
- Emerson Collective: https://www.emersoncollective.com/index.php?p=about-us
- Airbnb: https://news.airbnb.com/an-update-about-our-community-in-san-francisco
- Neighbors for a Better San Francisco: https://finance.yahoo.com/news/neighbors-better-san-francisco-launches-140200587.html ; https://www.guidestar.org/profile/86-2339545
- Jeremy Stoppelman: https://x.com/jeremys
- Crankstart (third-party descriptions): https://www.insidephilanthropy.com/find-a-grant/grants-c/crankstart-foundation
- Larsen and Lam: https://www.svcf.org/annual-reports/donor-2025/donor-stories-2025-26-larsenlam ; https://missionlocal.org/2024/02/prop-e-police-surveillance-sf/
- San Francisco Chronicle, "These are the wealthy people trying to reshape S.F. politics" (top-ten donors this decade): https://www.sfchronicle.com/projects/2026/san-francisco-election-donors/ (page itself not retrievable; excerpts only)
- Others: Mission Local on Jan Koum (https://missionlocal.org/2026/04/sf-jan-koum-daniel-lurie-campaign-finance/); Chronicle on Pritzker's UCSF gift; SF Standard on Lurie's donors (https://sfstandard.com/2026/10/28/san-francisco-mayor-daniel-lurie-money-campaign-election-2026/); Ballotpedia endorsements by the SF Police Officers Association; Department of Elections voter guide PDF (https://media.api.sf.gov/documents/N26_EN_VIP.pdf).

## Open questions

### What was looked for and not found

- **Own pages of the individual megadonors.** Searched by name plus topic for Moritz, Larsen/Lam, Pritzker, Dolby, Wolthuis, Seibel, Conte, Koum. No own site or statement about local priorities found for any except Stoppelman's X profile (class A) and Doerr's climate book. Crankstart's own site and the Larsen/Lam foundation pages were not opened.
- **Own pages of Anthropic, OpenAI, Ripple, SF Realtors, SF Labor Council, SFPOA.** Searched; only third-party or committee-filing pages came back. The unions' and associations' own sites (sfpoa.org, sflaborcouncil.org, sfrealtors.com beyond its home page) were not opened.
- **A feed, API or change log on any donor page.** Not seen; RSS and sitemap presence was not tested.
- **robots.txt and terms of use** of every donor site and of the social platform: not read.
- **Whether the Voter Information Pamphlet's ballot arguments are a source of donor-signed statements.** The pamphlet PDF appeared in search, but its arguments were not read; that proponents' paid arguments carry named signers is recalled, not read here (recalled).
- **Whether San Francisco lobbyist or behested-payment filings state the issues a donor cares about.** Behested payments are mentioned in SF Standard's reporting on the Mayor's donors; the issue fields of lobbyist filings were not looked at (recalled that lobbyist reports list the matters lobbied).
- **A ranking by dollars of the officials' largest donors across all years.** The sample frame is the 2026 Ethics Commission tables, not a computed ranking from the Transactions dataset.

### Claims not verified

- That the Chamber agenda page is stale: inferred from its COVID-19 opening and a search index age of roughly 600 days (unverified).
- That Crankstart's focus areas are as Inside Philanthropy and a profile site describe them, since its own pages were not opened (unverified).
- That the John Pritzker in the Ethics tables is the Hyatt heir whose UCSF gift the Chronicle describes; Mission Local and the Chronicle both say so, but no filing was checked (unverified).
- That Stoppelman's X profile text and the post on the Great Highway are current; the page was seen only as an indexed excerpt with an old index date (unverified).
- Shares and ranges are computed on 22 donors chosen by prominence; they are not estimates for all large donors.

### Questions for the maintainer

- Does a donor's **philanthropic or general focus** (an Emerson or Crankstart mission page) count as a "stated priority" for a pairing, or only a statement about a local-government issue? This moves individuals from 10% to 30% and organisations from 42% to 50%.
- Should a **sponsored committee's money** (a committee "sponsored by" Airbnb or the Chamber) be paired with the sponsor's statements?
- Should an individual with **no first-party statement** appear in pairings with the priority left blank, or be left out until one is found?
- Is a **statement made through a company** (a CEO's company page) the donor's own, when the donor is the CEO?

### What would turn this into a measurable key result

- The dollar ranking of each official's largest donors (from the campaign finance survey's data), joined to the class table here, to give "share of top-N donors by dollars with a class-A statement".
- Timing two or three local reporters as they verify a handful of real pairings built from class-A rows, as the objective's note describes.
