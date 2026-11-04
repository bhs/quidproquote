import assert from "node:assert/strict";
import { createServer } from "node:http";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { after, before, test } from "node:test";
import { createApp } from "../src/app.ts";
import { COOKIE, makeSession } from "../src/auth.ts";
import type { Context } from "../src/review.ts";
import type { Store } from "../src/store.ts";
import { seededContext, testConfig } from "./helpers.ts";

let ctx: Context;
let server: Server;
let base: string;
let logs: Record<string, unknown>[] = [];
let cookie = "";

const listen = (app: ReturnType<typeof createApp>): Promise<Server> =>
  new Promise((resolve) => {
    const s = createServer(app);
    s.listen(0, "127.0.0.1", () => resolve(s));
  });
const urlOf = (s: Server): string => `http://127.0.0.1:${(s.address() as AddressInfo).port}`;

const get = (path: string, headers: Record<string, string> = {}) => fetch(base + path, { redirect: "manual", headers });
const post = (path: string, fields: Record<string, string | string[]>, withCookie = true) => {
  const body = new URLSearchParams();
  for (const [k, v] of Object.entries(fields)) for (const x of Array.isArray(v) ? v : [v]) body.append(k, x);
  return fetch(base + path, {
    method: "POST", redirect: "manual", body,
    headers: withCookie ? { cookie: `${COOKIE}=${cookie}` } : {},
  });
};
const authed = (path: string) => get(path, { cookie: `${COOKIE}=${cookie}` });

before(async () => {
  ({ ctx } = await seededContext());
  logs = [];
  server = await listen(createApp({ config: testConfig(ctx.store.dir), ctx, log: (o) => logs.push(o) }));
  base = urlOf(server);
});

after(() => {
  server.close();
});

test("the front page answers 200 with the cards, and the request is logged as one JSON line", async () => {
  const res = await get("/", { "x-request-id": "front-page-1" });
  assert.equal(res.status, 200);
  const html = await res.text();
  assert.equal((html.match(/<article class="card"/g) ?? []).length, 5);
  assert.ok(html.includes("Maintainer sign-in"));
  const line = logs.find((l) => l.request_id === "front-page-1" && l.path === "/");
  assert.ok(line);
  assert.equal(line.status, 200);
  assert.equal(line.method, "GET");
  assert.equal(typeof line.duration_ms, "number");
  assert.equal(line.level, "info");
});

test("each card has its own page at a permanent address; an unknown address is a 404", async () => {
  const res = await get("/cards/lurie-chamber-muni");
  assert.equal(res.status, 200);
  assert.ok((await res.text()).includes("Daniel Lurie"));
  assert.equal((await get("/cards/no-such-card")).status, 404);
  assert.equal((await get("/cards/..%2f..%2fetc")).status, 404);
});

test("the maintainer's pages need the sign-in", async () => {
  for (const path of ["/admin", "/admin/priorities", "/admin/candidates/anything"]) {
    const res = await get(path);
    assert.equal(res.status, 303, path);
    assert.equal(res.headers.get("location"), "/admin/login");
  }
  const unpublish = await post("/admin/pairings/lurie-chamber-muni/unpublish", {}, false);
  assert.equal(unpublish.status, 303);
  assert.equal((await ctx.store.pairings.get("lurie-chamber-muni"))?.status, "published");
});

test("a wrong token is refused and the right one sets a signed cookie", async () => {
  const wrong = await post("/admin/login", { token: "nope" }, false);
  assert.equal(wrong.status, 401);
  assert.equal(wrong.headers.get("set-cookie"), null);
  const right = await post("/admin/login", { token: "test-token" }, false);
  assert.equal(right.status, 303);
  const set = right.headers.getSetCookie()[0];
  assert.ok(set.startsWith(`${COOKIE}=`) && set.includes("HttpOnly") && set.includes("SameSite=Strict"));
  cookie = decodeURIComponent(set.split(";")[0].slice(COOKIE.length + 1));
  const forged = await get("/admin", { cookie: `${COOKIE}=${Date.now() + 100000}.deadbeef` });
  assert.equal(forged.status, 303);
});

test("the queue shows exact caption lines with their context", async () => {
  const res = await authed("/admin");
  assert.equal(res.status, 200);
  const html = await res.text();
  assert.ok(html.includes("Passages to review"));
  const pending = (await ctx.store.candidates.all()).filter((c) => c.status === "pending");
  assert.ok(pending.length > 0);
  const first = pending[0];
  for (const line of first.lines.filter((l) => l.kind === "passage").slice(0, 2)) {
    assert.ok(html.includes(`<code>${line.stamp}</code>`));
  }
  assert.ok(html.includes('class="l before"') && html.includes('class="l passage"') && html.includes('class="l after"'));
  assert.ok(html.includes("Unpublish"));
});

