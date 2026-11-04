// The shapes the site keeps and passes around. Records on disk are JSON of these shapes.

export type Doubt = "low" | "medium" | "high";
export const DOUBT_LEVELS: readonly Doubt[] = ["low", "medium", "high"];

/** One caption row of a Legistar transcript: the stamp from the start of the recording, and its words. */
export interface Row {
  stamp: string;
  text: string;
}

export interface RosterCommittee {
  filer_nid: string;
  filer_name: string;
  filer_type: string;
  status: string;
}

/** A San Francisco official: the surname as the captions spell it when they get it right (`exact`), the
 * spellings the captions are known to garble it into (`garbled`), and the committees tied to the official. */
export interface Official {
  name: string;
  office: string;
  district: string;
  surname: string;
  given: string;
  exact: string[];
  garbled: string[];
  committees: RosterCommittee[];
}

export interface Family {
  key: string;
  name: string;
  kind: string;
  patterns: string[][];
  exclude?: string[];
  committee_ids?: string[];
  link_note?: string;
}

/** A committee tied to an official; `relation` is own, own-other, measure, supporting, opposing or other. */
export interface Committee {
  official: string;
  office: string;
  district: string;
  surname: string;
  given: string;
  filerNid: string;
  filerName: string;
  filerType: string;
  status: string;
  relation: string;
}

/** A row of the Ethics Commission's Transactions dataset, with the dataset's own column names. */
export interface TxRow {
  filer_nid: string;
  form_type: string;
  filing_id_number: string;
  filing_date: string;
  filing_version?: string;
  calculated_date: string;
  calculated_amount: string;
  committee_id?: string;
  entity_code?: string;
  fn?: string;
  ln?: string;
}

export interface IndependentRow {
  filer_nid: string;
  filer_name: string;
  filing_id_number: string;
  candidate_last_name: string;
  support_oppose_code: string;
  office_description?: string;
  district_number?: string;
  amt: string;
  d0: string;
  d1: string;
}

export interface FilerRecord {
  filer_name: string;
  filer_nid?: string;
  filer_type?: string;
  status?: string;
}

export interface MoneySnapshot {
  retrieved: string;
  dataLoadedAt: string;
  datasetUrl: string;
  committees: Committee[];
  familyRows: Record<string, TxRow[]>;
  filersLookup: Record<string, FilerRecord[]>;
  independent: IndependentRow[];
}

/** A donor's own words on a subject, as the maintainer entered them. */
export interface Priority {
  id: string;
  family: string;
  section: string;
  text: string;
  url: string;
  kind: string;
  pageDate: string;
  retrieved: string;
  /** Phrases a transcript passage may hit (the maintainer's). */
  phrases: string[];
  /** Measure letters the words name ("H" for Prop H). */
  measures: string[];
}

export interface Meeting {
  id: string;
  body: string;
  date: string;
  url: string;
  retrieved: string;
  rows: number;
}

export interface CaptionLine {
  stamp: string;
  text: string;
  kind: "before" | "passage" | "after";
}

export interface Candidate {
  id: string;
  status: "pending" | "approved" | "rejected";
  origin: "rules" | "maintainer";
  meetingId: string;
  body: string;
  date: string;
  official: string;
  officialRole: string;
  familyKey: string;
  familyName: string;
  priorityIds: string[];
  anchorHits: string[];
  topicHits: string[];
  firstStamp: string;
  lastStamp: string;
  text: string;
  doubt: Doubt;
  doubtWhy: string[];
  cue: string;
  cueStamp: string;
  cueLines: Row[];
  lines: CaptionLine[];
  createdAt: string;
  decidedAt?: string;
}

export interface OutsideSource {
  url: string;
  says: string;
}

/** What a person decides about a candidate: the quote's bounds, the credit and the readings. */
export interface ReviewInput {
  slug?: string;
  subject: string;
  quote: { from: string; to: string; beginAt: string; endAt: string };
  speaker: { cueStamps: string[]; support: string; doubt: Doubt; doubtReason: string; outside: OutsideSource[] };
  priorityIds: string[];
  highlight: string[];
  overlap: string;
  stance: string;
  moneyNote: string;
}

export interface FilingRow {
  contributionDate: string;
  filingId: string;
  version: string;
  filingDate: string;
  amount: number;
  amountText: string;
  giver: string;
}

export interface CommitteeLine {
  committee: string;
  filer: string;
  kind: string;
  scheduleATotal: number;
  scheduleATotalText: string;
  rows: FilingRow[];
  repeats: FilingRow[];
  h24Only: FilingRow[];
  h24OnlyTotalText: string;
  first: string;
  last: string;
  givers: string[];
}

export interface OutsideLine {
  spender: string;
  stance: "supporting" | "opposing";
  amountText: string;
  filings: string[];
  first: string;
  last: string;
}

export interface Statement {
  id: string;
  section: string;
  text: string;
  url: string;
  pageDate: string;
  retrieved: string;
  kind: string;
}

export interface Card {
  id: string;
  slug: string;
  title: string;
  subject: string;
  official: { name: string; role: string };
  quote: {
    text: string;
    meeting: string;
    date: string;
    firstStamp: string;
    lastStamp: string;
    transcriptUrl: string;
    retrieved: string;
  };
  highlight: string[];
  money: {
    committees: CommitteeLine[];
    outsideSpending: OutsideLine[];
    note: string;
    moneyNote: string;
    retrieved: string;
    dataLoadedAt: string;
    datasetUrl: string;
  };
  donor: { name: string; kind: string; tie: { how: string[]; text: string; note: string }; statements: Statement[] };
  reading: { inCommon: string; differs: string; cause: string };
  speakerCredit: { doubt: Doubt; reason: string; support: string; cueRows: Row[]; outside: OutsideSource[] };
  sources: { transcript: string; donorPages: string[]; filingIds: string[]; datasetUrl: string; moneyRetrieved: string };
}

export interface Pairing {
  id: string;
  n: number;
  slug: string;
  candidateId: string;
  status: "published" | "unpublished";
  publishedAt: string;
  unpublishedAt?: string;
  review: ReviewInput;
  card: Card;
}

export interface ReviewRecord {
  id: string;
  at: string;
  decision: "approved" | "rejected" | "unpublished" | "republished";
  candidateId: string;
  pairingId?: string;
  note?: string;
}

export interface FetchLogEntry {
  id: string;
  at: string;
  source: "legistar" | "granicus" | "datasf" | "refresh" | "seed";
  what: string;
  ok: boolean;
  detail: string;
}
