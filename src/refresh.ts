// The daily fetch: new Board and committee transcripts from Legistar, the campaign finance rows from DataSF, and
// then candidates from the funder-first rules. Every source read, and every failure, is written to the fetch
// log. A failed read leaves what was on disk as it was; it is never replaced by an empty answer.

import { DataSf, fetchMoneySnapshot } from "./datasf.ts";
import type { Fetcher } from "./fetcher.ts";
import { generateCandidates } from "./candidates.ts";
import { discoverMeetings, fetchTranscript, transcriptUrl } from "./legistar.ts";
import { today } from "./text.ts";
import type { Store } from "./store.ts";
import type { Family, Official, Row } from "./types.ts";

export interface RefreshDeps {
  store: Store;
  fetcher: Fetcher;
  datasf: DataSf;
  roster: Official[];
  families: Family[];
  now?: () => Date;
  /** How many transcripts one run fetches: each is a large page and is fetched slowly. */
  maxNewTranscripts?: number;
}

export interface RefreshSummary {
  startedAt: string;
  meetingsSeen: number;
  transcriptsFetched: number;
  moneyRefreshed: boolean;
  candidatesAdded: number;
  errors: string[];
}

export async function runRefresh(deps: RefreshDeps): Promise<RefreshSummary> {
  const { store } = deps;
  const now = deps.now ?? (() => new Date());
  const summary: RefreshSummary = {
    startedAt: now().toISOString(), meetingsSeen: 0, transcriptsFetched: 0, moneyRefreshed: false, candidatesAdded: 0, errors: [],
  };
  const fail = async (source: "legistar" | "granicus" | "datasf", what: string, err: unknown) => {
    const detail = `${(err as Error).name}: ${(err as Error).message}`;
    summary.errors.push(`${what}: ${detail}`);
    await store.logFetch({ source, what, ok: false, detail });
  };

  try {
    const found = await discoverMeetings(deps.fetcher, now().getUTCFullYear());
    summary.meetingsSeen = found.rows.length;
    const source = found.route === "Legistar calendar" ? "legistar" : "granicus";
    await store.logFetch({ source, what: `meeting list for ${now().getUTCFullYear()}`, ok: true, detail: `${found.rows.length} meetings with a transcript; ${found.notes.join("; ") || "no notes"}` });
    const known = new Set((await store.meetings.all()).map((m) => m.id));
    const fresh = found.rows.filter((r) => r.transcriptId && !known.has(r.transcriptId)).slice(0, deps.maxNewTranscripts ?? 4);
    for (const r of fresh) {
      const id = r.transcriptId!;
      try {
        const rows = await fetchTranscript(deps.fetcher, id);
        await store.saveTranscript(id, rows);
        await store.meetings.put({ id, body: r.body, date: r.date, url: transcriptUrl(id), retrieved: today(now()), rows: rows.length });
        summary.transcriptsFetched++;
        await store.logFetch({ source: "legistar", what: `transcript ${id} (${r.body}, ${r.date})`, ok: true, detail: `${rows.length} caption rows` });
      } catch (err) {
        await fail("legistar", `transcript ${id} (${r.body}, ${r.date})`, err);
      }
    }
  } catch (err) {
    await fail("legistar", "meeting list", err);
  }

  try {
    const snapshot = await fetchMoneySnapshot(deps.datasf, deps.roster, deps.families, async (what, ok, detail) => {
      await store.logFetch({ source: "datasf", what, ok, detail });
    });
    await store.saveSnapshot(snapshot);
    summary.moneyRefreshed = true;
  } catch (err) {
    await fail("datasf", "campaign finance snapshot (the earlier one is kept)", err);
  }

  try {
    summary.candidatesAdded = await addCandidates(deps, now().toISOString());
  } catch (err) {
    summary.errors.push(`candidates: ${(err as Error).message}`);
    await store.logFetch({ source: "refresh", what: "candidates", ok: false, detail: (err as Error).message });
  }

  await store.logFetch({
    source: "refresh", what: "daily refresh", ok: summary.errors.length === 0,
    detail: `${summary.meetingsSeen} meetings listed, ${summary.transcriptsFetched} transcripts fetched, ` +
      `money ${summary.moneyRefreshed ? "refreshed" : "not refreshed"}, ${summary.candidatesAdded} candidates added, ${summary.errors.length} errors`,
  });
  return summary;
}

/** Candidates from the rules over every transcript on disk; those already known (in any state) are kept as they are. */
export async function addCandidates(deps: Pick<RefreshDeps, "store" | "roster" | "families">, now: string): Promise<number> {
  const { store } = deps;
  const snapshot = await store.snapshot();
  const priorities = await store.priorities.all();
  if (!snapshot || !priorities.length) return 0;
  const meetings = await store.meetings.all();
  const transcripts = new Map<string, Row[]>();
  for (const m of meetings) {
    const rows = await store.transcript(m.id);
    if (rows) transcripts.set(m.id, rows);
  }
  const made = generateCandidates({ snapshot, families: deps.families, roster: deps.roster, priorities, meetings, transcripts, now });
  return store.candidates.update((items) => {
    const have = new Set(items.map((c) => c.id));
    const fresh = made.filter((c) => !have.has(c.id));
    return { items: [...items, ...fresh], result: fresh.length };
  });
}
