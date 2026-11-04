// The donor's priority: its own words, where they were read (a source description and a URL) and the date of the
// page. A save missing any of those is refused. The measure names the words speak to are read from the words
// themselves; phrases are the maintainer's.

import { createHash } from "node:crypto";
import { isIsoDate, squash, today } from "./text.ts";
import { ValidationError } from "./validation.ts";
import type { Family, Priority } from "./types.ts";

export interface PriorityForm {
  family?: string;
  text?: string;
  kind?: string;
  url?: string;
  pageDate?: string;
  retrieved?: string;
  section?: string;
  phrases?: string;
}

/** Measure letters named in the words: "Prop H", "Proposition H", "Props D, E and F", "Measure J". */
export function extractMeasures(text: string): string[] {
  const letters = new Set<string>();
  const rx = /\b(?:[Pp]rops?\.?|[Pp]ropositions?|[Mm]easures?)\s+([A-Z]{1,2}(?:\s*(?:,\s*and|,|and|&)\s*[A-Z]{1,2}\b)*)\b/g;
  for (const m of text.matchAll(rx)) {
    for (const l of m[1].split(/[^A-Z]+/).filter(Boolean)) letters.add(l);
  }
  return [...letters].sort();
}

/** The transcript spellings of the measures: "Proposition H", "Prop H", "Prop. H", "Measure H". */
export function measureTerms(letters: string[]): string[] {
  return letters.flatMap((l) => [`Proposition ${l}`, `Prop ${l}`, `Prop. ${l}`, `Measure ${l}`]);
}

export function splitPhrases(text: string): string[] {
  return [...new Set(text.split(/[\n,;]+/).map((p) => squash(p)).filter(Boolean))];
}

function validUrl(text: string): boolean {
  try {
    const u = new URL(text);
    return u.protocol === "https:" || u.protocol === "http:";
  } catch {
    return false;
  }
}

export function priorityId(family: string, url: string, text: string): string {
  return `${family}-${createHash("sha1").update(`${url}\n${text}`).digest("hex").slice(0, 8)}`;
}

/** The priority a form describes, or a ValidationError naming everything missing or wrong. */
export function validatePriority(form: PriorityForm, families: Family[], now: Date = new Date()): Priority {
  const problems: string[] = [];
  const family = (form.family ?? "").trim();
  const text = squash(form.text ?? "");
  const kind = squash(form.kind ?? "");
  const url = (form.url ?? "").trim();
  const pageDate = (form.pageDate ?? "").trim();
  const retrieved = (form.retrieved ?? "").trim() || today(now);
  if (!families.some((f) => f.key === family)) problems.push("Choose the donor the words belong to.");
  if (!text) problems.push("The donor's words are missing: paste them exactly as the donor's page gives them.");
  if (!kind) problems.push("The source is missing: say what kind of page it is (for example a voter guide on the organisation's own site).");
  if (!url) problems.push("The URL is missing.");
  else if (!validUrl(url)) problems.push("The URL must be a full http or https address.");
  if (!pageDate) problems.push("The date is missing: give the date shown on the page (YYYY-MM-DD).");
  else if (!isIsoDate(pageDate)) problems.push("The date must be written YYYY-MM-DD.");
  else if (pageDate > today(now)) problems.push("The page date is in the future.");
  if (!isIsoDate(retrieved)) problems.push("The retrieval date must be written YYYY-MM-DD.");
  if (problems.length) throw new ValidationError(problems);
  const section = squash(form.section ?? "");
  return {
    id: priorityId(family, url, text), family, section, text, url, kind, pageDate, retrieved,
    phrases: splitPhrases(form.phrases ?? ""), measures: extractMeasures(`${section} ${text}`),
  };
}
