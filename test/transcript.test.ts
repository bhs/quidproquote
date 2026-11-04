import assert from "node:assert/strict";
import { test } from "node:test";
import { Doc, candidatePassages, creditTier, extractQuote, findRegions, parseTranscriptHtml } from "../src/transcript.ts";
import { loadRoster } from "../src/reference.ts";
import { fixtureRows } from "./helpers.ts";

test("caption rows are read from a Legistar transcript page", () => {
  const page = "<tr><td>00:00:14</td><td>&gt;&gt; GOOD   AFTERNOON.</td></tr><tr><td>00:00:15</td><td>WELCOME TO THE MEETING</td></tr>";
  assert.deepEqual(parseTranscriptHtml(page), [
    { stamp: "00:00:14", text: ">> GOOD AFTERNOON." },
    { stamp: "00:00:15", text: "WELCOME TO THE MEETING" },
  ]);
});

test("a quote is the caption words exactly, cut at the phrases asked for", () => {
  const rows = fixtureRows("52849");
  const q = extractQuote(rows, "01:47:19", "01:48:25", "COLLEAGUES, I WILL RESPECTFULLY BE VOTING NO", "MAKING HOUSING PRODUCTION FEASIBLE.");
  assert.ok(q.text.startsWith("COLLEAGUES, I WILL RESPECTFULLY BE VOTING NO ON THE PROPOSED AMENDMENT"));
  assert.ok(q.text.endsWith("MAKING HOUSING PRODUCTION FEASIBLE."));
  assert.equal(q.firstStamp, "01:47:19");
  assert.throws(() => extractQuote(rows, "01:47:19", "01:48:25", "WORDS THAT ARE NOT THERE"), /not found/);
  assert.throws(() => extractQuote(rows, "99:00:00", "99:00:01"), /no caption rows/);
});

test("roster cues open the Mayor's remarks and the members' turns", async () => {
  const roster = await loadRoster();
  const doc = new Doc(fixtureRows("52849"));
  const regions = findRegions(doc, roster);
  const mayor = regions.find((r) => r.official === "Daniel Lurie");
  assert.equal(mayor?.kind, "mayor-opening");
  assert.equal(mayor?.cueStamp, "00:02:28");
  const dorsey = regions.find((r) => r.official === "Matt Dorsey" && r.cueStamp === "01:47:15");
  assert.ok(dorsey, "the cue 'SUPERVISOR DORSEY' at 01:47:15 opens a region");
  assert.ok(regions.some((r) => r.official === "Shamann Walton" && r.cueStamp === "02:36:50"));
});

test("a passage that hits the donor's phrase is proposed with a doubt level", async () => {
  const roster = await loadRoster();
  const doc = new Doc(fixtureRows("52849"));
  const dorsey = findRegions(doc, roster).find((r) => r.official === "Matt Dorsey" && r.cueStamp === "01:47:15")!;
  const passages = candidatePassages(doc, dorsey, { anchor: [], topic: ["inclusionary"] });
  assert.ok(passages.length >= 1);
  assert.equal(passages[0].tier, "topic");
  assert.deepEqual(passages[0].topicHits, ["INCLUSIONARY"]);
  const [doubt, why] = creditTier(doc, dorsey, passages[0].start);
  assert.equal(doubt, "low");
  assert.ok(why[0].includes("SUPERVISOR DORSEY"));
});

test("a passage with no measure name or phrase is never proposed", async () => {
  const roster = await loadRoster();
  const doc = new Doc(fixtureRows("52849"));
  const region = findRegions(doc, roster)[0];
  assert.deepEqual(candidatePassages(doc, region, { anchor: [], topic: [] }), []);
});
