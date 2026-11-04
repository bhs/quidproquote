import assert from "node:assert/strict";
import { test } from "node:test";
import { committeeLines, familyOf, outsideSpending, pairMoney, relationOf } from "../src/money.ts";
import { loadFamilies } from "../src/reference.ts";
import { SHOWN, fixtureSnapshot } from "./helpers.ts";

const FAMILY: Record<string, string> = {
  "lurie-chamber-muni": "sf-chamber", "lurie-poa-budget": "sf-poa", "dorsey-poa-inclusionary": "sf-poa",
  "mahmood-gfc-prop-j": "govern-for-california", "walton-seiu1021-charter": "seiu-1021",
};

test("each shown pairing's money is per committee, counted once, with 24-hour repeats listed apart", async () => {
  const families = await loadFamilies();
  const snap = fixtureSnapshot();
  for (const shown of SHOWN) {
    const lines = committeeLines(pairMoney(snap, families, shown.official, FAMILY[shown.slug]));
    const got = lines.map((l) => `${l.committee}|${l.scheduleATotalText}|${l.rows.length}|${l.repeats.length}`).sort();
    assert.deepEqual(got, [...shown.committees].sort(), shown.slug);
  }
});

test("a 24-hour report repeating a Schedule A row is not in the total", async () => {
  const families = await loadFamilies();
  const [line] = committeeLines(pairMoney(fixtureSnapshot(), families, "Daniel Lurie", "sf-chamber"));
  assert.equal(line.scheduleATotal, 499000);
  assert.equal(line.rows.length, 4);
  assert.equal(line.repeats.length, 2);
  assert.equal(line.h24Only.length, 0);
  assert.deepEqual(line.rows.map((r) => r.filingId), ["216870148", "216863528", "217514736", "217719664"]);
  assert.equal(line.rows[0].contributionDate, "2026-03-09");
  assert.equal(line.rows[0].version, "3");
  assert.equal(line.rows[0].filingDate, "2026-06-09");
});

test("no outside spending is found for the five shown pairings, and none is mixed into the gifts", async () => {
  const families = await loadFamilies();
  const snap = fixtureSnapshot();
  for (const shown of SHOWN) assert.deepEqual(outsideSpending(snap, families, shown.official, FAMILY[shown.slug]), [], shown.slug);
});

test("a donor is recognised by the FPPC id first and by name second", async () => {
  const families = await loadFamilies();
  assert.deepEqual(familyOf(families, "SF Forward", "891575"), ["sf-chamber", "id"]);
  assert.deepEqual(familyOf(families, "SEIU Local 1021"), ["seiu-1021", "name"]);
  assert.deepEqual(familyOf(families, "Somebody Else"), [null, null]);
});

test("a committee's tie to the official is read from the data's own type and its name", () => {
  for (const c of fixtureSnapshot().committees) assert.equal(relationOf(c.filerType, c.filerName), c.relation, c.filerName);
});
