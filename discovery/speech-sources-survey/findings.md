# Speech sources survey: where San Francisco officials' exact words can be collected

**Kind of hop: a survey** of sources outside the project (public recordings, captions, transcripts and the rules around fetching them). It records what exists; it makes no decisions. Evidence is from pages read or searched during this research; the latest Legistar calendar read was a snapshot from late October 2026, so "now" below means that period.

## Summary by charter question

1. **What exists, and what gives exact words with a jumpable reference?** The city's own pipeline is the best source. Every Board of Supervisors meeting and committee meeting is recorded by SFGovTV and archived on Granicus, and the Board's Legistar calendar links a **Video, Audio and Transcript** per meeting. The Legistar transcript is a full caption text with a `HH:MM:SS` stamp on every line, so each quote can carry a time. It is the only first-party source read that gives words plus a time. Minutes are not verbatim. The Mayor has no equivalent full archive: the Mayor's words come from (a) the monthly appearance at the Board, which is inside the Board transcript, (b) selected press conferences on SFGovTV and on news outlets' video, and (c) written statements and "remarks as prepared" on sf.gov, which are not a record of what was said aloud.
2. **How often, and how soon?** The Board meets on Tuesdays at 2:00 pm and its committees meet on set weekdays, about four meetings a week in the October 2026 calendar. The Sunshine Ordinance requires recordings on the city site within 72 hours. In the late-October 2026 calendar snapshot, meetings up to the 22nd already showed minutes, video, audio and transcript while the 26th onward showed "Not available". Exact per-meeting lag was not measured.
3. **How accurate, and who is speaking?** The 2026 transcripts are real-time captions in capitals with speaker changes marked only by `>>`, not names. Sampled text has misheard names, numbers and words (examples below). Older captions (2012, 2018) carry speaker labels. A transcript alone cannot meet a word-for-word spot check; each quote needs checking against the recording.
4. **Terms and limits?** No page read forbids automated fetching. sf.gov's disclaimer concerns accuracy and liability only, and DataSF's public-domain terms cover datasets on the open-data portal. The `robots.txt` files and the Granicus and Legistar terms of service were **not read**, so the permitted pace is unknown. The Legistar Web API's availability for San Francisco is unverified.

## Map of sources

| # | Source | Covers | What it holds | Exact words + time reference? | Notes |
|---|--------|--------|---------------|-------------------------------|-------|
| A | **Legistar calendar and `Transcript.aspx`** (`sfgov.legistar.com`) | Board, all standing committees, some special and joint meetings | One row per meeting with Agenda, Minutes, Video, Audio (+download) and Transcript columns | **Yes**: per-line `HH:MM:SS` stamps | Best candidate for first-version polling. Transcript URLs have the form `Transcript.aspx?ID1=<number>`; the number looks like the Granicus clip number (my reading). |
| B | **Granicus video archive** (`sanfrancisco.granicus.com`, one publisher view per body: Board `view_id=10`, Land Use and Transportation `view_id=177`, Rules `view_id=13`, Government Audit and Oversight `view_id=11`) | Same meetings | Video player with an agenda **Index** and subtitles, RSS feeds per body, `TranscriptViewer.php?view_id=..&clip_id=..` | Yes for transcript viewer; the player's index jumps to agenda items | RSS items read "The agenda for ... has been archived" with a link to the clip. |
| C | **Meeting minutes** (PDFs on `media.api.sf.gov/documents/`, older ones on `sfbos.archive.sf.gov`) | Board and committees | Action minutes: who moved, how members voted, summaries such as the Mayor "addressed the Board regarding" a topic | **No** (summaries, page numbers only) | Useful to confirm attendance, votes and who held the floor. |
| D | **Agenda PDFs** (Legistar `View.ashx?M=A`) | Same | Agenda items, file numbers, the statement that meetings are real-time captioned | No | The agenda gives the item order that can help name speakers. |
| E | **Mayor: Board "special order" appearance** | Mayor, monthly | Charter 3.100(7) requires the Mayor to appear at one regular Board meeting each month for policy discussion; it is a numbered item on that agenda | **Yes**, through source A or B transcript of that meeting | Only a few exchanges a month. |
| F | **Mayor: SFGovTV press conference archive** (Granicus `view_id=18`) | Mayor | "Select coverage" of press conferences, held "at the call of the Mayor" | Video only; no caption text read | Coverage is selective. |
| G | **Mayor: sf.gov Office of the Mayor news** | Mayor | Statements, press releases, State of the City text "as prepared for delivery" | Text, but **not verbatim of speech**; no time reference | Quotable as a written statement only, not as something said. |
| H | **News-outlet video of Mayor press conferences** (YouTube uploads) | Mayor | Full or partial press conferences | Video with time offsets; platform auto-captions not assessed | Third-party content; reuse terms not read. |
| I | **SFGovTV YouTube channel and cable channel 26** | Original programming and live streams | Not assessed for Board meetings | Unknown | Not shown to hold the Board archive. |
| J | **Third-party transcript sites** (`sfgovernmentconnection.com` "SmartTranscripts", `redtaperecordings.com`) | Board, committees, other bodies | Machine transcripts with some named speakers and clip selection | Names for some turns; many turns labelled "Speaker 20.0" | Operators, accuracy and reuse terms unknown. One sampled Board of Education transcript contained the phrase "SFGov TV, San Francisco government television" attributed to commissioners, which suggests the machine transcript picked up broadcast bumper audio. |
| K | **Legistar Web API** (`webapi.legistar.com/v1/{Client}`) | Meetings, items, votes | Structured data, not speech | No | Some clients need a token. One project's README says San Francisco's mirror stopped updating around 2018 (unverified; not tested here). |
| L | **Sunshine Ordinance Section 67.14** | Rule, not a source | Recording rule | n/a | See "Publication timing". |

