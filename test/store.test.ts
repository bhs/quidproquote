import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { test } from "node:test";
import { writeTextAtomic } from "../src/store.ts";
import { tempStore } from "./helpers.ts";

test("an atomic write leaves the file whole and no temporary file behind", async () => {
  const store = await tempStore();
  const file = join(store.dir, "nested", "a.json");
  await writeTextAtomic(file, '{"a":1}');
  await writeTextAtomic(file, '{"a":2}');
  assert.equal(await readFile(file, "utf-8"), '{"a":2}');
  assert.deepEqual(await readdir(join(store.dir, "nested")), ["a.json"]);
});

test("concurrent changes to one record file all survive", async () => {
  const store = await tempStore();
  await Promise.all(Array.from({ length: 25 }, (_, i) => store.reviews.put({
    id: `r${i}`, at: "2026-11-01T00:00:00Z", decision: "approved", candidateId: `c${i}`,
  })));
  assert.equal((await store.reviews.all()).length, 25);
});

test("the last successful refresh is read from the fetch log; a failed one does not count", async () => {
  const store = await tempStore();
  assert.equal(await store.lastRefreshAt(), undefined);
  await store.logFetch({ source: "refresh", what: "daily refresh", ok: false, detail: "failed", at: "2026-11-01T00:00:00.000Z" });
  assert.equal(await store.lastRefreshAt(), undefined);
  await store.logFetch({ source: "refresh", what: "daily refresh", ok: true, detail: "fine", at: "2026-11-02T00:00:00.000Z" });
  assert.equal((await store.lastRefreshAt())?.toISOString(), "2026-11-02T00:00:00.000Z");
});
