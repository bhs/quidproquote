// The city's Legistar calendar and caption transcripts. The calendar is read the way the page itself is used:
// the year list is a form field, so the page is requested, its hidden fields are sent back with the year
// chosen, and the rows of the calendar table are read for each meeting's body, date and transcript link. When
// the calendar cannot be read the Granicus feeds, which carry the same recordings, are read instead.

import { Fetcher, FetchError } from "./fetcher.ts";
import { decodeEntities, plainText } from "./text.ts";
import { parseTranscriptHtml } from "./transcript.ts";
import type { Row } from "./types.ts";

export const BASE = "https://sfgov.legistar.com/";
export const CALENDAR = BASE + "Calendar.aspx";
export const transcriptUrl = (id: string | number): string => `${BASE}Transcript.aspx?ID1=${id}`;
const YEARS_FIELD = "ctl00$ContentPlaceHolder1$lstYears";
const BODIES_FIELD = "ctl00$ContentPlaceHolder1$lstBodies";

/** The Board and the standing committees whose members are the officials of the roster. */
export const BODIES = [
  "Board of Supervisors", "Budget and Appropriations Committee", "Budget and Finance Committee",
  "Government Audit and Oversight Committee", "Land Use and Transportation Committee",
  "Public Safety and Neighborhood Services Committee", "Rules Committee",
];

const MONTHS: Record<string, number> = Object.fromEntries(
  "JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY AUGUST SEPTEMBER OCTOBER NOVEMBER DECEMBER".split(" ").map((m, i) => [m, i + 1]),
);

export interface CalendarRow {
  body: string;
  date: string;
  minutesUrl: string;
  detailUrl: string;
  transcriptId: string | null;
}

export function hiddenFields(page: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const m of page.matchAll(/<input[^>]+type="hidden"[^>]*>/gi)) {
    const name = /name="([^"]+)"/.exec(m[0]);
    const value = /value="([^"]*)"/.exec(m[0]);
    if (name) out[name[1]] = value ? decodeEntities(value[1]) : "";
  }
  return out;
}

