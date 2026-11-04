// Fills the data directory with the five pairings shown by 'Pairings end to end', through the same code the
// maintainer uses: the fixture transcripts, money snapshot and donor statements are loaded; the funder-first rules
// propose candidates over them; and each of the five reviews (the quote bounds, speaker credit and readings a
// person made) is approved as a pairing, which builds its card and regenerates the static pages. The passages the
// rules propose that no review took are left in the queue.
//
//   npm run seed
//
// It is run by hand (or by a demo's setup), never at startup.

import { readFile } from "node:fs/promises";
import { loadConfig } from "./config.ts";
import { manualCandidate, stampsOverlap } from "./candidates.ts";
import { addCandidates } from "./refresh.ts";
import { fixturePath, loadFamilies, loadRoster } from "./reference.ts";
import { approveCandidate } from "./review.ts";
import { publishSite } from "./site.ts";
import { Store, parseTsv } from "./store.ts";
import type { Context } from "./review.ts";
import type { Meeting, MoneySnapshot, Priority, ReviewInput } from "./types.ts";

export interface FixtureReview extends ReviewInput {
  id: number;
  official: string;
  family: string;
  meetingId: string;
}

async function fixture<T>(name: string): Promise<T> {
  return JSON.parse(await readFile(fixturePath(name), "utf-8")) as T;
}

const seconds = (stamp: string): number => {
  const [h, m, s] = stamp.split(":").map(Number);
  return h * 3600 + m * 60 + s;
};

export interface SeedSummary {
  meetings: number;
  priorities: number;
  proposed: number;
  published: number;
  handFound: number;
  pending: number;
}

export async function seedFixtures(ctx: Context): Promise<SeedSummary> {
  const { store } = ctx;
  const now = (ctx.now ?? (() => new Date()))().toISOString();
  const meetings = await fixture<Meeting[]>("meetings.json");
  for (const m of meetings) await store.saveTranscript(m.id, parseTsv(await readFile(fixturePath(`transcripts/${m.id}.tsv`), "utf-8")));
  await store.meetings.putMany(meetings);
  await store.saveSnapshot(await fixture<MoneySnapshot>("money.json"));
  const priorities = await fixture<Priority[]>("priorities.json");
  await store.priorities.putMany(priorities);

  const proposed = await addCandidates(ctx, now);
  const reviews = (await fixture<FixtureReview[]>("reviews.json")).sort((a, b) => a.id - b.id);
  let published = 0;
  let handFound = 0;
  for (const r of reviews) {
    if ((await store.pairings.all()).some((p) => p.slug === r.slug)) continue;
    const official = ctx.roster.find((o) => o.name === r.official)!;
    const family = ctx.families.find((f) => f.key === r.family)!;
    const overlapping = (await store.candidates.all())
      .filter((c) => c.status === "pending" && c.meetingId === r.meetingId && c.official === r.official && c.familyKey === r.family
        && stampsOverlap(c.firstStamp, c.lastStamp, r.quote.from, r.quote.to))
      .sort((a, b) => Math.abs(seconds(a.firstStamp) - seconds(r.quote.from)) - Math.abs(seconds(b.firstStamp) - seconds(r.quote.from)));
    let candidate = overlapping[0];
    if (!candidate) {
      const rows = (await store.transcript(r.meetingId))!;
      candidate = manualCandidate({
        meeting: meetings.find((m) => m.id === r.meetingId)!, rows, official, family, from: r.quote.from, to: r.quote.to,
        priorityIds: r.priorityIds, now,
        why: "found by hand: the captions garble the speaker's name, so no roster cue opened this turn",
      });
      await store.candidates.put(candidate);
      handFound++;
    }
    await approveCandidate(ctx, candidate.id, {
      slug: r.slug, subject: r.subject, quote: r.quote, speaker: r.speaker, priorityIds: r.priorityIds,
      highlight: r.highlight, overlap: r.overlap, stance: r.stance, moneyNote: r.moneyNote,
    });
    published++;
  }
  await store.logFetch({ source: "seed", what: "fixtures loaded (transcripts, money snapshot, donor statements)", ok: true, detail: `${published} pairings published` });
  await publishSite(store);
  const pending = (await store.candidates.all()).filter((c) => c.status === "pending").length;
  return { meetings: meetings.length, priorities: priorities.length, proposed, published, handFound, pending };
}

if (import.meta.main) {
  const config = loadConfig();
  const ctx: Context = { store: new Store(config.dataDir), roster: await loadRoster(), families: await loadFamilies() };
  const s = await seedFixtures(ctx);
  console.log(
    `${s.meetings} meeting transcripts, ${s.priorities} donor priorities and the money snapshot loaded; ` +
      `the rules proposed ${s.proposed} passages; ${s.published} pairings published (${s.handFound} found by hand); ` +
      `${s.pending} passages waiting in the review queue`,
  );
}
