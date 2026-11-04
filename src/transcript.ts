// Legistar caption transcripts: the rows, the stretches of a transcript opened by a cue that names an official
// as about to speak, and the passages of those stretches that hit a donor's subject.
//
// Nothing here decides that a remark is on the donor's subject or that a quote belongs to an official: it
// proposes (a candidate, a doubt level and why) and a person's review decides.

import { decodeEntities, escapeRegex, termRegex } from "./text.ts";
import type { Doubt, Official, Row } from "./types.ts";

export const REGION_MAX_CHARS = 4200; // about 700 words of captions after an opening cue
export const PASSAGE_MAX_ROWS = 16;
export const HIT_GAP_ROWS = 3;

/** The caption rows of a Legistar Transcript.aspx page. */
export function parseTranscriptHtml(raw: string): Row[] {
  const rows: Row[] = [];
  const rx = /(\d\d:\d\d:\d\d)\s*<\/[^>]+>\s*(?:<[^>]+>\s*)*([^<]+)/g;
  for (const m of raw.matchAll(rx)) {
    rows.push({ stamp: m[1], text: decodeEntities(m[2]).split(/\s+/).filter(Boolean).join(" ") });
  }
  return rows;
}

/** One transcript as rows and as one text, with the offset of every row. */
export class Doc {
  readonly rows: Row[];
  readonly starts: number[] = [];
  readonly text: string;

  constructor(rows: Row[]) {
    this.rows = rows;
    let pos = 0;
    for (const row of rows) {
      this.starts.push(pos);
      pos += row.text.length + 1;
    }
    this.text = rows.map((r) => r.text).join(" ");
  }

  rowIndex(pos: number): number {
    let lo = 0;
    let hi = this.starts.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (this.starts[mid] <= pos) lo = mid;
      else hi = mid - 1;
    }
    return Math.max(lo, 0);
  }

  stamp(pos: number): string {
    return this.rows[this.rowIndex(pos)].stamp;
  }
}

export interface Region {
  official: string;
  start: number;
  end: number;
  cue: string;
  cueStamp: string;
  cueRow: number;
  exact: boolean;
  district: number | null;
  bounded: boolean;
  kind: "cue" | "mayor-opening";
}

const DISTRICT_WORDS: Record<string, number> = {
  ONE: 1, TWO: 2, THREE: 3, FOUR: 4, FIVE: 5, SIX: 6, SEVEN: 7, EIGHT: 8, NINE: 9, TEN: 10, ELEVEN: 11,
};
const OPEN_BEFORE = /(?:>>|[.?!]|NEXT UP|FIRST UP|WE HAVE|\b(?:OH|OKAY|ALL RIGHT|YES|YEAH|SO),?)\s*$/;
const CLOSER_RX = /(?:>>|[.?!])\s*MADAM CLERK\b|\bPLEASE CALL THE ROLL\b|\bWITHOUT OBJECTION\b/g;
// A new speaker introducing themselves ends a member's turn even when no cue names the next speaker.
const SELF_INTRO_RX = new RegExp(
  "\\bMY NAME IS\\b|\\b(?:I'M|I AM)\\s+(?:[A-Z.',-]+\\s+){1,3}(?:[A-Z]+\\s+)?(?:GOVERNMENT AFFAIRS|" +
    "DIRECTOR|DEPUTY|MANAGER|LEGISLATIVE AIDE|ANALYST|COUNSEL|ATTORNEY|SENIOR|COMMISSIONER|EXECUTIVE)\\b",
  "g",
);
const MAYOR_OPEN_RX = /ANY OPENING\s+REMARKS/;
const AMBIGUOUS_PAIR = ["Connie Chan", "Chyanne Chen"];

interface Cue {
  kind: "rollcall" | "opener" | "mention";
  official: string;
  exact: boolean;
  start: number;
  end: number;
  text: string;
  district: number | null;
}

function tokenTable(roster: Official[]): Map<string, { official: string; exact: boolean }> {
  const out = new Map<string, { official: string; exact: boolean }>();
  for (const o of roster) {
    for (const t of o.exact) out.set(t, { official: o.name, exact: true });
    for (const t of o.garbled) out.set(t, { official: o.name, exact: false });
  }
  return out;
}

function matches(rx: RegExp, text: string): RegExpMatchArray[] {
  return [...text.matchAll(new RegExp(rx.source, rx.flags.includes("g") ? rx.flags : rx.flags + "g"))];
}

/** The stretches of a transcript opened by a cue that names an official as about to speak.
 *
 * A cue opens a turn when a member's title and name follow a '>>', a sentence end, 'NEXT UP' or 'WE HAVE' and
 * are not a roll-call answer. A region runs to the next opening cue, roll call or clerk call, or 700 words.
 * The Mayor's opening remarks are one region, from the presiding officer's question to 'THANK YOU, MAYOR'. */
