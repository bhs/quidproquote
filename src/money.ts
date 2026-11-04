// The money joined to an official: a donor family's Schedule A gifts to the committees tied to the official,
// per committee and per filing, without double counting, and kept apart from outside spending. Totals are
// per committee and are never added across committees or across kinds of money.

import { dollars } from "./text.ts";
import type {
  Committee, CommitteeLine, Family, FilingRow, IndependentRow, MoneySnapshot, OutsideLine, TxRow,
} from "./types.ts";

/** Committees tied to an official: the official's own, or a ballot-measure committee carrying the name. */
export const TIED = ["own", "own-other", "measure"];

// --------------------------------------------------------------------------- committees and officials

/** The office a candidate committee is for, read from its name (the dataset has no office field). */
export function officeOf(filerName: string): string {
  const n = (filerName || "").toUpperCase();
  if (n.includes("DEMOCRATIC") || n.includes("DCCC") || n.includes("CENTRAL COMMITTEE")) return "Democratic County Central Committee";
  if (n.includes("COLLEGE")) return "Community College Board";
  if (n.includes("SCHOOL BOARD") || n.includes("BOARD OF EDUCATION")) return "School Board";
  if (n.includes("MAYOR")) return "Mayor";
  if (n.includes("SUPERVISOR") || /\bD\d+\b/.test(n) || n.includes("MANDELMAN FOR SUPERVISOR")) return "Supervisor";
  return "unstated in the name";
}

/** How a committee is tied to the official, from the data's `filer_type` and the words of its name. The data
 * has no field for control; a name carrying the official's own is the only tie for a ballot-measure committee. */
export function relationOf(filerType: string, filerName: string): string {
  const n = filerName.toUpperCase();
  if (filerType === "Candidate or Officeholder") {
    return ["Supervisor", "Mayor"].includes(officeOf(filerName)) ? "own" : "own-other";
  }
  if (filerType === "470 [Officeholder]") return "own";
  if (filerType === "Person") return "own-other";
  if (filerType === "Primarily Formed Candidate") return n.includes("OPPOS") ? "opposing" : "supporting";
  if (filerType === "Primarily Formed Measure") return "measure";
  return "other";
}

export function committeeKind(c: Committee): string {
  if (c.relation === "measure") return "ballot-measure committee carrying the official's name";
  const officeholder = c.filerName.toUpperCase().includes("OFFICEHOLDER") || c.filerType === "470 [Officeholder]";
  let kind = officeholder ? "officeholder committee" : "own committee";
  if (c.relation === "own-other") kind += `, for another office (${officeOf(c.filerName)})`;
  return kind;
}

// --------------------------------------------------------------------------- donor names and families

