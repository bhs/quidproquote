// The HTTP side: the static card pages are served from disk; the maintainer's pages are rendered on request
// behind the sign-in. Every request is logged as one JSON line when its response is complete, and every
// unhandled error as one more line with the same request id, the message and the stack.

import { randomUUID } from "node:crypto";
import type { IncomingMessage, ServerResponse } from "node:http";
import { clearedCookie, makeSession, readCookie, sessionCookie, sessionValid, COOKIE, tokenMatches } from "./auth.ts";
import { defaultsFor, toReviewInput, valuesFromForm } from "./forms.ts";
import { logLine } from "./log.ts";
import type { LogFn } from "./log.ts";
import { candidatePage, loginPage, plainError, plainNotFound, prioritiesPage, queuePage } from "./pages.ts";
import { validatePriority } from "./priorities.ts";
import type { PriorityForm } from "./priorities.ts";
import { approveCandidate, rejectCandidate, republishPairing, unpublishPairing } from "./review.ts";
import type { Context } from "./review.ts";
import type { Scheduler } from "./scheduler.ts";
import { readCardPage, readIndexPage } from "./site.ts";
import { addCandidates } from "./refresh.ts";
import type { Config } from "./config.ts";
import { ValidationError } from "./validation.ts";

export interface AppDeps {
  config: Config;
  ctx: Context;
  log?: LogFn;
  scheduler?: Scheduler;
}

const MAX_BODY = 256 * 1024;

class Redirect {
  readonly to: string;
  readonly headers: Record<string, string>;

  constructor(to: string, headers: Record<string, string> = {}) {
    this.to = to;
    this.headers = headers;
  }
}

async function readForm(req: IncomingMessage): Promise<URLSearchParams> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    if (size > MAX_BODY) throw new ValidationError(["That form is too large."]);
    chunks.push(chunk as Buffer);
  }
  return new URLSearchParams(Buffer.concat(chunks).toString("utf-8"));
}

function sameOrigin(req: IncomingMessage): boolean {
  const origin = req.headers.origin;
  if (!origin) return true;
  try {
    return new URL(origin).host === req.headers.host;
  } catch {
    return false;
  }
}

