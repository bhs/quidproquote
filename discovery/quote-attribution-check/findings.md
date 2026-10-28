# Quote attribution check: can a 2026 transcript quote be tied to the official and the recorded moment?

**Kind of hop: a survey** of sources outside the project (the city's captions, calendar and archive, plus two third-party transcript sites), read against the three charter questions. It records what was observed and how well it is sourced; it makes no decisions. **No audio or video was played in this research**, so nothing below was checked by listening. Where the charter asks for a comparison "with what is heard", the finding is what the transcript text itself gives away, and a clear statement of what remains untested.

Builds on `discovery/speech-sources-survey/findings.md` (called "the speech survey" below). Funding and donor questions are out of scope.

## Summary by charter question

1. **Tying an unnamed passage to the official.** Not reliably from the city transcript alone. The `>>` marker is neither a complete nor a clean speaker-change signal in the 21 April 2026 Board transcript: speakers change with no `>>`, and `>>` appears inside one person's remarks. What does work as a *candidate* generator is the spoken cue ("Supervisor X", "District N Supervisor X") that the chair or clerk says just before a member speaks, but the captions garble those very names (the Board President's surname was never rendered correctly in any of nine roll calls read). Strength of the cue depends on the kind of segment (see the table). Every route found gives a *proposed* speaker; confirming it needs the agenda, the minutes or the video. Answered in part: the routes and their failure modes are mapped; their hit rate was not measured.
2. **Time stamps and meeting references.** Partly. The stamp structure is clear (line-start stamps counted from `00:00:00` of the recording, with gaps where nothing is captioned), and the transcript's own spoken opening ("the April 21st 2026 regular meeting") can validate a meeting reference. Whether a stamp lands on the same second of the archived video was **not** tested, because no archive player page could be opened. The calendar rows do not expose the recording link in their static HTML, and the Legistar calendar's meeting ids are a different number from the transcript id, so the "calendar row to recording" step is unresolved. Ids of transcripts and clips rise together with meeting date, which is consistent with, not proof of, one shared id.
3. **Transcript wording against the recording.** Not measurable here (no audio). What the text shows without audio: a dense set of caption-grade errors in names, titles, numbers and small words, including one passage whose own numbers contradict each other. The earlier conclusion stands, now with more examples: transcript wording cannot be published as "word for word" without listening at the stamped moment. A rate of difference per quote is **not found**.

## What was read

| # | Item | What it is | Used for |
|---|------|-----------|----------|
| 1 | Legistar `Transcript.aspx?ID1=52251` | Full caption transcript of the Board of Supervisors regular meeting of 21 April 2026; read from `00:00:13` to `01:49:14` (the page text was cut there) | Attribution and error audit |
| 2 | Legistar calendar (`Calendar.aspx`), October 2026 view | 16 meeting rows with Agenda, Minutes, Video, Audio, Transcript columns | Meeting reference |
| 3 | Granicus listings and RSS (search extracts of `ViewPublisher.php?view_id=192` and `view_id=10`, `ViewPublisherRSS.php?view_id=10`) | Clip ids, dates, durations | Id and date relation |
| 4 | `sfgovernmentconnection.com` SmartTranscripts (search extracts for 3 Feb, 10 Feb 2026 and 29 Jul 2025 Board meetings) and its open-source README (`github.com/ang-eichhorst/legitalk`, a fork of the pipeline) | Independent machine transcripts with speaker names | Attribution aid, independence check |
| 5 | `sfbos.org`, `lwvsf.org` (search extracts) | Current Board roster | Name mapping |

Not read: the Legistar transcript of the 9 July 2026 committee meeting used in the speech survey (only its recorded findings are used), any minutes PDF, any Granicus player or transcript-viewer page (only search extracts), any Mayor press-conference caption.

## Q1. Tying a passage to the official who said it

### What the city transcript gives

