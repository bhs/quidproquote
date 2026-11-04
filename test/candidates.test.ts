import assert from "node:assert/strict";
import { before, test } from "node:test";
import { generateCandidates, stampsOverlap } from "../src/candidates.ts";
import { isFunded, pairMoney } from "../src/money.ts";
import { loadFamilies, loadRoster } from "../src/reference.ts";
import type { Context } from "../src/review.ts";
import type { Candidate, Meeting, Priority, Row } from "../src/types.ts";
import { fixtureRows, fixtureSnapshot, seededContext } from "./helpers.ts";
import { readFileSync } from "node:fs";
import { fixturePath } from "../src/reference.ts";

let ctx: Context;
let candidates: Candidate[];

before(async () => {
  ({ ctx } = await seededContext());
  candidates = await ctx.store.candidates.all();
});

test("the rules proposed the passages of four shown pairings; the fifth was found by hand", async () => {
  const pairings = await ctx.store.pairings.all();
  const origin = (slug: string) => candidates.find((c) => c.id === pairings.find((p) => p.slug === slug)!.candidateId)?.origin;
  assert.equal(origin("lurie-chamber-muni"), "rules");
  assert.equal(origin("lurie-poa-budget"), "rules");
  assert.equal(origin("dorsey-poa-inclusionary"), "rules");
  assert.equal(origin("walton-seiu1021-charter"), "rules");
  assert.equal(origin("mahmood-gfc-prop-j"), "maintainer");
});

test("passages the rules proposed that no review took wait in the queue, with exact caption lines and context", () => {
  const pending = candidates.filter((c) => c.status === "pending");
  assert.ok(pending.length > 0);
  for (const c of pending) {
    assert.ok(c.lines.some((l) => l.kind === "passage"));
    assert.ok(c.lines.length > c.lines.filter((l) => l.kind === "passage").length, "context lines come with the passage");
  }
});

test("a candidate is made only for a donor that gave to a committee tied to the official", async () => {
  const roster = await loadRoster();
  const families = await loadFamilies();
  const meetings = JSON.parse(readFileSync(fixturePath("meetings.json"), "utf-8")) as Meeting[];
  const priorities = JSON.parse(readFileSync(fixturePath("priorities.json"), "utf-8")) as Priority[];
  const transcripts = new Map<string, Row[]>(meetings.map((m) => [m.id, fixtureRows(m.id)]));
  const input = { snapshot: fixtureSnapshot(), families, roster, priorities, meetings, transcripts, now: "2026-11-01T00:00:00Z" };
  const all = generateCandidates(input);
  assert.ok(all.length > 0);
  for (const c of all) {
    assert.ok(isFunded(pairMoney(input.snapshot, families, c.official, c.familyKey)), `${c.official} and ${c.familyName} have no Schedule A money`);
  }
  const none = generateCandidates({ ...input, snapshot: { ...input.snapshot, familyRows: {} } });
  assert.deepEqual(none, []);
});

test("stamp ranges overlap when they share caption time", () => {
  assert.ok(stampsOverlap("00:04:36", "00:04:51", "00:04:36", "00:05:01"));
  assert.ok(!stampsOverlap("00:01:00", "00:02:00", "00:03:00", "00:04:00"));
});
