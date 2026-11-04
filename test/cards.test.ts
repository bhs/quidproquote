import assert from "node:assert/strict";
import { before, test } from "node:test";
import { approveCandidate } from "../src/review.ts";
import { isVerbatim } from "../src/transcript.ts";
import { ValidationError } from "../src/validation.ts";
import type { Context } from "../src/review.ts";
import type { Pairing } from "../src/types.ts";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { SHOWN, fixtureRows, seededContext } from "./helpers.ts";

let ctx: Context;
let pairings: Pairing[];

before(async () => {
  ({ ctx } = await seededContext());
  pairings = await ctx.store.pairings.all();
});

const page = (slug: string) => readFile(join(ctx.store.siteDir, "cards", `${slug}.html`), "utf-8");

test("the five shown pairings are published as cards", () => {
  assert.deepEqual(pairings.map((p) => p.slug).sort(), SHOWN.map((s) => s.slug).sort());
  assert.ok(pairings.every((p) => p.status === "published"));
});

for (const shown of SHOWN) {
  test(`${shown.slug}: the words, meeting, speaker credit, priority and money`, async () => {
    const p = pairings.find((x) => x.slug === shown.slug)!;
    const { card } = p;
    assert.ok(card.quote.text.startsWith(shown.starts));
    assert.ok(card.quote.text.endsWith(shown.ends));
    assert.ok(isVerbatim(fixtureRows(shown.slug.startsWith("mahmood") ? "52853" : "52849"), card.quote.text));
    assert.equal(card.quote.meeting, shown.meeting);
    assert.equal(card.quote.date, shown.date);
    assert.equal(card.quote.firstStamp, shown.from);
    assert.equal(card.quote.lastStamp, shown.to);
    assert.equal(card.official.name, shown.official);
    assert.equal(card.donor.name, shown.donor);
    assert.equal(card.speakerCredit.doubt, shown.doubt);
    assert.ok(card.speakerCredit.cueRows.length > 0 && card.speakerCredit.support.length > 0);
    assert.ok(card.donor.statements.every((s) => s.url.startsWith("https://") && s.retrieved === "2026-10-30" && s.pageDate));
    assert.deepEqual(
      card.money.committees.map((c) => `${c.committee}|${c.scheduleATotalText}|${c.rows.length}|${c.repeats.length}`).sort(),
      [...shown.committees].sort(),
    );
    assert.equal(card.reading.cause, "No cause is claimed.");
  });

  test(`${shown.slug}: the static page shows the three zones, the badge, the permanent link and the published date`, async () => {
    const html = await page(shown.slug);
    const p = pairings.find((x) => x.slug === shown.slug)!;
    assert.ok(html.includes("Money in, then the donor's priority"));
    assert.ok(html.includes("The official's exact words"));
    assert.ok(html.includes(`>${shown.official}<`));
    assert.ok(html.includes(`SPEAKER-CREDIT DOUBT: ${shown.doubt.toUpperCase()}`));
    assert.ok(html.includes(`/cards/${shown.slug}`));
    assert.ok(html.includes(`Published ${p.publishedAt}`));
    assert.ok(html.includes(`transcript time ${shown.from} to ${shown.to}`));
    assert.ok(html.includes("Outside spending, kept apart"));
    assert.ok(html.includes("<mark>") === (p.card.highlight.length > 0));
    assert.ok(html.includes("Filing id (version)"));
    assert.ok(html.includes("retrieved 2026-10-30"));
    assert.ok(html.includes("never summed across committees"));
    assert.ok(html.includes("No cause is claimed."));
  });
}

test("committee totals are never added together on any card or on the list", async () => {
  const index = await readFile(join(ctx.store.siteDir, "index.html"), "utf-8");
  assert.ok(!index.includes("$8,000"), "Dorsey: $500 + $7,500");
  assert.ok(!index.includes("$18,000"), "Mahmood: $10,500 + $7,500");
  assert.ok(index.includes("$499,000") && index.includes("$7,500") && index.includes("$10,500"));
});

test("highlighted words are marked where they are literally in the quote and the donor's words", async () => {
  const html = await page("lurie-chamber-muni");
  assert.ok(html.includes("<mark>MUNI</mark>"));
  assert.ok(html.includes("<mark>Muni</mark>"));
});

test("a card is refused when its words, stamps, highlights or doubt do not hold", async () => {
  const pending = (await ctx.store.candidates.all()).find((c) => c.status === "pending" && c.origin === "rules");
  assert.ok(pending, "the queue holds a passage the rules proposed");
  const good = {
    subject: "A test subject", quote: { from: pending.firstStamp, to: pending.lastStamp, beginAt: "", endAt: "" },
    speaker: { cueStamps: pending.cueLines.map((r) => r.stamp), support: "The cue names the speaker.", doubt: pending.doubt, doubtReason: "Because.", outside: [] },
    priorityIds: pending.priorityIds, highlight: [], overlap: "Same subject.", stance: "Not comparable.", moneyNote: "",
  };
  const refuse = async (change: Record<string, unknown>, message: RegExp) => {
    await assert.rejects(
      approveCandidate(ctx, pending.id, { ...good, ...change } as never),
      (err: unknown) => err instanceof ValidationError && message.test(err.problems.join(" | ")),
    );
  };
  await refuse({ highlight: ["zebra"] }, /"zebra" is not in the quote/);
  await refuse({ quote: { ...good.quote, beginAt: "WORDS NOBODY SAID" } }, /not found/);
  await refuse({ speaker: { ...good.speaker, cueStamps: ["99:99:99"] } }, /is not in the transcript|not a caption stamp|99:99:99/);
  await refuse({ speaker: { ...good.speaker, doubt: "certain" } }, /low, medium or high/);
  await refuse({ subject: "" }, /subject is missing/);
  await refuse({ priorityIds: ["no-such-priority"] }, /does not exist/);
  assert.equal((await ctx.store.candidates.get(pending.id))?.status, "pending", "a refused review changes nothing");
});
