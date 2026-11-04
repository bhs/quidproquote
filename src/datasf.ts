// The Ethics Commission's campaign finance Transactions and Filers datasets on DataSF (public). An app token,
// when one is supplied, only lifts the rate limit. A failed query stops the refresh and is logged; an empty
// list means the query found no rows.

import { Fetcher, FetchError } from "./fetcher.ts";
import { familyOf, relationOf } from "./money.ts";
import { today } from "./text.ts";
import type { Committee, Family, FilerRecord, IndependentRow, MoneySnapshot, Official, TxRow } from "./types.ts";

export const TRANSACTIONS = "pitq-e56w";
export const FILERS = "4c8t-ngau";
export const DATASET_PAGE = "https://data.sf.gov/d/pitq-e56w";
const RESOURCE = (dataset: string): string => `https://data.sf.gov/resource/${dataset}.json`;

export const lit = (value: string): string => `'${String(value).replace(/'/g, "''")}'`;
export const inList = (values: string[]): string => values.map(lit).join(",");

/** A SoQL clause matching the family's patterns in a name column and the family's FPPC ids in an id column. */
export function familyClause(column: string, fam: Family, idColumn: string): string {
  const groups = fam.patterns.map((words) => "(" + words.map((w) => `upper(${column}) like ${lit("%" + w + "%")}`).join(" AND ") + ")");
  if (fam.committee_ids?.length) groups.push(`${idColumn} in (${inList(fam.committee_ids)})`);
  return "(" + groups.join(" OR ") + ")";
}

export class DataSf {
  private readonly fetcher: Fetcher;
  private readonly appToken: string;

  constructor(fetcher: Fetcher, appToken = "") {
    this.fetcher = fetcher;
    this.appToken = appToken;
  }

  async query<T>(dataset: string, params: Record<string, string>): Promise<T[]> {
    const url = `${RESOURCE(dataset)}?${new URLSearchParams(params)}`;
    const headers: Record<string, string> = { Accept: "application/json" };
    if (this.appToken) headers["X-App-Token"] = this.appToken;
    const raw = await this.fetcher.text(url, undefined, headers);
    let rows: unknown;
    try {
      rows = JSON.parse(raw);
    } catch {
      throw new FetchError(`DataSF answered with something other than JSON (${url.slice(0, 200)})`);
    }
    if (!Array.isArray(rows)) throw new FetchError(`unexpected DataSF reply: ${raw.slice(0, 200)}`);
    return rows as T[];
  }

  /** Every row of a query, paged. The query must carry a stable $order. */
  async queryAll<T>(dataset: string, params: Record<string, string>, page = 5000): Promise<T[]> {
    const out: T[] = [];
    for (let offset = 0; ; offset += page) {
      const rows = await this.query<T>(dataset, { ...params, $limit: String(page), $offset: String(offset) });
      out.push(...rows);
      if (rows.length < page) return out;
    }
  }
}

export function committeesTable(roster: Official[]): Committee[] {
  return roster.flatMap((o) =>
    o.committees.map((c) => ({
      official: o.name, office: o.office, district: o.district, surname: o.surname, given: o.given,
      filerNid: c.filer_nid, filerName: c.filer_name, filerType: c.filer_type, status: c.status,
      relation: relationOf(c.filer_type, c.filer_name),
    })),
  );
}

export interface MoneyProgress {
  (what: string, ok: boolean, detail: string): Promise<void> | void;
}

/** Reads the money for every committee tied to the roster's officials: the Schedule A and 24-hour rows under
 * each donor family's names, the form 496 spending that names an official, and who the committee donors are.
 * Throws on the first failed query, so a half-read snapshot is never saved. */
export async function fetchMoneySnapshot(
  datasf: DataSf, roster: Official[], families: Family[], progress: MoneyProgress = () => undefined,
): Promise<MoneySnapshot> {
  const committees = committeesTable(roster);
  const nids = [...new Set(committees.map((c) => c.filerNid))].sort();

  const filers = await datasf.query<{ filer_nid: string; filer_name?: string; status?: string }>(FILERS, {
    $where: `filer_nid in (${inList(nids)})`, $limit: "500",
  });
  await progress("Filers records of the tied committees", true, `${filers.length} read`);
  const byNid = new Map(filers.map((f) => [f.filer_nid, f] as const));
  for (const c of committees) {
    const f = byNid.get(c.filerNid);
    if (f) {
      c.status = f.status ?? c.status;
      c.filerName = f.filer_name ?? c.filerName;
      c.relation = relationOf(c.filerType, c.filerName);
    }
  }

  const loaded = await datasf.query<{ m: string }>(TRANSACTIONS, { $select: "max(data_loaded_at) as m" });
  const dataLoadedAt = (loaded[0]?.m ?? "").slice(0, 10);
  if (!dataLoadedAt) throw new FetchError("the Transactions dataset did not say when it was loaded");

  const familyRows: Record<string, TxRow[]> = {};
  for (const fam of families) {
    const rows = await datasf.queryAll<TxRow>(TRANSACTIONS, {
      $select: "filer_nid, form_type, filing_id_number, filing_date, filing_version, calculated_date, " +
        "calculated_amount, entity_code, committee_id, transaction_first_name as fn, transaction_last_name as ln",
      $where: `form_type in ('A','F497P1') AND filer_nid in (${inList(nids)}) AND ${familyClause("transaction_last_name", fam, "committee_id")}`,
      $order: "filer_nid, calculated_date, filing_id_number",
    });
    familyRows[fam.key] = rows.filter((r) => familyOf(families, `${r.fn ?? ""} ${r.ln ?? ""}`.trim(), r.committee_id)[0] === fam.key);
    await progress(`rows under ${fam.name}'s names`, true, `${familyRows[fam.key].length} rows`);
  }

  const surnames = [...new Set(committees.map((c) => c.surname))].sort();
  const like = surnames.map((s) => `upper(candidate_last_name) like ${lit("%" + s.toUpperCase() + "%")}`).join(" OR ");
  const independent = await datasf.queryAll<IndependentRow>(TRANSACTIONS, {
    $select: "filer_nid, filer_name, filing_id_number, candidate_last_name, support_oppose_code, office_description, " +
      "district_number, sum(calculated_amount) as amt, min(calculated_date) as d0, max(calculated_date) as d1",
    $where: `form_type='F496' AND (${like})`,
    $group: "filer_nid, filer_name, filing_id_number, candidate_last_name, support_oppose_code, office_description, district_number",
    $order: "filer_nid, filing_id_number, candidate_last_name",
  });
  await progress("form 496 outside spending naming an official", true, `${independent.length} rows`);

  const ids = [...new Set(Object.values(familyRows).flat().map((r) => r.committee_id).filter((x): x is string => !!x))].sort();
  const filersLookup: Record<string, FilerRecord[]> = {};
  for (let i = 0; i < ids.length; i += 120) {
    const chunk = ids.slice(i, i + 120);
    const found = await datasf.query<FilerRecord & { fppc_id: string }>(FILERS, {
      $where: `fppc_id in (${inList(chunk)})`, $limit: "2000",
    });
    for (const r of found) {
      (filersLookup[r.fppc_id] ??= []).push({ filer_name: r.filer_name, filer_nid: r.filer_nid, filer_type: r.filer_type, status: r.status });
    }
  }
  await progress("who the committee donors are (Filers dataset)", true, `${Object.keys(filersLookup).length} ids resolved`);

  return { retrieved: today(), dataLoadedAt, datasetUrl: DATASET_PAGE, committees, familyRows, filersLookup, independent };
}