export function isoDate(text: string): string {
  const m = /(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(text || "");
  return m ? `${m[3]}-${m[1].padStart(2, "0")}-${m[2].padStart(2, "0")}` : "";
}

export function parseCalendar(page: string): CalendarRow[] {
  const out: CalendarRow[] = [];
  for (const tr of page.match(/<tr\b[\s\S]*?<\/tr>/gi) ?? []) {
    const cells = tr.match(/<td\b[\s\S]*?<\/td>/gi) ?? [];
    if (cells.length < 4) continue;
    const text = cells.map(plainText);
    const date = text.map(isoDate).find(Boolean) ?? "";
    if (!date) continue;
    const links = [...tr.matchAll(/href=["']([^"']+)["']/gi)].map((m) => decodeEntities(m[1]));
    const minutes = links.find((l) => /View\.ashx\?M=M\b/.test(l)) ?? "";
    const detail = links.find((l) => l.includes("MeetingDetail.aspx")) ?? "";
    const tid = /Transcript\.aspx\?ID1=(\d+)/.exec(tr);
    out.push({
      body: text[0], date, minutesUrl: minutes ? new URL(minutes, BASE).toString() : "",
      detailUrl: detail ? new URL(detail, BASE).toString() : "", transcriptId: tid ? tid[1] : null,
    });
  }
  return out;
}

export async function calendarYear(fetcher: Fetcher, year: number): Promise<CalendarRow[]> {
  const page = await fetcher.text(CALENDAR);
  const fields = hiddenFields(page);
  if (!("__VIEWSTATE" in fields)) throw new FetchError("the calendar page carries no form state to send back");
  Object.assign(fields, {
    __EVENTTARGET: YEARS_FIELD, __EVENTARGUMENT: "", [YEARS_FIELD]: String(year), [BODIES_FIELD]: "All",
    ctl00_ContentPlaceHolder1_lstYears_ClientState:
      `{"logEntries":[],"value":"${year}","text":"${year}","enabled":true,"checkedIndices":[],"checkedItemsTextOverflows":false}`,
  });
  const rows = parseCalendar(await fetcher.text(CALENDAR, fields));
  if (!rows.length) throw new FetchError(`the calendar for ${year} held no meeting rows`);
  return rows;
}

const GRANICUS_RSS = (view: number): string => `https://sanfrancisco.granicus.com/ViewPublisherRSS.php?view_id=${view}`;
const RSS_VIEWS: Record<number, string> = {
  10: "Board of Supervisors", 177: "Land Use and Transportation Committee", 13: "Rules Committee",
  11: "Government Audit and Oversight Committee",
};

/** [{body, date, transcriptId}] from a Granicus publisher feed: each item's clip id is the transcript id of the
 * Legistar page for the same recording, and its title gives the date. */
export function parseRss(xml: string, body: string): CalendarRow[] {
  const out: CalendarRow[] = [];
  for (const item of xml.match(/<item>[\s\S]*?<\/item>/gi) ?? []) {
    const clip = /clip_id=(\d+)/.exec(item);
    const d = /dated\s+\w+,\s+(\d{1,2})\s+(\w+)\s+(\d{4})/i.exec(decodeEntities(item));
    if (!clip || !d || !(d[2].toUpperCase() in MONTHS)) continue;
    out.push({
      body, date: `${d[3]}-${String(MONTHS[d[2].toUpperCase()]).padStart(2, "0")}-${d[1].padStart(2, "0")}`,
      minutesUrl: "", detailUrl: "", transcriptId: clip[1],
    });
  }
  return out;
}

export async function rssRows(fetcher: Fetcher, year: number): Promise<CalendarRow[]> {
  const rows: CalendarRow[] = [];
  for (const [view, body] of Object.entries(RSS_VIEWS)) {
    rows.push(...parseRss(await fetcher.text(GRANICUS_RSS(Number(view))), body).filter((r) => r.date.startsWith(String(year))));
  }
  if (!rows.length) throw new FetchError(`the Granicus feeds held no meetings of ${year}`);
  return rows;
}

export interface Discovered {
  rows: CalendarRow[];
  route: "Legistar calendar" | "Granicus feeds";
  notes: string[];
}

function bodyMatch(name: string): string | undefined {
  return BODIES.find((b) => b.toLowerCase() === name.trim().toLowerCase());
}

/** The meetings of `year` in the Board and its standing committees that have a transcript, newest first. */
export async function discoverMeetings(fetcher: Fetcher, year: number): Promise<Discovered> {
  const notes: string[] = [];
  let route: Discovered["route"] = "Legistar calendar";
  let rows: CalendarRow[];
  try {
    rows = (await calendarYear(fetcher, year)).flatMap((r) => {
      const body = bodyMatch(r.body);
      return body ? [{ ...r, body }] : [];
    });
    if (!rows.length) throw new FetchError("no row of the calendar names the Board or one of its standing committees");
  } catch (err) {
    if (!(err instanceof FetchError)) throw err;
    notes.push(`Legistar calendar not read (${err.message}); the Granicus feeds were used instead`);
    route = "Granicus feeds";
    rows = await rssRows(fetcher, year);
  }
  const withTranscript = rows.filter((r) => r.transcriptId);
  const without = rows.length - withTranscript.length;
  if (without) notes.push(`${without} meeting rows of the Board and its standing committees carry no transcript link`);
  withTranscript.sort((a, b) => b.date.localeCompare(a.date));
  return { rows: withTranscript, route, notes };
}

/** The caption rows of one transcript. Throws FetchError when the page holds no captions. */
export async function fetchTranscript(fetcher: Fetcher, id: string): Promise<Row[]> {
  const rows = parseTranscriptHtml(await fetcher.text(transcriptUrl(id)));
  if (rows.length < 50) throw new FetchError(`transcript ${id} holds ${rows.length} caption rows`);
  return rows;
}
