import assert from "node:assert/strict";
import { test } from "node:test";
import { DataSf, familyClause, lit } from "../src/datasf.ts";
import { Fetcher, FetchError, userAgent } from "../src/fetcher.ts";
import { parseCalendar, parseRss } from "../src/legistar.ts";
import { loadFamilies } from "../src/reference.ts";
import { startScheduler } from "../src/scheduler.ts";
import { tempStore } from "./helpers.ts";

const noSleep = async () => undefined;

test("every request carries a user agent that says who is asking and how to reach them", async () => {
  const seen: Record<string, string>[] = [];
  const fetcher = new Fetcher({
    contactEmail: "maintainer@example.org", pauseMs: 0, sleep: noSleep,
    fetchImpl: async (_url, init) => {
      seen.push(init?.headers as Record<string, string>);
      return new Response("ok");
    },
  });
  assert.equal(await fetcher.text("https://example.org/"), "ok");
  assert.ok(seen[0]["User-Agent"].includes("maintainer@example.org"));
  assert.equal(seen[0]["User-Agent"], userAgent("maintainer@example.org"));
});

test("a request that keeps failing raises an error, and is not turned into an empty answer", async () => {
  let calls = 0;
  const fetcher = new Fetcher({
    contactEmail: "maintainer@example.org", pauseMs: 0, sleep: noSleep,
    fetchImpl: async () => {
      calls++;
      return new Response("busy", { status: 503 });
    },
  });
  await assert.rejects(fetcher.text("https://example.org/"), FetchError);
  assert.equal(calls, 3);
});

test("DataSF answering with something that is not a list of rows is an error", async () => {
  const fetcher = new Fetcher({
    contactEmail: "maintainer@example.org", pauseMs: 0, sleep: noSleep, retries: 1,
    fetchImpl: async () => new Response('{"error":true,"message":"nope"}'),
  });
  await assert.rejects(new DataSf(fetcher).query("pitq-e56w", {}), /unexpected DataSF reply/);
});

test("a family becomes a SoQL clause on its name patterns and FPPC ids", async () => {
  const chamber = (await loadFamilies()).find((f) => f.key === "sf-chamber")!;
  const clause = familyClause("transaction_last_name", chamber, "committee_id");
  assert.ok(clause.includes("upper(transaction_last_name) like '%SAN FRANCISCO FORWARD%'"));
  assert.ok(clause.includes("committee_id in ('891575','1290133')"));
  assert.equal(lit("O'Neil"), "'O''Neil'");
});

test("the calendar rows and the Granicus feed items are read for body, date and transcript id", () => {
  const page = `<table><tr><td>Board of Supervisors</td><td>7/14/2026</td><td>x</td><td><a href="Transcript.aspx?ID1=52849">Transcript</a></td></tr>
    <tr><td>Some Other Body</td><td>no date</td><td>x</td><td>y</td></tr></table>`;
  const rows = parseCalendar(page);
  assert.equal(rows.length, 1);
  assert.deepEqual([rows[0].body, rows[0].date, rows[0].transcriptId], ["Board of Supervisors", "2026-07-14", "52849"]);
  const rss = `<item><title>Board of Supervisors dated Tuesday, 14 July 2026</title><link>https://x/?clip_id=52849</link></item>`;
  assert.deepEqual(parseRss(rss, "Board of Supervisors").map((r) => [r.date, r.transcriptId]), [["2026-07-14", "52849"]]);
});

test("the scheduler runs the fetch when none was read in the last day, and not just after one", async () => {
  const fresh = await tempStore();
  await fresh.logFetch({ source: "seed", what: "fixtures", ok: true, detail: "" });
  let freshRuns = 0;
  const a = startScheduler({ store: fresh, firstDelayMs: 5, log: () => undefined, run: async () => { freshRuns++; } });
  const empty = await tempStore();
  let emptyRuns = 0;
  const b = startScheduler({ store: empty, firstDelayMs: 5, log: () => undefined, run: async () => { emptyRuns++; } });
  await new Promise((resolve) => setTimeout(resolve, 150));
  a.stop();
  b.stop();
  assert.equal(freshRuns, 0);
  assert.equal(emptyRuns, 1);
});
