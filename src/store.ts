// Records are JSON files under the data directory, written atomically (a temporary file in the same
// directory, flushed, then renamed over the target) so a reader never sees a half-written file. There is no
// database engine. Writes to one file are serialised so two requests cannot lose each other's change.

import { randomBytes } from "node:crypto";
import { mkdir, open, readFile, readdir, rename, rm } from "node:fs/promises";
import { dirname, join } from "node:path";
import type { Candidate, FetchLogEntry, Meeting, MoneySnapshot, Pairing, Priority, ReviewRecord, Row } from "./types.ts";

export async function writeTextAtomic(file: string, text: string): Promise<void> {
  await mkdir(dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.${randomBytes(4).toString("hex")}.tmp`;
  const handle = await open(tmp, "w");
  try {
    await handle.writeFile(text, "utf-8");
    await handle.sync();
  } finally {
    await handle.close();
  }
  try {
    await rename(tmp, file);
  } catch (err) {
    await rm(tmp, { force: true });
    throw err;
  }
}

export async function readJson<T>(file: string, fallback: T): Promise<T> {
  let raw: string;
  try {
    raw = await readFile(file, "utf-8");
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return fallback;
    throw err;
  }
  return JSON.parse(raw) as T;
}

const chains = new Map<string, Promise<unknown>>();

/** Runs `job` after every earlier job on the same key has finished. */
function serialised<T>(key: string, job: () => Promise<T>): Promise<T> {
  const previous = chains.get(key) ?? Promise.resolve();
  const next = previous.then(job, job);
  chains.set(key, next.catch(() => undefined));
  return next;
}

/** A list of records with an `id`, kept in one JSON file. */
export class Collection<T extends { id: string }> {
  readonly file: string;

  constructor(file: string) {
    this.file = file;
  }

  async all(): Promise<T[]> {
    return readJson<T[]>(this.file, []);
  }

  async get(id: string): Promise<T | undefined> {
    return (await this.all()).find((item) => item.id === id);
  }

  /** Reads the list, lets `change` return the new one, and writes it, as one step. */
  update<R>(change: (items: T[]) => { items: T[]; result: R }): Promise<R> {
    return serialised(this.file, async () => {
      const { items, result } = change(await this.all());
      await writeTextAtomic(this.file, JSON.stringify(items, null, 1) + "\n");
      return result;
    });
  }

  async put(item: T): Promise<void> {
    await this.update((items) => {
      const at = items.findIndex((x) => x.id === item.id);
      const next = at < 0 ? [...items, item] : items.map((x, i) => (i === at ? item : x));
      return { items: next, result: undefined };
    });
  }

  async putMany(more: T[]): Promise<void> {
    await this.update((items) => {
      const byId = new Map(items.map((x) => [x.id, x] as const));
      for (const item of more) byId.set(item.id, item);
      return { items: [...byId.values()], result: undefined };
    });
  }
}

const FETCH_LOG_KEEP = 300;

export class Store {
  readonly dir: string;
  readonly candidates: Collection<Candidate>;
  readonly pairings: Collection<Pairing>;
  readonly priorities: Collection<Priority>;
  readonly reviews: Collection<ReviewRecord>;
  readonly meetings: Collection<Meeting>;
  readonly fetchLog: Collection<FetchLogEntry>;

  constructor(dir: string) {
    this.dir = dir;
    this.candidates = new Collection(join(dir, "candidates.json"));
    this.pairings = new Collection(join(dir, "pairings.json"));
    this.priorities = new Collection(join(dir, "priorities.json"));
    this.reviews = new Collection(join(dir, "reviews.json"));
    this.meetings = new Collection(join(dir, "meetings.json"));
    this.fetchLog = new Collection(join(dir, "fetch-log.json"));
  }

  get siteDir(): string {
    return join(this.dir, "site");
  }

  async snapshot(): Promise<MoneySnapshot | undefined> {
    return readJson<MoneySnapshot | undefined>(join(this.dir, "money.json"), undefined);
  }

  async saveSnapshot(snapshot: MoneySnapshot): Promise<void> {
    await writeTextAtomic(join(this.dir, "money.json"), JSON.stringify(snapshot) + "\n");
  }

  async transcript(meetingId: string): Promise<Row[] | undefined> {
    let raw: string;
    try {
      raw = await readFile(join(this.dir, "transcripts", `${meetingId}.tsv`), "utf-8");
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") return undefined;
      throw err;
    }
    return parseTsv(raw);
  }

  async saveTranscript(meetingId: string, rows: Row[]): Promise<void> {
    await writeTextAtomic(join(this.dir, "transcripts", `${meetingId}.tsv`), toTsv(rows));
  }

  async logFetch(entry: Omit<FetchLogEntry, "id" | "at"> & { at?: string }): Promise<void> {
    const at = entry.at ?? new Date().toISOString();
    const full: FetchLogEntry = { ...entry, at, id: `${at}-${randomBytes(3).toString("hex")}` };
    await this.fetchLog.update((items) => ({ items: [...items, full].slice(-FETCH_LOG_KEEP), result: undefined }));
  }

  async lastRefreshAt(): Promise<Date | undefined> {
    const refreshes = (await this.fetchLog.all()).filter((e) => e.ok && (e.source === "refresh" || e.source === "seed"));
    const last = refreshes[refreshes.length - 1];
    return last ? new Date(last.at) : undefined;
  }

  async listTranscriptIds(): Promise<string[]> {
    try {
      return (await readdir(join(this.dir, "transcripts"))).filter((f) => f.endsWith(".tsv")).map((f) => f.slice(0, -4));
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
      throw err;
    }
  }
}

export function parseTsv(raw: string): Row[] {
  const rows: Row[] = [];
  for (const line of raw.split("\n")) {
    const tab = line.indexOf("\t");
    if (tab < 0) continue;
    rows.push({ stamp: line.slice(0, tab), text: line.slice(tab + 1).split(/\s+/).filter(Boolean).join(" ") });
  }
  return rows;
}

export function toTsv(rows: Row[]): string {
  return rows.map((r) => `${r.stamp}\t${r.text}\n`).join("");
}