export function findRegions(doc: Doc, roster: Official[]): Region[] {
  const tokens = tokenTable(roster);
  if (!tokens.size) return [];
  const names = [...tokens.keys()].sort((a, b) => b.length - a.length).map(escapeRegex).join("|");
  const cueRx = new RegExp(
    `(?:DISTRICT\\s+(?<dist>\\w+)\\s+)?(?<title>(?:VICE[\\s-]+)?CHAIR|SUPERVISOR|PRESIDENT|MEMBER)\\s+(?<name>${names})\\b`,
    "g",
  );
  const rollAfter = new RegExp(`^[\\s,.]*(?:(?:${names})[\\s,.]*)?(?:I|I'M|EYES|EYE|AYE|AYES|NO|NOS|PRESENT|YES|HI)\\b`);
  const cues: Cue[] = [];
  for (const m of doc.text.matchAll(cueRx)) {
    const start = m.index ?? 0;
    const end = start + m[0].length;
    const who = tokens.get(m.groups!.name)!;
    const before = doc.text.slice(Math.max(0, start - 24), start);
    const after = doc.text.slice(end, end + 44);
    const title = m.groups!.title;
    let kind: Cue["kind"];
    if (rollAfter.test(after)) kind = "rollcall";
    else if ((title.endsWith("SUPERVISOR") || title.endsWith("CHAIR")) && OPEN_BEFORE.test(before)) kind = "opener";
    else kind = "mention";
    const district = DISTRICT_WORDS[(m.groups!.dist ?? "").toUpperCase()] ?? null;
    cues.push({ kind, official: who.official, exact: who.exact, start, end, text: m[0], district });
  }
  const stops = [
    ...cues.filter((c) => c.kind === "opener" || c.kind === "rollcall").map((c) => c.start),
    ...matches(CLOSER_RX, doc.text).map((m) => m.index ?? 0),
    ...matches(SELF_INTRO_RX, doc.text).map((m) => m.index ?? 0),
  ].sort((a, b) => a - b);
  const regions: Region[] = [];
  for (const c of cues) {
    if (c.kind !== "opener") continue;
    const next = stops.find((s) => s >= c.end);
    const limit = c.end + REGION_MAX_CHARS;
    const end = next !== undefined ? Math.min(next, limit) : Math.min(doc.text.length, limit);
    regions.push({
      official: c.official, start: c.end, end, cue: c.text, cueStamp: doc.stamp(c.start), cueRow: doc.rowIndex(c.start),
      exact: c.exact, district: c.district, bounded: next !== undefined && next < limit, kind: "cue",
    });
  }
  const mayor = roster.find((o) => o.office === "Mayor");
  const open = MAYOR_OPEN_RX.exec(doc.text);
  if (mayor && open && doc.text.slice(Math.max(0, open.index - 500), open.index).includes("MAYOR")) {
    const close = /THANK YOU,?\s+(?:MR\.?\s+)?MAYOR(?:\s+[A-Z]+)?/g;
    close.lastIndex = open.index + open[0].length;
    const found = close.exec(doc.text);
    if (found) {
      regions.push({
        official: mayor.name, start: open.index + open[0].length, end: found.index,
        cue: "the presiding officer asks the Mayor for opening remarks", cueStamp: doc.stamp(open.index),
        cueRow: doc.rowIndex(open.index), exact: true, district: null, bounded: true, kind: "mayor-opening",
      });
    }
  }
  return regions.sort((a, b) => a.start - b.start);
}

/** [doubt, reasons] for a passage starting at offset `ps` inside a region.
 *
 * low: the opening cue spells the surname as the captions' own roster does, the region is closed by another
 * cue, no further '>>' mark lies between the cue and the passage, and the passage starts within 400 words.
 * medium: a garbled spelling, an unclosed region, a few '>>' marks or up to 700 words. high: otherwise. Chan and
 * Chen are never better than medium without a district cue. The Mayor's opening remarks are low (named by the
 * clerk's introduction and thanked by name when they end). */
export function creditTier(doc: Doc, region: Region, ps: number): [Doubt, string[]] {
  const gap = doc.text.slice(region.start, ps);
  const words = gap.split(/\s+/).filter(Boolean).length;
  const arrows = (gap.match(/>>/g) ?? []).length;
  if (region.kind === "mayor-opening") {
    return ["low", [`inside the Mayor's opening remarks, which the presiding officer's question opens and 'THANK YOU, MAYOR' closes (${region.cueStamp})`]];
  }
  const why = [`${words} words after the cue '${region.cue}' (${region.cueStamp})`];
  if (arrows) why.push(`${arrows} '>>' mark(s) between the cue and the passage`);
  if (!region.exact) why.push("the caption garbles the surname");
  if (!region.bounded) why.push("no cue closes the turn");
  let tier: Doubt;
  if (region.exact && region.bounded && arrows <= 1 && words <= 400) tier = "low";
  else if (arrows <= 4 && words <= 700) tier = "medium";
  else tier = "high";
  if (tier === "low" && AMBIGUOUS_PAIR.includes(region.official) && !region.district) {
    tier = "medium";
    why.push("Chan and Chen differ by one letter and no district cue is given");
  }
  return [tier, why];
}

export interface Subject {
  /** Measure names ("Prop H", "Proposition H"): a hit is a specific one. */
  anchor: string[];
  /** The donor's phrases. */
  topic: string[];
}

