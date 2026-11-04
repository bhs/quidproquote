import assert from "node:assert/strict";
import { test } from "node:test";
import { extractMeasures, measureTerms, splitPhrases, validatePriority } from "../src/priorities.ts";
import { loadFamilies } from "../src/reference.ts";
import { ValidationError } from "../src/validation.ts";

test("measure names are read from the donor's words", () => {
  assert.deepEqual(extractMeasures("Prop H would introduce a parcel tax"), ["H"]);
  assert.deepEqual(extractMeasures("Proposition D - Changes to Ballot Measure Process - Vote NO"), ["D"]);
  assert.deepEqual(extractMeasures("Props D, E and F are the Mayor's three"), ["D", "E", "F"]);
  assert.deepEqual(extractMeasures("The Chamber supports public transit"), []);
  assert.deepEqual(measureTerms(["H"]), ["Proposition H", "Prop H", "Prop. H", "Measure H"]);
  assert.deepEqual(splitPhrases("Muni, parcel tax;\nMuni"), ["Muni", "parcel tax"]);
});

test("a priority save missing words, source, URL or date is refused with each reason", async () => {
  const families = await loadFamilies();
  try {
    validatePriority({ family: "sf-chamber" }, families);
    assert.fail("should have been refused");
  } catch (err) {
    assert.ok(err instanceof ValidationError);
    const all = err.problems.join(" | ");
    assert.match(all, /words are missing/);
    assert.match(all, /source is missing/);
    assert.match(all, /URL is missing/);
    assert.match(all, /date is missing/);
  }
  assert.throws(() => validatePriority({ family: "sf-chamber", text: "x", kind: "page", url: "not a url", pageDate: "10/08/2026" }, families), ValidationError);
});

test("a complete priority is kept with its measures, phrases and a retrieval date", async () => {
  const families = await loadFamilies();
  const p = validatePriority(
    { family: "sf-chamber", text: "The Chamber supports Prop H\u2019s parcel tax.", kind: "voter guide on the organisation's own site",
      url: "https://sfchamber.com/november-2026-voter-guide/", pageDate: "2026-10-08", phrases: "Muni" },
    families, new Date("2026-10-30T12:00:00Z"),
  );
  assert.equal(p.retrieved, "2026-10-30");
  assert.deepEqual(p.measures, ["H"]);
  assert.deepEqual(p.phrases, ["Muni"]);
  assert.ok(p.text.includes("Prop H's"), "typographic quotes are straightened");
});