test("the priority form refuses a save missing words, source, URL or date", async () => {
  const res = await post("/admin/priorities", { family: "sf-chamber" });
  assert.equal(res.status, 422);
  const html = await res.text();
  assert.ok(html.includes("words are missing") && html.includes("source is missing"));
  assert.ok(html.includes("URL is missing") && html.includes("date is missing"));
  assert.equal((await ctx.store.priorities.all()).some((p) => p.family === "sf-chamber" && p.text === ""), false);
});

test("a complete priority is saved and its measure names are looked for in the transcripts", async () => {
  const count = (await ctx.store.priorities.all()).length;
  const res = await post("/admin/priorities", {
    family: "sf-chamber", text: "The Chamber opposes Prop J, the transfer tax on foreclosures.", kind: "voter guide on the organisation's own site",
    url: "https://sfchamber.com/november-2026-voter-guide/", pageDate: "2026-10-08", phrases: "transfer tax",
  });
  assert.equal(res.status, 200);
  assert.ok((await res.text()).includes("Saved."));
  assert.equal((await ctx.store.priorities.all()).length, count + 1);
});

test("approving a passage publishes a card and rebuilds the card list", async () => {
  const pending = (await ctx.store.candidates.all()).find((c) => c.status === "pending" && c.origin === "rules" && c.cueLines.length)!;
  const page = await authed(`/admin/candidates/${pending.id}`);
  assert.equal(page.status, 200);
  assert.ok((await page.text()).includes("Approve as a pairing"));
  const fields = {
    subject: "A reviewed subject", from: pending.firstStamp, to: pending.lastStamp, beginAt: "", endAt: "",
    cueStamps: pending.cueLines.map((r) => r.stamp).join(", "), support: "The cue names the speaker as about to speak.",
    doubt: pending.doubt, doubtReason: pending.doubtWhy.join("; "), priorityIds: pending.priorityIds, highlight: "",
    overlap: "Same subject.", stance: "Not comparable on the text.", moneyNote: "", outside: "", slug: "",
  };
  const refused = await post(`/admin/candidates/${pending.id}/approve`, { ...fields, subject: "" });
  assert.equal(refused.status, 422);
  assert.ok((await refused.text()).includes("The subject is missing."));
  const ok = await post(`/admin/candidates/${pending.id}/approve`, fields);
  assert.equal(ok.status, 303);
  const pairings = await ctx.store.pairings.all();
  assert.equal(pairings.length, 6);
  const made = pairings.find((p) => p.card.subject === "A reviewed subject")!;
  assert.equal((await get(`/cards/${made.slug}`)).status, 200);
  const index = await (await get("/")).text();
  assert.equal((index.match(/<article class="card"/g) ?? []).length, 6);
  assert.equal((await ctx.store.candidates.get(pending.id))?.status, "approved");
});

test("unpublishing regenerates the pages: the address shows a plain notice and the list drops the card", async () => {
  const res = await post("/admin/pairings/lurie-chamber-muni/unpublish", {});
  assert.equal(res.status, 303);
  const gone = await get("/cards/lurie-chamber-muni");
  assert.equal(gone.status, 410);
  const notice = await gone.text();
  assert.ok(notice.includes("This card is not published"));
  assert.ok(!notice.includes("Daniel Lurie"));
  const index = await (await get("/")).text();
  assert.ok(!index.includes("/cards/lurie-chamber-muni"));
  assert.equal((index.match(/<article class="card"/g) ?? []).length, 5);
  const back = await post("/admin/pairings/lurie-chamber-muni/republish", {});
  assert.equal(back.status, 303);
  assert.equal((await get("/cards/lurie-chamber-muni")).status, 200);
});

test("an unhandled error is logged with the request id, the message and the stack", async () => {
  const broken = Object.create(ctx.store) as Store;
  Object.defineProperty(broken, "candidates", {
    value: { all: async () => { throw new Error("disk exploded"); } },
  });
  const errLogs: Record<string, unknown>[] = [];
  const s = await listen(createApp({
    config: testConfig(ctx.store.dir), ctx: { ...ctx, store: broken }, log: (o) => errLogs.push(o),
  }));
  try {
    const res = await fetch(urlOf(s) + "/admin", {
      headers: { cookie: `${COOKIE}=${makeSession("test-token")}`, "x-request-id": "boom-1" },
    });
    assert.equal(res.status, 500);
    const line = errLogs.find((l) => l.level === "error");
    assert.ok(line);
    assert.equal(line.request_id, "boom-1");
    assert.equal(line.error, "disk exploded");
    assert.equal(typeof line.stack, "string");
    assert.ok((line.stack as string).includes("disk exploded"));
    const access = errLogs.find((l) => l.path === "/admin" && l.status === 500);
    assert.equal(access?.request_id, "boom-1");
  } finally {
    s.close();
  }
});
