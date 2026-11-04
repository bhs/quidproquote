// The review form: the values it shows (prefilled from the candidate), how a submission is read back into a
// ReviewInput, and the highlight words suggested from the candidate's hits.

import { hasTerm, squash } from "./text.ts";
import type { Candidate, Doubt, OutsideSource, Priority, ReviewInput } from "./types.ts";

export interface ApproveValues {
  subject: string;
  slug: string;
  from: string;
  to: string;
  beginAt: string;
  endAt: string;
  cueStamps: string;
  support: string;
  doubt: string;
  doubtReason: string;
  priorityIds: string[];
  highlight: string;
  overlap: string;
  stance: string;
  moneyNote: string;
  outside: string;
}

/** Hits the candidate's rules found that are literally also in the donor's words: a start for the highlight. */
export function suggestHighlights(candidate: Candidate, priorities: Priority[]): string[] {
  const donor = priorities.filter((p) => candidate.priorityIds.includes(p.id)).map((p) => `${p.section} ${p.text}`);
  return candidate.topicHits.map((h) => h.toLowerCase()).filter((h) => donor.some((t) => hasTerm(t, h)));
}

export function defaultsFor(candidate: Candidate, priorities: Priority[]): ApproveValues {
  return {
    subject: "", slug: "", from: candidate.firstStamp, to: candidate.lastStamp, beginAt: "", endAt: "",
    cueStamps: candidate.cueLines.map((r) => r.stamp).join(", "), support: "", doubt: candidate.doubt,
    doubtReason: candidate.doubtWhy.join("; "), priorityIds: candidate.priorityIds,
    highlight: suggestHighlights(candidate, priorities).join(", "), overlap: "", stance: "", moneyNote: "", outside: "",
  };
}

const one = (form: URLSearchParams, name: string): string => form.get(name) ?? "";

export function valuesFromForm(form: URLSearchParams): ApproveValues {
  return {
    subject: one(form, "subject"), slug: one(form, "slug"), from: one(form, "from"), to: one(form, "to"),
    beginAt: one(form, "beginAt"), endAt: one(form, "endAt"), cueStamps: one(form, "cueStamps"),
    support: one(form, "support"), doubt: one(form, "doubt"), doubtReason: one(form, "doubtReason"),
    priorityIds: form.getAll("priorityIds"), highlight: one(form, "highlight"), overlap: one(form, "overlap"),
    stance: one(form, "stance"), moneyNote: one(form, "moneyNote"), outside: one(form, "outside"),
  };
}

function parseOutside(text: string): OutsideSource[] {
  return text.split("\n").map((l) => l.trim()).filter(Boolean).map((line) => {
    const bar = line.indexOf("|");
    return bar < 0 ? { url: line, says: "" } : { url: line.slice(0, bar).trim(), says: line.slice(bar + 1).trim() };
  });
}

export function toReviewInput(v: ApproveValues): ReviewInput {
  return {
    slug: v.slug.trim() || undefined,
    subject: v.subject.trim(),
    quote: { from: v.from.trim(), to: v.to.trim(), beginAt: v.beginAt.trim(), endAt: v.endAt.trim() },
    speaker: {
      cueStamps: v.cueStamps.split(/[\s,]+/).filter(Boolean),
      support: v.support.trim(),
      doubt: v.doubt as Doubt,
      doubtReason: v.doubtReason.trim(),
      outside: parseOutside(v.outside),
    },
    priorityIds: v.priorityIds,
    highlight: v.highlight.split(/[,\n]+/).map((t) => squash(t)).filter(Boolean),
    overlap: v.overlap.trim(),
    stance: v.stance.trim(),
    moneyNote: v.moneyNote.trim(),
  };
}