export function createApp(deps: AppDeps): (req: IncomingMessage, res: ServerResponse) => void {
  const { config, ctx } = deps;
  const log = deps.log ?? logLine;

  const send = (res: ServerResponse, status: number, html: string, headers: Record<string, string> = {}): void => {
    res.writeHead(status, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", ...headers });
    res.end(html);
  };

  async function admin(req: IncomingMessage, path: string, secure: boolean): Promise<{ status: number; html: string; headers?: Record<string, string> } | Redirect> {
    const method = req.method ?? "GET";
    const signedIn = sessionValid(readCookie(req.headers.cookie, COOKIE), config.adminToken);

    if (path === "/admin/login") {
      if (method === "GET") return { status: 200, html: loginPage() };
      if (method === "POST") {
        if (!sameOrigin(req)) return { status: 403, html: loginPage("That request came from another site.") };
        const form = await readForm(req);
        if (!tokenMatches(form.get("token") ?? "", config.adminToken)) {
          return { status: 401, html: loginPage("That token is not right.") };
        }
        return new Redirect("/admin", { "Set-Cookie": sessionCookie(makeSession(config.adminToken), secure) });
      }
    }
    if (path === "/admin/logout" && method === "POST") return new Redirect("/admin/login", { "Set-Cookie": clearedCookie() });
    if (!signedIn) return new Redirect("/admin/login");
    if (method === "POST" && !sameOrigin(req)) return { status: 403, html: plainError() };

    const store = ctx.store;
    const queue = async (notice?: string) => {
      const candidates = await store.candidates.all();
      return {
        status: 200,
        html: queuePage({
          pending: candidates.filter((c) => c.status === "pending"), rejected: candidates.filter((c) => c.status === "rejected").length,
          pairings: await store.pairings.all(), fetchLog: await store.fetchLog.all(), nextRun: deps.scheduler?.nextRunAt(),
          running: deps.scheduler?.running() ?? false, notice,
        }),
      };
    };

    if (path === "/admin" && method === "GET") return queue(new URL(req.url ?? "/", "http://x").searchParams.get("notice") ?? undefined);

    let m = /^\/admin\/candidates\/([a-z0-9-]+)$/.exec(path);
    if (m && method === "GET") {
      const c = await store.candidates.get(m[1]);
      if (!c) return { status: 404, html: plainNotFound() };
      const priorities = await store.priorities.all();
      return { status: 200, html: candidatePage(c, priorities, defaultsFor(c, priorities), []) };
    }
    m = /^\/admin\/candidates\/([a-z0-9-]+)\/approve$/.exec(path);
    if (m && method === "POST") {
      const c = await store.candidates.get(m[1]);
      if (!c) return { status: 404, html: plainNotFound() };
      const values = valuesFromForm(await readForm(req));
      try {
        const pairing = await approveCandidate(ctx, c.id, toReviewInput(values));
        return new Redirect(`/admin?notice=${encodeURIComponent(`Published ${pairing.card.title} at /cards/${pairing.slug}`)}`);
      } catch (err) {
        if (!(err instanceof ValidationError)) throw err;
        return { status: 422, html: candidatePage(c, await store.priorities.all(), values, err.problems) };
      }
    }
    m = /^\/admin\/candidates\/([a-z0-9-]+)\/reject$/.exec(path);
    if (m && method === "POST") {
      try {
        await rejectCandidate(ctx, m[1]);
      } catch (err) {
        if (!(err instanceof ValidationError)) throw err;
        return { status: 422, html: plainError() };
      }
      return new Redirect("/admin?notice=" + encodeURIComponent("Passage rejected."));
    }
    m = /^\/admin\/pairings\/([a-z0-9-]+)\/(unpublish|republish)$/.exec(path);
    if (m && method === "POST") {
      try {
        const done = m[2] === "unpublish" ? await unpublishPairing(ctx, m[1]) : await republishPairing(ctx, m[1]);
        return new Redirect("/admin?notice=" + encodeURIComponent(`${done.card.title} is ${done.status === "published" ? "published again" : "unpublished; its address now shows a notice"}.`));
      } catch (err) {
        if (!(err instanceof ValidationError)) throw err;
        return { status: 422, html: plainError() };
      }
    }
    if (path === "/admin/priorities") {
      if (method === "GET") return { status: 200, html: prioritiesPage(await store.priorities.all(), ctx.families, {}, [], "") };
      if (method === "POST") {
        const form = await readForm(req);
        const values: PriorityForm = Object.fromEntries(["family", "text", "kind", "url", "pageDate", "retrieved", "section", "phrases"].map((k) => [k, form.get(k) ?? ""]));
        try {
          const priority = validatePriority(values, ctx.families, ctx.now?.());
          await store.priorities.put(priority);
          const added = await addCandidates(ctx, new Date().toISOString());
          const saved = `Saved. ${added ? `${added} new passage${added === 1 ? "" : "s"} now wait${added === 1 ? "s" : ""} in the review queue.` : "No new passage in the transcripts on disk matches it."}`;
          return { status: 200, html: prioritiesPage(await store.priorities.all(), ctx.families, {}, [], saved) };
        } catch (err) {
          if (!(err instanceof ValidationError)) throw err;
          return { status: 422, html: prioritiesPage(await store.priorities.all(), ctx.families, values, err.problems, "") };
        }
      }
    }
    return { status: 404, html: plainNotFound() };
  }

  async function route(req: IncomingMessage, res: ServerResponse, path: string): Promise<void> {
    const method = req.method ?? "GET";
    const secure = req.headers["x-forwarded-proto"] === "https";
    if (path.startsWith("/admin")) {
      const out = await admin(req, path, secure);
      if (out instanceof Redirect) {
        res.writeHead(303, { Location: out.to, "Cache-Control": "no-store", ...out.headers });
        res.end();
      } else send(res, out.status, out.html, out.headers);
      return;
    }
    if (method !== "GET" && method !== "HEAD") return send(res, 405, plainNotFound(), { Allow: "GET, HEAD" });
    if (path === "/") return send(res, 200, await readIndexPage(ctx.store), { "Cache-Control": "no-cache" });
    const m = /^\/cards\/([a-z0-9-]+)$/.exec(path);
    if (m) {
      const page = await readCardPage(ctx.store, m[1]);
      if (page) return send(res, page.status, page.html, { "Cache-Control": "no-cache" });
    }
    send(res, 404, plainNotFound());
  }

  return (req, res) => {
    const started = process.hrtime.bigint();
    const incoming = req.headers["x-request-id"];
    const requestId = (Array.isArray(incoming) ? incoming[0] : incoming)?.slice(0, 100) || randomUUID();
    const path = (req.url ?? "/").split("?")[0];
    res.setHeader("X-Request-Id", requestId);
    res.on("finish", () => {
      log({
        level: "info", msg: `${req.method} ${path} ${res.statusCode}`, request_id: requestId, method: req.method, path,
        status: res.statusCode, duration_ms: Number(process.hrtime.bigint() - started) / 1e6,
      });
    });
    route(req, res, path).catch((err: unknown) => {
      const e = err instanceof Error ? err : new Error(String(err));
      log({ level: "error", msg: "unhandled error", request_id: requestId, error: e.message, stack: e.stack });
      if (!res.headersSent) send(res, 500, plainError());
      else res.end();
    });
  };
}