Related bodies on the same Granicus platform (SFUSD Board of Education `view_id=47`, commissions) exist but are outside the Board and Mayor scope set by the brief.

## Exact words with a time or page reference

- **Legistar transcript (source A).** Read in full for the Public Safety and Neighborhood Services Committee of 9 July 2026 (`Transcript.aspx?ID1=52816`). Every line starts with a stamp such as `00:18:05`, counted from the start of the recording. A quote can therefore cite "meeting, body, date, hh:mm:ss". The stamps are line starts, so a quote that spans lines needs the first line's stamp.
- **Granicus (source B).** The clip player offers an agenda **Index** (items such as "11 ROLL CALL AND ANNOUNCEMENTS" followed by file numbers), so an agenda item can be linked. Whether a Granicus player URL accepts a start-time parameter for San Francisco was not tested; another Granicus site's links use an `entrytime` parameter in seconds (unverified for San Francisco).
- **Minutes (source C)** give no timestamps and no words. They can confirm who was present and how each member voted.
- **Meetings covered.** The Legistar body list includes the Board, Budget and Appropriations, Budget and Finance, Government Audit and Oversight, Land Use and Transportation, Public Safety and Neighborhood Services and Rules committees, plus special and joint meetings and many inactive committees. A joint special meeting on 8 October 2026 had minutes but no video, audio or transcript, so not every meeting has a recording.
- **Depth of history.** The Legistar calendar year filter runs back to 1998. Transcripts were seen for 2012 (Granicus viewer), November 2018 (Legistar) and 2026. Which years have a transcript was not enumerated.

## Publication timing

| Item | Evidence |
|------|----------|
| Rule | Sunshine Ordinance 67.14(c): the City must make audio or video of noticed meetings in equipped City Hall rooms available digitally on the city website **within 72 hours** and keep it at least two years. It admits exceptions for technical reasons. |
| Observed calendar | Legistar snapshot, late October 2026: meetings on 1, 5, 6, 7, 8 (rescheduled committee), 15, 19, 20, 21 and 22 October showed Minutes, Video, Audio and Transcript links; 26 to 29 October showed "Not available" for all. So the lag for the 22nd was at most a few days. The exact hour each item appeared was not captured. |
| Minutes | The minutes PDF for the Board meeting of 14 July 2026 carries "Printed at 4:45 pm on 7/15/26" (search extract), i.e. the day after the meeting. |
| Agendas | The agenda for 7 October 2025 was printed on 2 October 2025, five days ahead. The Board packet is described as usually available the Friday before the meeting. |
| RSS | Granicus RSS items give the meeting date with a fixed early-morning time as the publication date (for example a 21 July 2026 item stamped 21 Jul 2026 02:15), so the feed date does not measure publication lag (seen in a search extract). |

**Cadence of new material.** The October 2026 Legistar calendar shows the Board on Tuesdays at 2:00 pm (6, 20 and 27 October listed), Land Use and Transportation on Mondays 1:30 pm, Rules on Mondays 10:00 am, Government Audit and Oversight on Thursdays 10:00 am, Budget and Finance on Wednesdays 10:00 am and Public Safety and Neighborhood Services on Thursdays 10:00 am: sixteen records for the month's calendar view. The Mayor's appearance is monthly. Press conferences are irregular. What this implies for polling, as evidence not as a decision: new Board speech arrives in weekly batches, and the 72-hour rule with the observed few-day lag means a daily check of the Legistar calendar would see each transcript soon after it appears, while hourly checks would add little.

## Accuracy and speaker identification

Sampled: the 9 July 2026 committee transcript (source A).

