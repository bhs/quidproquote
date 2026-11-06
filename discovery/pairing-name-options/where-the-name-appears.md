# Where the name appears: every place the site and its documents say what a card is, and whether each place needs the same word

**Kind of hop: a survey** of this repository's own wording (the pairing site's templates, code and the earlier findings), written as findings. It reads the code as it is and changes nothing. Summary: `findings.md`; candidate words: `name-options.md`.

## Three words are in use for what is arguably two things

| Word | Used for | Where |
|---|---|---|
| **Pairing** | A record with a status (pending, approved, rejected), a public page, a database table, and the whole site's name | brand "Pairings" and the title tag, the page heading, `/pairings/<slug>`, table `pairings`, the review screen's log column "Pairing", the permalink page's notice "This pairing is pending", the worker status counters (`pairings_pending` and the like), 83 occurrences across templates and code |
| **Card** | The published display of a pairing | nav link "Cards", "N cards shown", "No card matches", the footer ("Each card is a reading, not a finding"), the review lede ("publishes the card"), 125 occurrences |
| **Pair** | A candidate that has passed the shortlist and the AI filter and is awaiting review, or was dropped | the review lede ("Each pair below"), "Dropped pairs", "Why dropped" |

Counts are of case-insensitive matches in `pairing_site/templates`, `pairing_site/*.py` and `pairing_site/static` (pairing 83, card 125, pair or pairs 46). They show weight, not the number of places.

So the same object is a **pair** while it is a candidate, a **pairing** as a record, and a **card** as a page. That is a defensible internal split (the reviewer needs to tell stages apart). The question for the public places is whether a first-time reader needs to meet more than one of them.

## The places, and what each needs

| # | Place | Words now | What this place has to do | Needs the unit's name? | Needs the same word as the others? |
|---|---|---|---|---|---|
| 1 | Browser title and tab | "Pairings - San Francisco officials, donors' priorities and money" (`base.html`) | Say what the site is before the page loads, in a search result | Yes, with the three parts spelled out | Yes: this is the first meeting with the word |
| 2 | Site brand in the header | "Pairings" | Be a name a person can say and remember | The brand may be a different word from the unit | No: the brand is a site name |
| 3 | Navigation | "Cards", and for the maintainer "Review queue", "Dropped pairs", "Add a priority", "Worker status" | Say where each link goes | The public link names a display ("Cards") | Not necessarily: a link names what is behind it |
| 4 | Page heading and lede (`index.html`) | h1 "Pairings"; the lede says each card puts three things side by side and "a card says what is shown, not why" | Say what the card is and what it is not | Yes | Yes: here the name is defined |
| 5 | Filters and counts | "Official", "Donor", "N cards shown", "No pairing has been approved yet" | Narrow the list | The count and empty-state use a unit word | Yes: a reader should not see "cards" and then "pairing" in one paragraph |
| 6 | Card title | "{Official} × {Donor}" (`pairing_cards.py`, `_card.html`) | Say who and who | No unit word; the "×" is a symbol that can read as "versus", "meets" or multiplication | A symbol or word for the relation between the two names is its own choice |
| 7 | Left zone heading | "Money in, then the donor's priority" | Label two things | No | No: slot 2 and 3 words (`name-options.md`), and "then" implies an order |
| 8 | Middle zone | "The official", the name, the role, "San Francisco official, as the city's roster has them" | Say who | No | No |
| 9 | Right zone heading | "The official's exact words" | Label the quote | No | No: slot 4 |
| 10 | Strip | "SPEAKER-CREDIT DOUBT: LOW", "Reading, not a finding.", "In common ... Where they differ ... No cause is claimed." | Say what the card is not | The strip says what the card is not, so it needs the unit word in the same place as the lede | Yes: the strip and the footer say the same thing and should use the same unit word |
| 11 | Sources row | "Sources: transcript, donor page, filing ids, money retrieved" | Give the checks | No | No |
| 12 | Footer on every page | "Each card is a reading, not a finding. It shows ..." | Repeat the guard on every page | Yes | Yes: same sentence as the strip |
| 13 | Permalink page and Copy link | "All cards", "Copy link", `/pairings/<slug>` | A shareable address | The path has the word, and reporters will cite it | A changed word needs a redirect from `/pairings/` (design point for the redesign) |
| 14 | Review queue (maintainer) | "Review queue", "Each pair below passed the shortlist and the AI filter", "Approve and publish", "I played the recording at {stamp} and the words match" | Make a decision on a candidate | Needs to say what is being approved: a candidate for a published card | No: a stage word ("pair") separates it from the published card |
| 15 | Log and decided list | "Pairing" column, "{status}: {Official} × {Donor}" | Audit | A record word | No |
| 16 | Dropped pairs | "Dropped pairs", "Why dropped" | Show what was filtered and why | A candidate word | No |
| 17 | Add a priority form | "Add a donor's priority", "Donor statements on file" | Enter the donor's words | Uses slot 3 | Yes with slot 3: whatever the donor's side is called on the card should be called the same here |
| 18 | Worker status JSON | "pairings_pending" etc. | Machine-readable status | An internal key | No: internal keys need not follow a rename |
| 19 | Earlier findings, `pairings.md`, `pairing-cards.md` | "pairing", "card" | Documentation | Internal | No |

## What this says about the charter question

- **Six of the places do not need the unit's name at all** (6 partly, 7, 8, 9, 11, 18): they label a part. Choosing the unit's name does not decide them; slots 2 to 5 in `name-options.md` do.
- **Five public places should use one word** (1, 4, 5, 10, 12): the title, the lede, the count and empty-state, the strip and the footer. Together these are where a first-time reader first meets the word and where its explanation lives.
- **Three places use a different word for a good reason** (14, 15, 16): the maintainer's stage words (candidate or "pair", then published). They need to say what a decision on a candidate becomes (the public word), not to match it.
- **Two places cost something to rename** (13, and 18 as an internal key): the public path `/pairings/` is a shareable address that reporters will cite, and database and counter names are internal. Neither has to follow a rename; the path would need a redirect.
- **The strip and the footer say the same sentence in two places.** If the guard sentence changes (`name-options.md`, slot 5), both change together.

## What the reviewer screen shows

The review queue reuses the public card macro with `queue=True` and adds an approve form with a required recording check. It therefore shows the **public** wording in the card and the **stage** wording around it. The reviewer reads the strip's "Reading, not a finding" as a statement about the card, not about their own decision. Its own heading, "Review queue", names the activity, not the object, and is not affected by the unit's name. Where it matters: "Each pair below ... Approving publishes the card" uses two words for one thing in one sentence; if the unit's name changes, that sentence is the only reviewer-facing place that must change with it.

## Not looked at

- The site's mobile layout and any text in images; there are none in the templates.
- Any wording outside this repository (social-media text, press materials); none exists in the repository.
