import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { readFileSync } from "node:fs";
import type { Config } from "../src/config.ts";
import { fixturePath, loadFamilies, loadRoster } from "../src/reference.ts";
import type { Context } from "../src/review.ts";
import { seedFixtures } from "../src/seed.ts";
import type { SeedSummary } from "../src/seed.ts";
import { Store, parseTsv } from "../src/store.ts";
import type { MoneySnapshot, Row } from "../src/types.ts";

export async function tempStore(): Promise<Store> {
  return new Store(await mkdtemp(join(tmpdir(), "pairing-site-")));
}

export async function seededContext(): Promise<{ ctx: Context; summary: SeedSummary }> {
  const ctx: Context = { store: await tempStore(), roster: await loadRoster(), families: await loadFamilies() };
  return { ctx, summary: await seedFixtures(ctx) };
}

export const testConfig = (dir: string): Config => ({
  port: 0, dataDir: dir, adminToken: "test-token", contactEmail: "tester@example.org", dataSfAppToken: "", refreshDelayMs: 0,
});

export const fixtureSnapshot = (): MoneySnapshot => JSON.parse(readFileSync(fixturePath("money.json"), "utf-8")) as MoneySnapshot;

export const fixtureRows = (meetingId: string): Row[] => parseTsv(readFileSync(fixturePath(`transcripts/${meetingId}.tsv`), "utf-8"));

/** What the Pairings end to end instances showed, for checking the cards against. */
export const SHOWN = [
  { slug: "lurie-chamber-muni", official: "Daniel Lurie", donor: "San Francisco Chamber of Commerce", meeting: "Board of Supervisors", date: "2026-07-14",
    from: "00:03:46", to: "00:03:59", starts: "MUNI WEEKEND RIDERSHIP SURPASSED", ends: "THAN IN 2025.", doubt: "low",
    committees: ["Mayor Lurie's Yes on H Committee|$499,000|4|2"] },
  { slug: "lurie-poa-budget", official: "Daniel Lurie", donor: "San Francisco Police Officers Association", meeting: "Board of Supervisors", date: "2026-07-14",
    from: "00:04:36", to: "00:05:01", starts: "I'M CONFIDENT THAT THE UPCOMING BUDGET", ends: "$642 MILLION DEFICIT.", doubt: "low",
    committees: ["Mayor Lurie's Yes on D, E & F Committee|$10,000|1|1"] },
  { slug: "dorsey-poa-inclusionary", official: "Matt Dorsey", donor: "San Francisco Police Officers Association", meeting: "Board of Supervisors", date: "2026-07-14",
    from: "01:47:19", to: "01:48:25", starts: "COLLEAGUES, I WILL RESPECTFULLY BE VOTING NO", ends: "MAKING HOUSING PRODUCTION FEASIBLE.", doubt: "low",
    committees: ["Matt Dorsey for Supervisor 2022|$500|1|0", "Matt Dorsey for DCCC Member 2024 Officeholder Committee|$7,500|3|1"] },
  { slug: "mahmood-gfc-prop-j", official: "Bilal Mahmood", donor: "Govern For California", meeting: "Budget and Finance Committee", date: "2026-07-15",
    from: "02:52:31", to: "02:52:42", starts: "THIS MEASURE GIVES SAN FRANCISCO VOTERS", ends: "DECADES AGO.", doubt: "high",
    committees: ["Bilal Mahmood for DCCC Member 2024|$10,500|4|4", "Bilal Mahmood for Supervisor 2024|$7,500|15|0"] },
  { slug: "walton-seiu1021-charter", official: "Shamann Walton", donor: "SEIU Local 1021", meeting: "Board of Supervisors", date: "2026-07-14",
    from: "02:39:58", to: "02:40:56", starts: "COLLEAGUES I AM ALSO REQUESTING", ends: "RESIDENTS OF SAN FRANCISCO.", doubt: "low",
    committees: ["Committee to Elect Shamann Walton for SF Board of Education 2012|$500|1|0", "Shamann Walton for School Board 2014|$500|1|0"] },
];