export interface Passage {
  start: number;
  end: number;
  text: string;
  firstStamp: string;
  lastStamp: string;
  firstRow: number;
  lastRow: number;
  anchorHits: string[];
  topicHits: string[];
  tier: "specific" | "topic";
}

/** Passages of a credited region that hit the subject's terms. Rows holding a hit are grouped when at most
 * three rows apart; a passage runs from the row before the first hit to the row after the last, never past the
 * region or 16 rows. */
export function candidatePassages(doc: Doc, region: Region, subject: Subject): Passage[] {
  const anchorRx = termRegex(subject.anchor);
  const topicRx = termRegex(subject.topic);
  if (!anchorRx && !topicRx) return [];
  const r0 = doc.rowIndex(region.start);
  const r1 = doc.rowIndex(Math.max(region.end - 1, region.start));
  const hits: { row: number; anchor: string[]; topic: string[] }[] = [];
  for (let i = r0; i <= r1; i++) {
    const lo = Math.max(doc.starts[i], region.start);
    const hi = Math.min(doc.starts[i] + doc.rows[i].text.length, region.end);
    const seg = doc.text.slice(lo, hi);
    const anchor = anchorRx ? [...new Set([...seg.matchAll(anchorRx)].map((m) => m[0].toUpperCase()))].sort() : [];
    const topic = topicRx ? [...new Set([...seg.matchAll(topicRx)].map((m) => m[0].toUpperCase()))].sort() : [];
    if (anchor.length || topic.length) hits.push({ row: i, anchor, topic });
  }
  const groups: (typeof hits)[] = [];
  let current: typeof hits = [];
  for (const hit of hits) {
    if (current.length && hit.row - current[current.length - 1].row > HIT_GAP_ROWS) {
      groups.push(current);
      current = [];
    }
    current.push(hit);
  }
  if (current.length) groups.push(current);
  return groups.map((g) => {
    const i0 = Math.max(g[0].row - 1, r0);
    const i1 = Math.min(g[g.length - 1].row + 1, r1, i0 + PASSAGE_MAX_ROWS - 1);
    const start = Math.max(doc.starts[i0], region.start);
    const end = Math.min(doc.starts[i1] + doc.rows[i1].text.length, region.end);
    let text = doc.text.slice(start, end).trim();
    text = text.replace(/^[.>, ]+/, "");
    const anchor = [...new Set(g.flatMap((h) => h.anchor))].sort();
    const topic = [...new Set(g.flatMap((h) => h.topic))].sort();
    return {
      start, end, text, firstStamp: doc.stamp(start), lastStamp: doc.stamp(Math.max(end - 1, start)),
      firstRow: doc.rowIndex(start), lastRow: doc.rowIndex(Math.max(end - 1, start)), anchorHits: anchor,
      topicHits: topic, tier: anchor.length ? "specific" : "topic",
    };
  });
}

export interface Quote {
  text: string;
  firstStamp: string;
  lastStamp: string;
}

/** The words of the caption rows from stamp `from` to `to`, exactly as published.
 *
 * `beginAt` / `endAt` cut the first and last row at a phrase that must occur in them. A leading '>>' (the
 * captions' speaker-change mark) is dropped. Throws when anything asked for is not there. */
export function extractQuote(rows: Row[], from: string, to: string, beginAt = "", endAt = ""): Quote {
  const selected = rows.filter((r) => r.stamp >= from && r.stamp <= to);
  if (!selected.length) throw new Error(`no caption rows between ${from} and ${to}`);
  let joined = "";
  const offsets: [number, string][] = [];
  for (const r of selected) {
    offsets.push([joined.length, r.stamp]);
    joined += r.text + " ";
  }
  let b = 0;
  let e = joined.trimEnd().length;
  if (beginAt) {
    b = joined.indexOf(beginAt);
    if (b < 0) throw new Error(`"begin at" phrase not found in those rows: ${beginAt}`);
  }
  if (endAt) {
    const i = joined.indexOf(endAt, b);
    if (i < 0) throw new Error(`"end at" phrase not found in those rows: ${endAt}`);
    e = i + endAt.length;
  }
  while (b < e && (joined[b] === ">" || joined[b] === " ")) b++;
  const text = joined.slice(b, e).trim();
  if (!text) throw new Error("the quote is empty");
  const first = [...offsets].reverse().find(([off]) => off <= b)![1];
  const last = [...offsets].reverse().find(([off]) => off <= Math.max(e - 1, 0))![1];
  return { text, firstStamp: first, lastStamp: last };
}

export function isVerbatim(rows: Row[], text: string): boolean {
  return rows.map((r) => r.text).join(" ").includes(text);
}

/** The rows at the given stamps; throws for a stamp the transcript does not hold. */
export function cueRows(rows: Row[], stamps: string[]): Row[] {
  const out: Row[] = [];
  for (const stamp of stamps) {
    const hits = rows.filter((r) => r.stamp === stamp);
    if (!hits.length) throw new Error(`stamp ${stamp} is not in the transcript`);
    out.push(...hits);
  }
  return out;
}
