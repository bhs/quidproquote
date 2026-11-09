# Signs that reporters find the site valuable, and which one person running it can count

**Kind of document: a survey assessment.** It weighs candidate signs; it does not choose the measure or a threshold. The key result that waits on this is written elsewhere.

**What "one person running it" means here.** The maintainer runs the site alone after launch, with no paid staff (an assumption recorded for the project, not an answer). A sign is "countable by one person" if a weekly sitting of under an hour, using only what the site records or an inbox, yields a number.

**What the first version records today** (read from `pairing_site/`):

- Every request is logged as one JSON line with request id, method, path, status and duration (`pairing_site/logs.py`). No IP, visitor identifier, referrer or user agent is kept by the app, and `start.sh` turns off uvicorn's own access line. The repository holds no proxy or server configuration; what a network layer in front of the deployed site records is not stated in it.
- Each approved card has a stable address, `/pairings/{slug}`, and a "Copy link" button (`pairing_site/templates/_card.html`). Clicks on that button, and on the outbound transcript, recording, donor page and filing links, are not recorded.
- There is no contact or correction route, no sign-up and no account. The audit log records the maintainer's review decisions, not readers' actions.

**What the maintainer has settled that bears on counting.**

- Feedback route: "I'd like the reporters to be able to send feedback to the admins, and that feedback should be in an admin queue. But they shouldn't directly send email." So the route that signs 2, 5 and 6 need is a feedback entry that lands in an admin queue, not a mailbox and not a published address. It is not built yet. A queue is countable by one person (rows by kind and by week), and the site already has a review queue for the maintainer's decisions on pairings (`pairing_site/templates/review.html`).
- Early readers: "No reporter has used it and I have none to ask." There is no named list of reporters, so signs 3 and 10 cannot be read from a list the maintainer holds. A reporter is known as a reporter only if they say so when they write in, or if a story names the site.
- Referrer: the maintainer has not said whether the referring page may be recorded. Signs 1, 4, 7, 8 and 9 are shown below with what each needs, and stay open on this point.

So today only "requests per path" can be counted, and it cannot separate reporters from anyone else.

## The candidate signs

"Count today" is what the site supports now. "Add" is the smallest addition that would make it countable; none has been built.

| # | Sign | What it shows about value | Who counts it and how | Count today | What it misses | Add |
|---|---|---|---|---|---|---|
| 1 | **A published story cites or links the site** (link, named in text, or a card shown) | The strongest: a reporter staked a published piece on it. Matches the "improved media coverage" category of five nonprofit newsrooms | One person, by hand: weekly web and news search for the site's name and `/pairings/` addresses, plus reporters reporting their own pieces. Log each with date, outlet, reporter, card | No (no referrer) | Print, broadcast, screenshots, unlinked mentions; lags the visit by days or weeks | Record the referrer of requests to `/pairings/{slug}` |
| 2 | **A reporter says a card started or shaped a story not yet published** | An earlier form of sign 1; catches use before publication | One person, from feedback entries that say so; no named readers to ask | No | Depends on reporters writing in; the feedback route is one-way unless the sender leaves a way to reply | The admin-queue feedback route, with a way for the sender to say they are a reporter |
| 3 | **The same reporter returns** (second use, within weeks) | Repeat use is the plainest sign a tool is worth the trip | One person, only for reporters who identify themselves (a second feedback entry from the same sender, or their own account of it); no invited reporters exist to give tagged links to | No (no visitor identifier) | Anonymous readers; the same reporter on two devices; nearly everything, while no reporters are known | A visit counter that does not identify people, or self-identification in the feedback entry |
| 4 | **Returning visitors overall** | Weak for reporters: the public is the main audience | One person, if a counter exists | No | Cannot tell reporters from residents | A privacy-preserving visit counter |
| 5 | **Corrections or challenges sent in** | A reporter checked a card closely enough to dispute it. Also a quality signal: a rising count may mean errors, not value | One person, from the admin queue, sorted by kind (speaker credit, quote text, money, donor page) and by sender type | No route exists | Reporters who check and say nothing; counts stay small for a long time | The feedback route on every card, with the card it concerns and a kind recorded on each entry |
| 6 | **Requests for a pairing or data the site does not have** (a named official, donor or measure) | Shows reporters want more than the cards; feeds what to build next | One person, from the same admin queue | No | Same | The same feedback route |
| 7 | **Opening cards by permalink rather than from the front page** | Reporters and sharers arrive at a card, not the list; a rough sign of citing and sharing | One person, from the request log (path) | **Yes**, as requests per card path | Cannot tell reporters from anyone | None |
| 8 | **Clicks on "Copy link"** | Someone meant to put the card into a message or a draft | One person, if recorded | No | Same | A counter on the button |
| 9 | **Clicks to the transcript, recording, donor page or filing** | Readers verifying before relying; the behaviour a reporter's use needs | One person, if recorded | No | Same | Count outbound clicks |
| 10 | **Reporter answers to a short survey** ("used in a story", "checked a source", "would come back") | Direct, but self-reported; positive answers dominate in civic-tech surveys | One person, ten or so answers, if there is anyone to ask; no reporter is known | No | Self-selection, courtesy answers; no one to send it to | A way to reach reporters at all (not yet settled), or optional questions on the feedback entry |
| 11 | **Number of distinct outlets or reporters who have used it at least once** | Breadth: is use spreading beyond one friendly reporter | One person, by a running list | Partly, by hand | Needs 1, 2, 3 or 10 to fill it; starts from zero | None beyond those |
| 12 | **Total page views** | Reach, not value; reported as a contrast | One person | Yes (requests, with bots and the maintainer's own checks mixed in) | Everything about who and why | None |

## How the signs relate

- **Outcome signs** are 1 and 2 (a story was made). **Engagement signs** are 3, 5, 6, 8 and 9 (a reporter did something with a card). **Reach signs** are 4, 7 and 12 (someone came). The sources agree on outcome signs as the ones that show value; engagement signs are the ones a lone operator can read in the first weeks, because stories take time. (My reading.)
- 5 and 6 need the same inbox; 8 and 9 need the same counter. Four additions (a feedback route into the admin queue, a referrer record, a counter on the button and outbound links, a visit counter) would make every sign except the page-view caveat in 12 countable, though 3, 4 and 10 would still not be about reporters alone. Of the four, only the feedback route is settled by the maintainer; the others hang on the unanswered question about recording where visitors came from.
- No sign says why a reporter came or whether the card was right. The site's own non-goal, never claiming or implying that donations cause what politicians say, applies to what it says about itself too: a count of stories is a count of use, not proof the pairings were right.

## What one person can and cannot count (summary)

- **Countable by one person once the feedback route exists (no referrer needed):** 2, 5, 6, and 11 for reporters who say who they are.
- **Countable by one person only if a referrer record is allowed:** 1 (as a cross-check on the web search, which needs nothing built), 7 beyond raw requests.
- **Countable only for reporters who identify themselves, since none is known by name:** 3, 10.
- **Countable but not about reporters:** 4, 7, 12.
- **Not countable until something is built:** 8, 9.

## Signs from other work that were considered and not carried over

- *Downstream legislative or institutional change* (law proposed, policy changed, an investigation opened): the other categories of the newsrooms' schemes. They are outcomes of reporting on a problem, not of a lookup site, and they take longer than the early weeks.
- *Individual or community benefit*: same reason; and the site's non-goals rule out claiming that kind of effect.
- *Officials mentioning the tool* (Digital Democracy reports lawmakers joking about its rankings in meetings): a sign of notice, not of reporters' value; not available for this site at present. Mentioned only because it was reported as an early reaction.
