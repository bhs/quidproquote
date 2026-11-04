// Candidates, from funder-first rules and no model: start from a donor family that gave Schedule A money to a
// committee tied to an official; take each of the family's stated priorities; read the measure names and the
// phrases in them; and look for those names and phrases inside the stretches of the transcripts opened by a cue
// that names the official as about to speak. A hit is only a candidate: a person decides whether the passage
// is on the donor's subject and whether the speaker is the official.

import { isFunded, pairMoney } from "./money.ts";
import { measureTerms } from "./priorities.ts";
import { slugify } from "./text.ts";
import { Doc, candidatePassages, creditTier, extractQuote, findRegions } from "./transcript.ts";
import type { Region } from "./transcript.ts";
import type { Candidate, CaptionLine, Family, Meeting, MoneySnapshot, Official, Priority, Row } from "./types.ts";

export const CONTEXT_ROWS = 3;

export function candidateId(meetingId: string, firstStamp: string, official: string, family: string): string {
  return `${meetingId}-${firstStamp.replace(/:/g, "")}-${slugify(official)}-${family}`;
}

export function roleOf(o: Official): string {
  return o.office + (o.district ? `, District ${o.district}` : "");
}

/** The caption rows of a passage with a few rows of context either side, each marked. */
export function captionLines(rows: Row[], firstRow: number, lastRow: number, context = CONTEXT_ROWS): CaptionLine[] {
  const lo = Math.max(firstRow - context, 0);
  const hi = Math.min(lastRow + context, rows.length - 1);
  const out: CaptionLine[] = [];
  for (let i = lo; i <= hi; i++) {
    out.push({ stamp: rows[i].stamp, text: rows[i].text, kind: i < firstRow ? "before" : i > lastRow ? "after" : "passage" });
  }
  return out;
}

export interface GenerateInput {
  snapshot: MoneySnapshot;
  families: Family[];
  roster: Official[];
  priorities: Priority[];
  meetings: Meeting[];
  transcripts: Map<string, Row[]>;
  now: string;
}

export function generateCandidates(input: GenerateInput): Candidate[] {
  const docs = input.meetings.flatMap((meeting) => {
    const rows = input.transcripts.get(meeting.id);
    if (!rows) return [];
    const doc = new Doc(rows);
    return [{ meeting, rows, doc, regions: findRegions(doc, input.roster) }];
  });
  const out = new Map<string, Candidate>();
  for (const family of input.families) {
    const priorities = input.priorities.filter((p) => p.family === family.key);
    if (!priorities.length) continue;
    for (const official of input.roster) {
      if (!isFunded(pairMoney(input.snapshot, input.families, official.name, family.key))) continue;
      for (const priority of priorities) {
        const subject = { anchor: measureTerms(priority.measures), topic: priority.phrases };
        for (const { meeting, rows, doc, regions } of docs) {
          for (const region of regions.filter((r: Region) => r.official === official.name)) {
            for (const p of candidatePassages(doc, region, subject)) {
              const id = candidateId(meeting.id, p.firstStamp, official.name, family.key);
              const have = out.get(id);
              if (have) {
                have.priorityIds = [...new Set([...have.priorityIds, priority.id])];
                have.anchorHits = [...new Set([...have.anchorHits, ...p.anchorHits])].sort();
                have.topicHits = [...new Set([...have.topicHits, ...p.topicHits])].sort();
                continue;
              }
              const [doubt, why] = creditTier(doc, region, p.start);
              const cueFrom = Math.max(region.cueRow - 1, 0);
              out.set(id, {
                id, status: "pending", origin: "rules", meetingId: meeting.id, body: meeting.body, date: meeting.date,
                official: official.name, officialRole: roleOf(official), familyKey: family.key, familyName: family.name,
                priorityIds: [priority.id], anchorHits: p.anchorHits, topicHits: p.topicHits, firstStamp: p.firstStamp,
                lastStamp: p.lastStamp, text: p.text, doubt, doubtWhy: why, cue: region.cue, cueStamp: region.cueStamp,
                cueLines: rows.slice(cueFrom, Math.min(region.cueRow + 2, rows.length)),
                lines: captionLines(rows, p.firstRow, p.lastRow), createdAt: input.now,
              });
            }
          }
        }
      }
    }
  }
  return [...out.values()].sort((a, b) => a.date.localeCompare(b.date) || a.firstStamp.localeCompare(b.firstStamp));
}

/** True when two stamp ranges of the same transcript share any caption time. */
export function stampsOverlap(aFrom: string, aTo: string, bFrom: string, bTo: string): boolean {
  return aFrom <= bTo && bFrom <= aTo;
}

/** A candidate the maintainer found by hand (no cue in the captions names the speaker in a way the roster
 * reads), from the stamps of the passage. Its doubt starts at high. */
export function manualCandidate(args: {
  meeting: Meeting; rows: Row[]; official: Official; family: Family; from: string; to: string;
  priorityIds: string[]; why: string; now: string;
}): Candidate {
  const quote = extractQuote(args.rows, args.from, args.to);
  const firstRow = args.rows.findIndex((r) => r.stamp >= args.from);
  let lastRow = firstRow;
  args.rows.forEach((r, i) => {
    if (r.stamp <= args.to) lastRow = i;
  });
  return {
    id: candidateId(args.meeting.id, quote.firstStamp, args.official.name, args.family.key), status: "pending",
    origin: "maintainer", meetingId: args.meeting.id, body: args.meeting.body, date: args.meeting.date,
    official: args.official.name, officialRole: roleOf(args.official), familyKey: args.family.key, familyName: args.family.name,
    priorityIds: args.priorityIds, anchorHits: [], topicHits: [], firstStamp: quote.firstStamp, lastStamp: quote.lastStamp,
    text: quote.text, doubt: "high", doubtWhy: [args.why], cue: "", cueStamp: "", cueLines: [],
    lines: captionLines(args.rows, firstRow, lastRow), createdAt: args.now,
  };
}