- **Format.** Capital letters, no reliable sentence casing, and `>>` marks a change of speaker. **No speaker names** are given in the 2026 text; the reader infers the speaker from context, the agenda and the roll call.
- **Observed errors**, found by reading the text against what the same text implies: the opening "READY GOOD MORNING"; a Fire Department deputy chief's name given as "PET RABBITS" and then "PATRICK RABBITT"; the chair's colleague "Supervisor Wong" rendered as "SUPERVISOR HUANG" and "REMEMBER WONG" (for "Member Wong"); "I HAVE THREE EYES" for "three ayes"; "SPEEDY SAFETY SYSTEM" for the speed safety system; the clerk's e-mail address spelled out incorrectly; "BISHAN" where a sentence about bread baskets clearly meant something else. These are caption-grade errors in names, titles and short words, which are exactly what a verbatim quote and an attribution depend on. No measured word error rate was computed.
- **Who produces it.** Agendas say meetings are "real-time captioned", so the transcript is probably the live captioning feed; the text is consistent with that (my reading). No statement by the city or captioning vendor about accuracy was read.
- **Older eras are better labelled.** A 2012 Granicus transcript labels turns "President Chiu:" and "Clerk Calvillo:", and a November 2018 Legistar transcript labels turns "Supervisor Stefani:" (search extracts).
- **Third-party transcripts (source J)** name many speakers ("[Rafael Mandelman, Board President (District 8)]") but leave others as "Speaker 20.0" and show machine artifacts. Their accuracy was not measured.
- **Mayor.** Prepared remarks on sf.gov may differ from what was said. Only the recording or a caption of it is the spoken record.

**Consequence for the weekly verbatim spot check.** From transcripts alone the check cannot be met: names, numbers and short words are unreliable, and the speaker is unnamed. The transcript is good for locating a passage and its timestamp; the words must be confirmed by listening to the recording at that timestamp.

## Terms of use and technical limits

- **sf.gov disclaimer** (read): information is provided for convenience, the City does not certify the authenticity of third-party information, and it disclaims liability. It says nothing about automated access or reuse limits.
- **DataSF terms** (search extract): datasets on data.sfgov.org are offered under a Public Domain Dedication and License unless a file says otherwise. This covers portal datasets, not the Legistar or Granicus pages; no speech dataset on the portal was found.
- **Public record status.** Section 67.14 makes meeting recordings public records that may not be destroyed, and requires playback without charge.
- **Not read:** `robots.txt` for `sf.gov`, `sfgov.legistar.com` and `sanfrancisco.granicus.com`; Granicus or Legistar terms of service; any rate limit statement; YouTube's terms. A third-party project that scrapes `sfgov.legistar.com` reports caching responses and rate-limiting its own requests, which is a courtesy and not evidence of a published limit.
- **Practical pace.** The data change at most a few times a day, so a polite pace (one calendar request and a handful of transcript pages per day) is far below anything a public site would likely object to, but the allowed pace is unconfirmed.

## How this serves the objectives

- *Let a reporter check any pairing in minutes:* source A gives a link plus a timestamp to the recording, and the recording is public and free. The remaining cost is listening, because the caption text cannot be trusted word for word. A timing study of reporters could include "time to confirm a quote at a timestamp".
- *Everything shown is current and correct:* new Board speech is available within days, so a daily check keeps the site current; correctness depends on the recording check, not the caption.
- The non-goal "no paraphrasing" is compatible with source A only if quotes are confirmed against audio; sf.gov statements (G) must be labelled as written statements.

## Open questions

**Looked for and not found**
- Any city statement of caption accuracy or the vendor producing the captions. Looked at the agenda text, sf.gov SFGovTV pages and Legistar's calendar.
- `robots.txt` and the terms of service of Legistar and Granicus; a published rate limit. These pages could not be read in this research.
- Mayor press-conference transcripts or captions from SFGovTV; whether SFGovTV's YouTube channel carries Board meetings.
- Which years of Board and committee meetings have a Legistar transcript, and whether transcripts are ever revised after posting.

**Claims not verified**
- That the Legistar `ID1` number equals the Granicus clip number (my reading, from clip numbers in the same range).
- That Granicus player links for San Francisco accept an `entrytime` start offset (unverified).
- That the Legistar Web API for San Francisco is stale (unverified; one project's claim).
- That the exact lag between meeting and transcript is under four days for every meeting; only snapshot bounds were seen.
- The date of the latest calendar snapshot: it falls between 22 and 26 October 2026 as inferred from which rows had links (my reading).

**Questions for people**
- Maintainer: which bodies beyond the Board and its committees and the Mayor (for example commissions, the School Board, the City Attorney) belong in scope, and is a written press statement quotable if it is labelled as written, not spoken?
- Maintainer or site operator: may the first version contact the Clerk of the Board or SFGovTV to ask about the captioning vendor, permitted fetch rates, and a transcript feed?
- A reporter or watchdog (for the key result): how long does it take to confirm one quote from a caption timestamp against the recording?
