# Pairing site (Node and TypeScript)

A small site of **pairing cards** for San Francisco: an official's exact words from the city's Legistar caption
transcript, a donor's own stated priority, and the Schedule A money the donor gave through committees tied to the
official. A card shows two things side by side; it never says why anyone said or gave anything.

## How it works

- `src/transcript.ts`, `src/candidates.ts`: roster-cue speaker proposal and the funder-first candidate rules. A donor
  that gave Schedule A money to a committee tied to an official, a measure name or phrase from the donor's own words,
  and a stretch of a transcript where a cue names the official as about to speak give a *candidate*. No model is used.
- `src/money.ts`: the money-by-committee join. Totals are per committee, never summed; 24-hour repeats are listed and
  not counted; form 496 outside spending is kept apart.
- `src/legistar.ts`, `src/datasf.ts`, `src/fetcher.ts`: fetching, slowly (a pause between requests), with a user agent
  carrying `FETCH_CONTACT_EMAIL`. `src/refresh.ts` is the daily job and `src/scheduler.ts` runs it in-process.
- `src/store.ts`: records (candidates, pairings, priorities, reviews, fetch log) are JSON files under `DATA_DIR`,
  written atomically. There is no database engine.
- `src/review.ts`, `src/site.ts`, `src/render.ts`: approving or unpublishing a pairing rebuilds the static HTML for the
  card list and each card's page under `DATA_DIR/site`; an unpublished address serves a plain notice (410).
- `src/app.ts`, `src/pages.ts`: the HTTP server. The maintainer signs in with `ADMIN_TOKEN` (a signed cookie) to see
  the review queue (exact caption lines with context) and the priority form, which refuses a save missing the donor's
  words, source, URL or date.

## Settings

`DATA_DIR`, `ADMIN_TOKEN`, `FETCH_CONTACT_EMAIL` are required; `PORT` defaults to 8080; `DATASF_APP_TOKEN` is optional
(it only lifts DataSF's rate limit); `REFRESH_START_DELAY_SECONDS` (default 600) is how long after a start the first
due fetch may run.

## Commands

    npm start        # serve (node runs the TypeScript directly)
    npm run seed     # load the five shown pairings from fixtures/ through the same review code
    npm test         # node --test
    npm run typecheck

`fixtures/` holds the five pairings that 'Pairings end to end' showed (transcripts, money snapshot, donor statements and
the reviews a person made); `scripts/build_fixtures.py` rebuilds them and `reference/` from `discovery/official-funding-map/`.
