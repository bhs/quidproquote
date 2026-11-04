// Builds a card from a review: the official's exact words re-read from the transcript, the speaker credit with
// the caption rows it rests on, the donor's own words, and the money by committee and filing. A card is
// refused (ValidationError, with every reason) when its quote is not word for word in the transcript, a
// highlighted word is not literally in both the quote and the donor's words, a cited caption stamp is missing,
// the credit's doubt is not low, medium or high, or no money from the donor was found for the official.

import { committeeLines, isFunded, outsideSpending, pairMoney, tieNote } from "./money.ts";
import { NO_CAUSE } from "./render.ts";
import { hasTerm, isStamp } from "./text.ts";
import { cueRows, extractQuote, isVerbatim } from "./transcript.ts";
import { DOUBT_LEVELS } from "./types.ts";
import { ValidationError } from "./validation.ts";
import type { Card, Family, Meeting, MoneySnapshot, Official, Priority, ReviewInput, Row, Statement } from "./types.ts";

export interface CardInput {
  slug: string;
  review: ReviewInput;
  official: Official;
  family: Family;
  meeting: Meeting;
  rows: Row[];
  snapshot: MoneySnapshot;
  families: Family[];
  priorities: Priority[];
}

const MONEY_NOTE_STANDARD =
  "One line per receiving committee. Each Schedule A total is that committee's own and is never added to another's.";

export function buildCard(input: CardInput): Card {
  const { review, official, family, meeting, rows, snapshot, families } = input;
  const problems: string[] = [];
  const need = (value: string, what: string) => {
    if (!value.trim()) problems.push(`${what} is missing.`);
  };
  need(review.subject, "The subject");
  need(review.overlap, "What the two have in common");
  need(review.stance, "Where they differ");
  need(review.speaker.support, "How the transcript supports the speaker credit");
  need(review.speaker.doubtReason, "The reason for the doubt level");
  if (!DOUBT_LEVELS.includes(review.speaker.doubt)) problems.push("The doubt must be low, medium or high.");

  let quote: ReturnType<typeof extractQuote> | undefined;
  try {
    quote = extractQuote(rows, review.quote.from, review.quote.to, review.quote.beginAt, review.quote.endAt);
    if (!isVerbatim(rows, quote.text)) problems.push("The quote is not word for word in the transcript.");
  } catch (err) {
    problems.push(`Quote: ${(err as Error).message}.`);
  }

  let credit: Row[] = [];
  if (!review.speaker.cueStamps.length) problems.push("Name at least one caption row the speaker credit rests on.");
  for (const stamp of review.speaker.cueStamps) if (!isStamp(stamp)) problems.push(`"${stamp}" is not a caption stamp (HH:MM:SS).`);
  try {
    if (review.speaker.cueStamps.every(isStamp)) credit = cueRows(rows, review.speaker.cueStamps);
  } catch (err) {
    problems.push(`Speaker credit: ${(err as Error).message}.`);
  }

  const statements: Statement[] = [];
  if (!review.priorityIds.length) problems.push("Choose the donor priority the card shows.");
  for (const id of review.priorityIds) {
    const p = input.priorities.find((x) => x.id === id);
    if (!p) problems.push(`The priority ${id} does not exist.`);
    else if (p.family !== family.key) problems.push(`The priority ${id} belongs to another donor.`);
    else statements.push({ id: p.id, section: p.section, text: p.text, url: p.url, pageDate: p.pageDate, retrieved: p.retrieved, kind: p.kind });
  }

  if (quote) {
    const donorTexts = statements.map((s) => `${s.section} ${s.text}`);
    for (const term of review.highlight) {
      if (!hasTerm(quote.text, term)) problems.push(`The highlighted word "${term}" is not in the quote.`);
      else if (!donorTexts.some((t) => hasTerm(t, term))) problems.push(`The highlighted word "${term}" is not in the donor's words.`);
    }
  }

  const money = pairMoney(snapshot, families, official.name, family.key);
  if (!isFunded(money)) problems.push(`No Schedule A money from ${family.name} to a committee tied to ${official.name} was found, so there is no card.`);
  if (problems.length || !quote) throw new ValidationError(problems);

  const lines = committeeLines(money);
  const tie = tieNote(money, snapshot, families);
  const filingIds = [...new Set(lines.flatMap((l) => [...l.rows, ...l.h24Only].map((r) => r.filingId)))].sort();
  const role = official.office + (official.district ? `, District ${official.district}` : "");
  return {
    id: input.slug, slug: input.slug, title: `${official.name} \u00d7 ${family.name}`, subject: review.subject.trim(),
    official: { name: official.name, role },
    quote: {
      text: quote.text, meeting: meeting.body, date: meeting.date, firstStamp: quote.firstStamp, lastStamp: quote.lastStamp,
      transcriptUrl: meeting.url, retrieved: meeting.retrieved,
    },
    highlight: review.highlight,
    money: {
      committees: lines, outsideSpending: outsideSpending(snapshot, families, official.name, family.key),
      note: MONEY_NOTE_STANDARD, moneyNote: review.moneyNote.trim(), retrieved: snapshot.retrieved,
      dataLoadedAt: snapshot.dataLoadedAt, datasetUrl: snapshot.datasetUrl,
    },
    donor: { name: family.name, kind: family.kind, tie: { ...tie, note: family.link_note ?? "" }, statements },
    reading: { inCommon: review.overlap.trim(), differs: review.stance.trim(), cause: NO_CAUSE },
    speakerCredit: {
      doubt: review.speaker.doubt, reason: review.speaker.doubtReason.trim(), support: review.speaker.support.trim(),
      cueRows: credit, outside: review.speaker.outside,
    },
    sources: {
      transcript: meeting.url, donorPages: [...new Set(statements.map((s) => s.url))].sort(), filingIds,
      datasetUrl: snapshot.datasetUrl, moneyRetrieved: snapshot.retrieved,
    },
  };
}
