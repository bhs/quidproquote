// The static site: the card list and one page per card, written under <data dir>/site. It is regenerated
// every time a pairing is approved, unpublished or published again (and at start), so what is served is what
// the records say. A card's own file is replaced by a plain notice file when the card is unpublished.

import { mkdir, readdir, readFile, rm } from "node:fs/promises";
import { join } from "node:path";
import { cardPageHtml, indexHtml, noticeHtml } from "./render.ts";
import { writeTextAtomic } from "./store.ts";
import type { Store } from "./store.ts";

export interface SiteSummary {
  published: number;
  unpublished: number;
}

export async function publishSite(store: Store): Promise<SiteSummary> {
  const pairings = (await store.pairings.all()).sort((a, b) => a.n - b.n);
  const cardsDir = join(store.siteDir, "cards");
  await mkdir(cardsDir, { recursive: true });
  const live = pairings.filter((p) => p.status === "published");
  const gone = pairings.filter((p) => p.status === "unpublished");
  const notice = noticeHtml();
  for (const p of live) {
    await writeTextAtomic(join(cardsDir, `${p.slug}.html`), cardPageHtml(p.card, p.publishedAt));
    await rm(join(cardsDir, `${p.slug}.gone.html`), { force: true });
  }
  for (const p of gone) {
    await writeTextAtomic(join(cardsDir, `${p.slug}.gone.html`), notice);
    await rm(join(cardsDir, `${p.slug}.html`), { force: true });
  }
  const known = new Set(pairings.flatMap((p) => [`${p.slug}.html`, `${p.slug}.gone.html`]));
  for (const file of await readdir(cardsDir)) {
    if (!known.has(file) && file.endsWith(".html")) await rm(join(cardsDir, file), { force: true });
  }
  await writeTextAtomic(join(store.siteDir, "index.html"), indexHtml(live.map((p) => ({ card: p.card, publishedAt: p.publishedAt }))));
  return { published: live.length, unpublished: gone.length };
}

export interface StaticPage {
  status: number;
  html: string;
}

/** The static file for a card's address: its page, the notice where it was unpublished, or nothing. */
export async function readCardPage(store: Store, slug: string): Promise<StaticPage | undefined> {
  const base = join(store.siteDir, "cards", slug);
  for (const [suffix, status] of [[".html", 200], [".gone.html", 410]] as const) {
    try {
      return { status, html: await readFile(base + suffix, "utf-8") };
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
    }
  }
  return undefined;
}

export async function readIndexPage(store: Store): Promise<string> {
  return readFile(join(store.siteDir, "index.html"), "utf-8");
}