- Format of the 21 April transcript: one line per caption row, each with a `HH:MM:SS` stamp, all capitals, `>>` at some points where the speaker seems to change. No names.
- The Board's own procedure leaves spoken cues in the text. Examples: `00:44:42 >> NEXT UP WE HAVE DISTRICT FIVE SUPERVISOR MAHMOOD`; `00:50:30 >> NEXT UP DISTRICT SIX SUPERVISOR DORSEY`; `01:06:29 AND NEXT WE HAVE DISTRICT TEN SUPERVISOR WALTON`; `00:03:32 MOVED BY CHAN SECONDED BY WALTON`; and the clerk's roll for introductions, which names each member before they speak.

### How reliable `>>` is (observed on 21 April 2026)

| Observation | Example (stamp, paraphrase of position) | Meaning |
|---|---|---|
| Speaker changes **without** `>>` | `00:18:00` the clerk calls a member and the member begins on the same line; `00:19:34` to `00:19:40` three members called in a row, two with no `>>`; `00:35:06` to `00:35:12` clerk then Supervisor Chen | `>>` misses changes |
| `>>` **inside** one member's remarks | `00:18:20` and `00:18:40` inside a single hearing request; `00:22:10` and `00:23:44` inside one resolution speech; `00:27:23`, `00:27:28` and `00:28:00` inside one commendation (my reading from the surrounding text) | `>>` also marks pauses or paragraph breaks, so it over-counts changes |
| Roll-call names are not the speaker | `00:08:16` to `00:08:43` the clerk reads each member's name and the member answers "I" | A name next to a passage can be the person being called, not the person speaking |
| Name cue is attached to the *previous* speaker's thanks | `00:55:44` to `00:56:02` "thank you ... Supervisor Dorsey ... Supervisor Chen" then Chen's remarks | The cue for who speaks next sits at the end of the previous turn |

### Segment types and how well a cue identifies the speaker