export function normName(name: string): string {
  return (name || "")
    .toUpperCase()
    .replace(/\(.*?\)/g, " ")
    .replace(/[^A-Z0-9 ]/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
}

export function donorName(row: { fn?: string; ln?: string }): string {
  return `${(row.fn ?? "").trim()} ${(row.ln ?? "").trim()}`.trim();
}

/** [key, how] of the first family that takes the giver: by the FPPC id the row carries ('id'), else by one of
 * the family's word lists wholly in the name ('name'); [null, null] when none does. */
export function familyOf(families: Family[], name: string, committeeId?: string): [string | null, "id" | "name" | null] {
  const norm = normName(name);
  for (const fam of families) {
    if ((fam.exclude ?? []).some((x) => norm.includes(x))) continue;
    if (committeeId && (fam.committee_ids ?? []).includes(String(committeeId))) return [fam.key, "id"];
    if (fam.patterns.some((words) => words.every((w) => norm.includes(w)))) return [fam.key, "name"];
  }
  return [null, null];
}

export function day(stamp: string | undefined): string {
  return (stamp ?? "").slice(0, 10);
}

function amountOf(row: { calculated_amount: string }): number {
  const v = Number(row.calculated_amount);
  return Number.isFinite(v) ? v : 0;
}

function versionOf(row: TxRow): string {
  const n = Number(row.filing_version);
  return Number.isFinite(n) ? String(Math.trunc(n)) : String(row.filing_version ?? "");
}

function keyA(filer: string, date: string, amount: number): string {
  return `${filer}|${day(date)}|${amount.toFixed(2)}`;
}

// --------------------------------------------------------------------------- the money for a pair

export interface CommitteeMoney {
  committee: Committee;
  kind: string;
  /** Schedule A rows counted once. */
  a: TxRow[];
  aSum: number;
  /** 24-hour reports that repeat a Schedule A row: listed, not counted. */
  repeat: TxRow[];
  /** 24-hour reports with no Schedule A row yet: listed apart with their own total. */
  only: TxRow[];
  onlySum: number;
}

export interface PairMoney {
  per: CommitteeMoney[];
  /** Schedule A rows dropped because another filing repeats them (same committee, date, amount, giver). */
  dropped: TxRow[];
}

/** The family's Schedule A money beside an official, per receiving committee and per filing.
 *
 * Schedule A rows are counted once: a row that repeats another filing's row (same committee, date, amount and
 * giver) is dropped. A 24-hour report (form 497 part 1) that repeats a Schedule A row is listed and not
 * counted; one without a Schedule A row is listed apart with its own total. Only committees tied to the
 * official count. */
export function pairMoney(snap: MoneySnapshot, families: Family[], official: string, family: string): PairMoney {
  const mine = snap.committees.filter((c) => c.official === official && TIED.includes(c.relation));
  const nids = new Set(mine.map((c) => c.filerNid));
  const rows = (snap.familyRows[family] ?? []).filter(
    (r) => nids.has(r.filer_nid) && familyOf(families, donorName(r), r.committee_id)[0] === family,
  );
  const aKeys = new Set(
    rows.filter((r) => r.form_type === "A").map((r) => keyA(r.filer_nid, r.calculated_date, amountOf(r))),
  );
  const per: CommitteeMoney[] = [];
  const dropped: TxRow[] = [];
  for (const c of mine) {
    const committeeRows = rows.filter((r) => r.filer_nid === c.filerNid);
    if (!committeeRows.length) continue;
    const seen = new Set<string>();
    const counted: TxRow[] = [];
    for (const r of committeeRows.filter((x) => x.form_type === "A")) {
      const k = `${day(r.calculated_date)}|${amountOf(r).toFixed(2)}|${donorName(r).toUpperCase()}`;
      if (seen.has(k)) {
        dropped.push(r);
        continue;
      }
      seen.add(k);
      counted.push(r);
    }
    const h24 = committeeRows.filter((r) => r.form_type === "F497P1");
    const repeat = h24.filter((r) => aKeys.has(keyA(c.filerNid, r.calculated_date, amountOf(r))));
    const only = h24.filter((r) => !repeat.includes(r));
    per.push({
      committee: c, kind: committeeKind(c), a: counted, aSum: counted.reduce((s, r) => s + amountOf(r), 0), repeat,
      only, onlySum: only.reduce((s, r) => s + amountOf(r), 0),
    });
  }
  return { per, dropped };
}

/** True when some tied committee holds counted Schedule A money from the family. */
export function isFunded(m: PairMoney): boolean {
  return m.per.some((c) => c.a.length > 0);
}

function filingRow(r: TxRow): FilingRow {
  const amount = amountOf(r);
  return {
    contributionDate: day(r.calculated_date), filingId: r.filing_id_number, version: versionOf(r),
    filingDate: day(r.filing_date), amount, amountText: dollars(amount), giver: donorName(r),
  };
}

function byDate(a: FilingRow, b: FilingRow): number {
  return (
    a.contributionDate.localeCompare(b.contributionDate) ||
    a.filingId.localeCompare(b.filingId) ||
    a.giver.localeCompare(b.giver)
  );
}

/** One line per receiving committee, with its own Schedule A total. There is no total over committees. */
export function committeeLines(m: PairMoney): CommitteeLine[] {
  return m.per.map((c) => {
    const rows = c.a.map(filingRow).sort(byDate);
    const dates = rows.map((r) => r.contributionDate);
    return {
      committee: c.committee.filerName,
      filer: c.committee.filerNid,
      kind: c.kind,
      scheduleATotal: c.aSum,
      scheduleATotalText: dollars(c.aSum),
      rows,
      repeats: c.repeat.map(filingRow).sort(byDate),
      h24Only: c.only.map(filingRow).sort(byDate),
      h24OnlyTotalText: c.only.length ? dollars(c.onlySum) : "",
      first: dates[0] ?? "",
      last: dates[dates.length - 1] ?? "",
      givers: [...new Set([...c.a, ...c.repeat, ...c.only].map(donorName))].sort(),
    };
  });
}

// --------------------------------------------------------------------------- outside spending

/** True when the candidate as filed is the official: the surname is a whole word of it and, when it holds
 * other words, the given name is one of them. */
export function namesOfficial(candidate: string, surname: string, given?: string): boolean {
  const tokens = (candidate || "").toUpperCase().match(/[A-Z']+/g) ?? [];
  if (!tokens.includes(surname.toUpperCase())) return false;
  return !given || (tokens.length === 1 && tokens[0] === surname.toUpperCase()) || tokens.includes(given.toUpperCase());
}

/** Form 496 spending that names the official, by committees the family's names take: kept apart from gifts and
 * never added to them. */
export function outsideSpending(snap: MoneySnapshot, families: Family[], official: string, family: string): OutsideLine[] {
  const c0 = snap.committees.find((c) => c.official === official);
  if (!c0) return [];
  const agg = new Map<string, { payer: string; code: string; amount: number; filings: Set<string>; first: string; last: string }>();
  for (const r of snap.independent as IndependentRow[]) {
    if (!namesOfficial(r.candidate_last_name, c0.surname, c0.given)) continue;
    const dist = (r.district_number ?? "").trim();
    if (dist && c0.district && dist !== c0.district) continue;
    const office = (r.office_description ?? "").toUpperCase();
    if (c0.office === "Mayor" && office.includes("SUPERVISOR")) continue;
    if (c0.office !== "Mayor" && office.includes("MAYOR")) continue;
    if (familyOf(families, r.filer_name)[0] !== family) continue;
    const key = `${r.filer_nid}|${r.support_oppose_code}`;
    const a = agg.get(key) ?? { payer: r.filer_name, code: r.support_oppose_code, amount: 0, filings: new Set<string>(), first: "9999", last: "" };
    a.amount += Number(r.amt) || 0;
    a.filings.add(r.filing_id_number);
    if (day(r.d0) < a.first) a.first = day(r.d0);
    if (day(r.d1) > a.last) a.last = day(r.d1);
    agg.set(key, a);
  }
  return [...agg.values()].map((a) => ({
    spender: a.payer, stance: a.code === "S" ? "supporting" : "opposing", amountText: dollars(a.amount),
    filings: [...a.filings].sort(), first: a.first, last: a.last,
  }));
}

// --------------------------------------------------------------------------- how the donor is recognised

/** How the givers in a pair are recognised as the donor's: by the FPPC id the Filers dataset resolves, or by
 * name only. */
export function tieNote(m: PairMoney, snap: MoneySnapshot, families: Family[]): { how: string[]; text: string } {
  const seen = new Map<string, { name: string; cid: string; how: string | null }>();
  for (const c of m.per) {
    for (const r of [...c.a, ...c.repeat, ...c.only]) {
      const name = donorName(r);
      const cid = r.committee_id ?? "";
      seen.set(`${name}|${cid}`, { name, cid, how: familyOf(families, name, cid)[1] });
    }
  }
  const entries = [...seen.values()];
  const filerName = (cid: string) => snap.filersLookup[cid]?.[0]?.filer_name;
  const byId = [...new Set(entries.filter((e) => e.how === "id").map((e) => `${e.cid} (${filerName(e.cid) ?? "not in Filers"})`))].sort();
  const byName = [...new Set(entries.filter((e) => e.how === "name").map((e) => e.name))].sort();
  const idsName = [...new Set(entries.filter((e) => e.how === "name" && e.cid).map((e) => e.cid))].sort();
  const resolved = idsName.filter((cid) => snap.filersLookup[cid]);
  const how: string[] = [];
  if (byId.length) how.push(`by Filers id: ${byId.join("; ")}`);
  if (byName.length) {
    let s = `by name only (${byName.length} giver name${byName.length === 1 ? "" : "s"} as filed)`;
    if (idsName.length && !resolved.length) s += "; the FPPC ids on those rows do not resolve in the Filers dataset";
    else if (resolved.length) {
      s += `; FPPC id${resolved.length === 1 ? "" : "s"} that resolve${resolved.length === 1 ? "s" : ""} in the Filers dataset: ` +
        resolved.map((cid) => `${cid} ('${filerName(cid)}')`).join(", ");
    } else s += "; the rows carry no FPPC id";
    how.push(s);
  }
  return { how, text: `Tie to the donor recognised ${how.join("; ")}.` };
}
