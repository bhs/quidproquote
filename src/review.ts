// What a person does in the queue: approve a candidate as a pairing (which builds and stores its card and
// regenerates the static pages), reject it, unpublish a published pairing, or publish it again. Each change is
// kept as a review record, and the static site is rebuilt before the call returns.

import { buildCard } from "./cards.ts";
import { publishSite } from "./site.ts";
import { slugify, today } from "./text.ts";
import { ValidationError } from "./validation.ts";
import type { Store } from "./store.ts";
import type { Family, Official, Pairing, ReviewInput } from "./types.ts";

export interface Context {
  store: Store;
  roster: Official[];
  families: Family[];
  now?: () => Date;
}

const nowOf = (ctx: Context): Date => (ctx.now ?? (() => new Date()))();

async function record(ctx: Context, decision: "approved" | "rejected" | "unpublished" | "republished", candidateId: string, pairingId?: string, note?: string) {
  const at = nowOf(ctx).toISOString();
  await ctx.store.reviews.put({ id: `${at}-${decision}-${pairingId ?? candidateId}`, at, decision, candidateId, pairingId, note });
}

export async function approveCandidate(ctx: Context, candidateId: string, input: ReviewInput): Promise<Pairing> {
  const { store } = ctx;
  const candidate = await store.candidates.get(candidateId);
  if (!candidate) throw new ValidationError(["That candidate does not exist."]);
  if (candidate.status !== "pending") throw new ValidationError([`That candidate was already ${candidate.status}.`]);
  const official = ctx.roster.find((o) => o.name === candidate.official);
  const family = ctx.families.find((f) => f.key === candidate.familyKey);
  if (!official || !family) throw new Error(`candidate ${candidateId} names an official or a donor that is not on the roster`);
  const meeting = await store.meetings.get(candidate.meetingId);
  const rows = await store.transcript(candidate.meetingId);
  const snapshot = await store.snapshot();
  if (!meeting || !rows) throw new Error(`the transcript of meeting ${candidate.meetingId} is not on disk`);
  if (!snapshot) throw new Error("no campaign finance snapshot is on disk yet");
  const priorities = await store.priorities.all();
  const publishedAt = today(nowOf(ctx));

  const pairing = await store.pairings.update((items) => {
    const wanted = input.slug?.trim() ?? "";
    if (wanted && !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(wanted)) throw new ValidationError(["The address may hold only lower-case letters, digits and hyphens."]);
    const taken = new Set(items.map((p) => p.slug));
    if (wanted && taken.has(wanted)) throw new ValidationError([`The address ${wanted} is already used by another card.`]);
    let slug = wanted;
    if (!slug) {
      const base = slugify(`${official.name} ${family.key} ${input.subject}`, 70) || "pairing";
      slug = base;
      for (let n = 2; taken.has(slug); n++) slug = `${base}-${n}`;
    }
    const n = items.reduce((max, p) => Math.max(max, p.n), 0) + 1;
    const card = buildCard({ slug, review: input, official, family, meeting, rows, snapshot, families: ctx.families, priorities });
    const made: Pairing = { id: slug, n, slug, candidateId, status: "published", publishedAt, review: input, card };
    return { items: [...items, made], result: made };
  });
  await store.candidates.put({ ...candidate, status: "approved", decidedAt: nowOf(ctx).toISOString() });
  await record(ctx, "approved", candidateId, pairing.id);
  await publishSite(store);
  return pairing;
}

export async function rejectCandidate(ctx: Context, candidateId: string, note = ""): Promise<void> {
  const candidate = await ctx.store.candidates.get(candidateId);
  if (!candidate) throw new ValidationError(["That candidate does not exist."]);
  if (candidate.status !== "pending") throw new ValidationError([`That candidate was already ${candidate.status}.`]);
  await ctx.store.candidates.put({ ...candidate, status: "rejected", decidedAt: nowOf(ctx).toISOString() });
  await record(ctx, "rejected", candidateId, undefined, note.trim() || undefined);
}

async function setStatus(ctx: Context, pairingId: string, status: "published" | "unpublished"): Promise<Pairing> {
  const at = nowOf(ctx);
  const changed = await ctx.store.pairings.update((items) => {
    const found = items.find((p) => p.id === pairingId);
    if (!found) throw new ValidationError(["That pairing does not exist."]);
    if (found.status === status) throw new ValidationError([`That pairing is already ${status}.`]);
    const next: Pairing = status === "unpublished"
      ? { ...found, status, unpublishedAt: today(at) }
      : { ...found, status, publishedAt: today(at), unpublishedAt: undefined };
    return { items: items.map((p) => (p.id === pairingId ? next : p)), result: next };
  });
  await record(ctx, status === "unpublished" ? "unpublished" : "republished", changed.candidateId, changed.id);
  await publishSite(ctx.store);
  return changed;
}

export const unpublishPairing = (ctx: Context, pairingId: string): Promise<Pairing> => setStatus(ctx, pairingId, "unpublished");
export const republishPairing = (ctx: Context, pairingId: string): Promise<Pairing> => setStatus(ctx, pairingId, "published");