| Segment type (as seen on 21 April) | Cue available | Strength (my reading) |
|---|---|---|
| Item reading by the clerk and the President's motions | Role phrases ("MADAM CLERK, PLEASE CALL ITEM"), repeated formulas | Strong for clerk versus President as roles; the President's *name* is not in the text at all |
| Member speaks on an item (e.g. `00:05:30`, "SUPERVISOR MELGAR THANK YOU PRESIDENT") | Member's name in the opening words | Strong when the caption renders the name legibly |
| Roll call for introductions, in-memoriam, resolutions | Clerk or President names the member | Medium to strong; unnamed changes inside a long run of members need the agenda order |
| 2:30 pm special order (commendations) | "District N Supervisor X" cue, then honorees speak | Strong for the member's opening remarks, **weak afterwards**: honorees, other members and the President alternate with few cues |
| Public comment | Speakers say their own names | Names are captioned phonetically (for example a speaker's surname appears as a different surname-like phrase) and public speakers are not officials |
| Committee hearings with back-and-forth (the 9 July 2026 sample in the speech survey) | None beyond the chair's calls | Weak; members interject |
| The Mayor's monthly appearance | Not sampled | Unknown |

### Name garbling that breaks cue matching (21 April 2026)

| Official (district) | Renderings seen in the same transcript |
|---|---|
| Rafael Mandelman, President (D8) | "GENTLEMAN", "MANAGEMENT", "BENJAMIN", "MANDOLIN", "RANDLEMAN", "MENDHAM", "MADAM" (in roll calls), nine of nine roll-call instances read |
| Danny Sauter (D3) | "SADR", "SARDAR", "SLATER", "SOLDER", "SAUTER" |
| Stephen Sherrill (D2) | "CHERYL", "SHERRELL", "SHERYL" |
| Alan Wong (D4) | "WONG", "WANG", "HUANG" |
| Chyanne Chen (D11) | "CHEN", "CHEYENNE CHEN", "CHAD", "CHIN", "JEN" |
| Connie Chan (D1) | "CHAN"; read as a different member when the caption says "CHEN" (the two surnames differ by one letter) |

Roster source: current members by district, `sfbos.org` and `lwvsf.org` (Chan D1, Sherrill D2, Sauter D3, Wong D4, Mahmood D5, Dorsey D6); Mandelman D8, Fielder D9 and Walton D10 appear in the SmartTranscripts labels; Melgar D7 and Chen D11 (the latter also on her Wikipedia page) are not in the extracts read for D7 (recalled). A one-letter surname pair (Chan, Chen) means a fuzzy-matching attribution can silently pick the wrong official.

### Routes to a speaker, from what was found

| Route | What it gives | Failure mode seen or implied |
|---|---|---|
| A. Spoken cue before the passage, matched to the roster by district and fuzzy name | A proposed speaker for floor remarks | Captions garble names (table above); cue sits at the end of the previous turn; roll-call names are not speakers |
| B. Agenda order and item numbers (agenda PDFs are on Legistar) | Which items and which sponsors are on the floor at a stamp | Does not say who spoke inside an item |
| C. Action minutes (moved by, seconded by, vote) | Confirms who moved and how members voted | No words or times (speech survey) |
| D. Independent diarized transcript with names (SmartTranscripts shows `[Rafael Mandelman, Board President (District 8)]`, `[Angela Calvillo, Clerk of the Board]`) | Named turns for many passages | The README of its open-source pipeline says an automatic speech-to-text service transcribes the audio and a language model identifies the speakers, so the names are inferred, and unidentified turns show as "Speaker 22.0" and similar. The labels are a hint, not a record |
| E. Watching the video at the stamp | The speaker is visible at the podium or in the chamber | Needs a person; whether the broadcast carries name captions was not seen |
| F. Voice matching against known members | Not tried | (recalled) a technique used in speaker diarization; accuracy on this chamber's audio unknown |

## Q2. Time stamps and meeting references

### The stamp as it appears in the text

- Stamps are line starts counted from the beginning of the recording. In the 21 April transcript the first caption is at `00:00:13` and the text read runs to at least `01:49:14`.
- Caption rows are a few seconds apart (for example `00:05:23`, `00:05:25`, `00:05:27`, `00:05:30`); two rows can share nearly the same second (`00:02:18` and `00:02:19`).
- Stamps follow media time, not speech: there are silent or music stretches with no captions (`00:43:43` to `00:44:42`, a sung passage ending at `01:16:14` followed by `01:17:39`, and `01:41:49` to `01:42:04`). A reader can therefore not infer position from the amount of text.
- The text of a row is captioned live, so a row's stamp is when the caption appeared (my reading, since the agendas say meetings are real-time captioned, per the speech survey). A live caption normally trails the words it renders by some seconds (recalled). A quote's stamp therefore likely points a few seconds **after** the speech began, not at it. This lag was not measured.
- A quote that spans rows needs the stamp of the first row, and a safe link would start earlier than the stamp. How many seconds earlier is untested.

### Whether the stamp equals the archived recording's second: untested

- No Granicus player page could be opened, so no stamp was compared with a played second.
- The player's "Entry Time" and "Stop Time" fields and `entrytime` links exist (speech survey); the unit was read as seconds. Still untested.
- The Granicus listing's "Date" column is an epoch value that equals **midnight Pacific** on the meeting date (`1780988400` is 9 June 2026 00:00 PDT; `1780383600` is 2 June 2026 00:00), so it cannot anchor a wall-clock start time. Listed durations exist (for example 2 h 28 m for the 9 June 2026 Board meeting, 1 h 57 m for 2 June); a transcript's last stamp can be compared with that duration to detect a trimmed or mismatched recording, but only the 21 April transcript was read and its listing was not.
- Granicus documents a trimming tool for archived video (search extract of its support pages: pick start and end points and the system keeps a backup of the original). If an archive is trimmed after captions were produced, every stamp would shift. Whether SFGovTV trims Board meetings is unknown, and the article itself could not be read in full (unverified).
- The independent SmartTranscripts site transcribes the audio it downloads from the video, so its time offsets are tied to the audio by construction, and its pages offer text selection that plays the matching clip; this gives a second timeline to compare with the city's stamps. It was not compared.

### Whether the calendar's meeting reference leads to the right recording

| Check | Result |
|---|---|
| Legistar calendar row to the media | In the static page the Video, Audio and Transcript cells are links to `#` (filled in by page script); the real clip address is **not** visible in the page text. Rows with no recording say "Not available" in all three cells |
| Calendar meeting id versus transcript id | Different numbers: Public Safety and Neighborhood Services of 22 October 2026 is meeting id `1455122` on the calendar, while transcript ids are of the order of `52251`. The two are separate namespaces |
| Transcript id versus clip id | Ids rise with meeting date across sources: clip `51452` is the 6 January 2026 Board meeting, transcript `52251` is the 21 April 2026 Board meeting, transcript `52816` is the 9 July 2026 committee meeting (speech survey), clip `52849` is the 14 July and clip `52901` the 21 July 2026 Board meeting. Consistent with the Legistar transcript id being the Granicus clip id; not shown for any one pair |
| Transcript content versus meeting reference | The transcript opens with the date and type ("the April 21st 2026 regular meeting of the San Francisco Board of Supervisors") and a roll call. 21 April 2026 is a Tuesday, the Board's regular day. A cheap automatic check is to compare the spoken date with the calendar row's date; the calendar row for 21 April was not read (only an October 2026 view) |
| Rows without a recording | The joint special meeting of 8 October 2026 had minutes but "Not available" for video, audio and transcript, so a calendar row can exist with nothing behind it |
| Same-day multiple meetings | 5 October (Land Use 1:30 pm and Rules 10:00 am) and 8 October (a joint special meeting at 10:00 am and a rescheduled committee at 12:30 pm) show two meetings on one date, so date alone is not a safe reference; body, date and time are needed |

## Q3. Transcript wording against the recording

### What could not be done

No recording was played, so no line was compared with audio, and no per-quote rate of difference was produced. The speech survey's single committee sample and this research's Board sample are both read text only.

### What the 21 April 2026 text reveals without audio

Errors are listed from the text alone (a reader who knows the setting can see them); each is something a verbatim quote could not carry.

| Kind | Examples (stamp) | Effect on a published quote |
|---|---|---|
| Official's name | President's surname unrecognizable in all nine roll calls read (`00:00:40`, `00:04:21`, `00:05:07`, `00:08:32`, `00:09:33`, `00:14:31`, `00:15:56`, `00:16:03`, `01:47:38`); "SUPERVISOR CHEYENNE CHEN" (`00:13:53`) | Wrong or unmatched speaker |
| Other proper nouns | The city's broadcaster rendered three ways ("S.F. CAPTIVE TV" `00:02:07`, "S.F. GOP TV" `00:02:34`, "S.F. GOP TALK" for an e-mail address `00:02:38`); the street address of City Hall mangled (`00:02:46`); the same cultural district as "SOMA", "SALMA", "SANTA", "SUMMER" and "SOME OF" Pilipinas in one passage (`00:51:00` to `01:05:15`); "HAZE VALLEY" and "HAYES VALLEY" (`00:44:53`, `00:45:27`) | Misspelled or invented names |
| Vote words | "THREE EYES", "NINE EYES", "EIGHT EYES" for ayes (`00:05:11`, `00:08:39`, `00:09:38`, `00:14:35`) | Changes the meaning of a vote line |
| Numbers and dates | "TERM ENDING FEBRUARY 4TH, 2013" for an appointment made in 2026 (`00:13:53`; implausible, my reading); "CALL IT NUMBER SEVEN" for item 27 (`00:13:45`) | Wrong figures |
| Self-contradicting passage | A public comment says a building "was completed on a $5 million building permit in 1999 that expired in 1992" (`01:18:33` to `01:18:48`): a permit cannot expire before the work it covers, so a digit is wrong either in the caption or in what was said, and only the recording says which | A verbatim rule needs the recording even to decide what the words were |
| Factual slip that may be the speaker's | A public comment cites the federal "Privacy Act of 1970" (`01:21:41`); the Act is dated 1974 (recalled) | A verbatim quote must keep a speaker's own mistake, so the caption and recording must be told apart |
| Garbled crosstalk and non-speech | Side talk and photo-taking at `00:43:43` to `00:44:42` and `01:05:27` to `01:05:43`; a sung passage `01:13:47` to `01:16:14` rendered as nonsense | Not quotable |
| Formatting | All capitals, no reliable sentence breaks | Capitalization and punctuation must be rebuilt by a person, which is itself editorial |

The mix is the same as in the speech survey's committee sample (names, short words, numbers). The Board sample is longer and shows the pattern is not limited to one meeting or one body.

### Cheap signals that could narrow what a person must listen to (not tested)

- Disagreement between the city's caption and an independent machine transcript of the same audio (SmartTranscripts, which also adds punctuation and names) could flag lines more likely wrong. The two were not aligned or compared.
- A name or number from a quote can be checked against the roster, the agenda and the file number the item is about (the agenda lists file numbers), which would catch some of the errors above but not all.

## How this serves the objectives

- *Let a reporter check any pairing in minutes.* The stamp gives the place to listen; the open points are the lag (how far before the stamp to start) and whether the archive link opens at that second. The key-result timing study should include "start the video from the stamp and find the quote", with a note of how many seconds before the stamp the quote began.
- *Everything shown is current and correct.* Correctness of the speaker is the weaker link: the only dependable record of who spoke is a human who saw or heard the speaker. Correctness of the words rests on the recording.
- The non-goal against paraphrasing means a quote may show only words confirmed on the recording; caption text with the errors above is a lead, not the quote.
- What this means for the downstream hops, as evidence and not a decision: Matching trial run can find passages from the city transcript, but the speaker field would be a proposal with a stated route; Pairing site first version has no source here that credits a speaker without a person confirming; the weekly word-for-word spot check cannot be met from the transcript alone.

## Open questions

**Looked for and not found**
- Any measurement of how many words differ between caption and audio, or a per-quote rate. Looked at: the 21 April 2026 Board transcript, the speech survey's committee sample. No audio could be played.
- Whether a stamp lands at the same second in the archived video, and the size of the caption lag. Looked at: Legistar transcript text, Granicus listings and extracts. No player page was opened.
- The recording link behind the calendar's Video, Audio and Transcript cells; the static calendar HTML holds `#` only. The meeting detail page for a row was not opened.
- Whether the archived video is ever trimmed after captioning (Granicus lists a trimming tool; SFGovTV practice unknown).
- Whether the broadcast video shows member names on screen, or whether the chamber's seating or nameplates are visible enough to identify speakers.
- Minutes for the 21 April 2026 Board meeting (to test how far moved-by and vote lines confirm cue-based speakers).

**Claims not verified**
- That the Legistar transcript id equals the Granicus clip id (unverified): ids and dates rise together across the pairs listed above, but no single pair was checked in both systems.
- That the caption stamp lags the speech (my reading, from the text being live captions).
- That `>>` over-marks pauses inside a speech (my reading from context; no audio).
- That the Board listing's epoch "Date" is the only date field on the archive page (unverified; seen in search extracts).
- That Melgar is District 7 (recalled).
- The Privacy Act date (recalled).
- The 2013 appointment term being an error (my reading).

**Questions for people**
- A reporter or watchdog: for about 30 quotes from the October 2026 meetings, play the video from the stamp, note how many seconds before the stamp the quote starts, and write down every word that differs from the caption. This single exercise answers Q2's lag and Q3's rate, and the same session can time "check one quote" for the key result.
- Maintainer: is a speaker credit that a person confirms in review acceptable for the first version, or must the site be able to credit speakers without that step? (This decides whether the cue-based proposals above are enough.)
- Clerk of the Board or SFGovTV (via the maintainer, as the speech survey also asks): are the caption stamps and the archived video produced from the same timeline, and is an archive ever trimmed or replaced after the transcript is posted?
