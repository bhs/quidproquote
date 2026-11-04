// The maintainer's pages: sign-in, the review queue, one candidate's review form, and the priority form. They
// are rendered on request; only the public cards are static files.

import { layout } from "./render.ts";
import { escapeHtml as E } from "./text.ts";
import type { ApproveValues } from "./forms.ts";
import type { PriorityForm } from "./priorities.ts";
import type { Candidate, Doubt, FetchLogEntry, Family, Pairing, Priority } from "./types.ts";

const ADMIN_CSS = `
nav.admin{display:flex;gap:1rem;align-items:center;margin:0 0 1rem;padding-bottom:.5rem;border-bottom:1px solid #ccc}
nav.admin form{margin-left:auto}
.cand{background:#fff;border:1px solid #bbb;border-radius:8px;margin:1rem 0;padding:.7rem 1rem}
.cand h3{margin:.1rem 0 .3rem;font-size:1rem}
.lines{border:1px solid #ddd;background:#fafafa;padding:.3rem .5rem;margin:.4rem 0;font-family:ui-monospace,monospace;font-size:.82rem}
.lines .l{display:flex;gap:.6rem;color:#777}
.lines .l.passage{color:#111;background:#fff3c4}
.lines .l code{flex:none}
form.stack label{display:block;margin:.6rem 0 .1rem;font-weight:600}
form.stack input[type=text],form.stack input[type=date],form.stack select,form.stack textarea{width:100%;max-width:60rem;box-sizing:border-box;font:inherit;padding:.25rem}
form.stack textarea{min-height:4.5rem}
form.stack .hint{font-weight:400;color:#555;font-size:.82rem}
button{font:inherit;padding:.3rem .8rem;cursor:pointer}
ul.errors{background:#fbe9e9;border:1px solid #c66;padding:.5rem 1.5rem;border-radius:4px}
p.ok{background:#e8f4ec;border:1px solid #6a9;padding:.4rem .8rem;border-radius:4px}
table.log{border-collapse:collapse;font-size:.82rem;width:100%}
table.log td,table.log th{border:1px solid #ddd;padding:.15rem .4rem;text-align:left;vertical-align:top}
td.bad{color:#a33;font-weight:700}
.inline{display:inline}
`;

function adminPage(title: string, body: string): string {
  return layout(`${title}: pairing cards maintainer`, `<nav class="admin"><b>Maintainer</b> <a href="/admin">Review queue</a> <a href="/admin/priorities">Donor priorities</a> <a href="/">Public cards</a>
<form method="post" action="/admin/logout"><button type="submit">Sign out</button></form></nav>${body}`, ADMIN_CSS);
}

function errorList(errors: string[]): string {
  return errors.length ? `<ul class="errors" role="alert">${errors.map((e) => `<li>${E(e)}</li>`).join("")}</ul>` : "";
}

export function loginPage(error = ""): string {
  return layout("Sign in: pairing cards maintainer", `<h1>Maintainer sign-in</h1>
${error ? errorList([error]) : ""}
<form method="post" action="/admin/login" class="stack"><label for="token">Admin token</label>
<input id="token" type="password" name="token" autocomplete="current-password" style="width:24rem;max-width:100%">
<p><button type="submit">Sign in</button></p></form>`, ADMIN_CSS);
}

const badge = (d: Doubt): string => `<span class="badge ${d}">SPEAKER-CREDIT DOUBT: ${d.toUpperCase()}</span>`;

function linesBlock(c: Candidate): string {
  return `<div class="lines">${c.lines.map((l) => `<div class="l ${l.kind}"><code>${E(l.stamp)}</code><span>${E(l.text)}</span></div>`).join("")}</div>`;
}

function cueBlock(c: Candidate): string {
  if (!c.cueLines.length) return `<p class="small">${E(c.doubtWhy.join("; "))}</p>`;
  return `<p class="small">Why this speaker: the cue "${E(c.cue)}" at ${E(c.cueStamp)}. ${E(c.doubtWhy.join("; "))}.</p>` +
    `<div class="lines">${c.cueLines.map((l) => `<div class="l"><code>${E(l.stamp)}</code><span>${E(l.text)}</span></div>`).join("")}</div>`;
}

function candidateSummary(c: Candidate, link: boolean): string {
  const hits = [...c.anchorHits, ...c.topicHits];
  return `<h3>${link ? `<a href="/admin/candidates/${E(c.id)}">` : ""}${E(c.official)} &times; ${E(c.familyName)}${link ? "</a>" : ""}</h3>
<p class="small">${E(c.body)}, ${E(c.date)}, transcript time ${E(c.firstStamp)} to ${E(c.lastStamp)}. ${badge(c.doubt)}
${hits.length ? `Hit: ${E(hits.join(", "))}.` : "Added by hand."} ${c.origin === "maintainer" ? "Found by the maintainer." : ""}</p>`;
}

export interface QueueData {
  pending: Candidate[];
  rejected: number;
  pairings: Pairing[];
  fetchLog: FetchLogEntry[];
  nextRun?: Date;
  running: boolean;
  notice?: string;
}

const doubtRank: Record<Doubt, number> = { low: 0, medium: 1, high: 2 };

export function queuePage(q: QueueData): string {
  const pending = [...q.pending].sort((a, b) => doubtRank[a.doubt] - doubtRank[b.doubt] || b.date.localeCompare(a.date) || a.firstStamp.localeCompare(b.firstStamp));
  const published = q.pairings.filter((p) => p.status === "published").sort((a, b) => a.n - b.n);
  const unpublished = q.pairings.filter((p) => p.status === "unpublished").sort((a, b) => a.n - b.n);
  const cards = pending.map((c) => `<article class="cand">${candidateSummary(c, true)}${linesBlock(c)}
<p class="small">Exact caption lines; the shaded ones are the passage, the others are context. <a href="/admin/candidates/${E(c.id)}">Review this passage</a></p></article>`).join("");
  const log = [...q.fetchLog].slice(-8).reverse().map((e) =>
    `<tr><td>${E(e.at.replace("T", " ").slice(0, 19))}</td><td>${E(e.source)}</td><td>${E(e.what)}</td><td class="${e.ok ? "" : "bad"}">${e.ok ? "ok" : "failed"}</td><td>${E(e.detail)}</td></tr>`).join("");
  return adminPage("Review queue", `<h1>Review queue</h1>
${q.notice ? `<p class="ok">${E(q.notice)}</p>` : ""}
<p><b>${pending.length}</b> passage${pending.length === 1 ? "" : "s"} waiting for review, <b>${published.length}</b> card${published.length === 1 ? "" : "s"} published, ${unpublished.length} unpublished, ${q.rejected} rejected.</p>
<h2>Passages to review</h2>
<p class="small">Each passage comes from a rule: a donor that gave to a committee tied to the official, a measure name or phrase from the donor's own words, and a stretch of a transcript where a cue names the official as about to speak. A hit is a proposal; it is not a finding.</p>
${cards || "<p>Nothing is waiting for review.</p>"}
<h2>Published cards</h2>
${published.length ? `<ul>${published.map((p) => `<li><a href="/cards/${E(p.slug)}">${E(p.card.title)}</a>, published ${E(p.publishedAt)}
<form class="inline" method="post" action="/admin/pairings/${E(p.id)}/unpublish"><button type="submit">Unpublish</button></form></li>`).join("")}</ul>` : "<p>No card is published.</p>"}
${unpublished.length ? `<h2>Unpublished cards</h2><ul>${unpublished.map((p) => `<li>${E(p.card.title)}, unpublished ${E(p.unpublishedAt ?? "")}
<form class="inline" method="post" action="/admin/pairings/${E(p.id)}/republish"><button type="submit">Publish again</button></form></li>`).join("")}</ul>` : ""}
<h2>Fetching</h2>
<p class="small">${q.running ? "A fetch is running now." : q.nextRun ? `The next daily fetch is due about ${E(q.nextRun.toISOString().replace("T", " ").slice(0, 16))} UTC.` : "No fetch is scheduled."}
Legistar and DataSF are read slowly, once a day.</p>
${log ? `<table class="log"><thead><tr><th>When (UTC)</th><th>Source</th><th>What</th><th>Result</th><th>Detail</th></tr></thead><tbody>${log}</tbody></table>` : "<p>Nothing fetched yet.</p>"}`);
}

export function candidatePage(c: Candidate, priorities: Priority[], values: ApproveValues, errors: string[]): string {
  const mine = priorities.filter((p) => p.family === c.familyKey);
  const checks = mine.map((p) =>
    `<label style="font-weight:400"><input type="checkbox" name="priorityIds" value="${E(p.id)}"${values.priorityIds.includes(p.id) ? " checked" : ""}> ${E(p.section || p.id)}: ${E(p.text.slice(0, 160))}${p.text.length > 160 ? "&hellip;" : ""} <span class="small">(${E(p.pageDate)})</span></label>`).join("");
  const input = (name: string, label: string, value: string, hint = "") =>
    `<label for="${name}">${label}${hint ? ` <span class="hint">${hint}</span>` : ""}</label><input type="text" id="${name}" name="${name}" value="${E(value)}">`;
  const area = (name: string, label: string, value: string, hint = "") =>
    `<label for="${name}">${label}${hint ? ` <span class="hint">${hint}</span>` : ""}</label><textarea id="${name}" name="${name}">${E(value)}</textarea>`;
  const doubtOptions = (["low", "medium", "high"] as const).map((d) => `<option value="${d}"${values.doubt === d ? " selected" : ""}>${d}</option>`).join("");
  const form = c.status === "pending" ? `${errorList(errors)}
<form method="post" action="/admin/candidates/${E(c.id)}/approve" class="stack">
<h2>Approve as a pairing</h2>
${input("subject", "Subject", values.subject, "what the two are about, in a few words")}
${input("slug", "Address of the card (optional)", values.slug, "lower-case letters, digits and hyphens; made from the names when left empty")}
${input("from", "Quote starts at caption stamp", values.from)}
${input("to", "Quote ends at caption stamp", values.to)}
${input("beginAt", "Begin at these words (optional)", values.beginAt, "must be in the first row exactly")}
${input("endAt", "End at these words (optional)", values.endAt, "must be in the last row exactly")}
${input("cueStamps", "Caption rows the speaker credit rests on", values.cueStamps, "stamps, separated by commas")}
${area("support", "How the transcript supports that credit", values.support)}
<label for="doubt">Doubt in the credit</label><select id="doubt" name="doubt">${doubtOptions}</select>
${area("doubtReason", "Why that doubt", values.doubtReason)}
${area("outside", "Sources outside the transcript (optional)", values.outside, "one per line: address | what it says")}
<label>The donor's priority the card shows</label>${checks || '<p class="small">This donor has no priority saved yet.</p>'}
${input("highlight", "Highlighted words", values.highlight, "words literally in both the quote and the donor's words, separated by commas")}
${area("overlap", "What the two have in common (my reading)", values.overlap)}
${area("stance", "Where they differ (my reading)", values.stance)}
${area("moneyNote", "Note on the committees (optional)", values.moneyNote)}
<p><button type="submit">Approve and publish</button></p>
</form>
<form method="post" action="/admin/candidates/${E(c.id)}/reject" class="stack"><button type="submit">Reject this passage</button></form>` : `<p>This passage was ${E(c.status)}.</p>`;
  return adminPage("Review a passage", `<p class="small"><a href="/admin">&larr; Review queue</a></p><h1>Review a passage</h1>
<article class="cand">${candidateSummary(c, false)}${linesBlock(c)}${cueBlock(c)}</article>${form}`);
}

export function prioritiesPage(priorities: Priority[], families: Family[], values: PriorityForm, errors: string[], saved: string): string {
  const options = families.map((f) => `<option value="${E(f.key)}"${values.family === f.key ? " selected" : ""}>${E(f.name)}</option>`).join("");
  const rows = [...priorities].sort((a, b) => a.family.localeCompare(b.family) || a.id.localeCompare(b.id)).map((p) =>
    `<tr><td>${E(families.find((f) => f.key === p.family)?.name ?? p.family)}</td><td>${E(p.section)}</td><td>${E(p.text)}</td>
<td>${E(p.kind)}<br><a href="${E(p.url)}">${E(p.url)}</a></td><td>${E(p.pageDate)}<br>retrieved ${E(p.retrieved)}</td>
<td>${E([...p.measures.map((m) => `Prop ${m}`), ...p.phrases].join(", "))}</td></tr>`).join("");
  return adminPage("Donor priorities", `<h1>Donor priorities</h1>
<p>A donor's priority in its own words, with where it was read. The measure names in the words and the phrases below are what the daily rules look for in the transcripts.</p>
${saved ? `<p class="ok">${E(saved)}</p>` : ""}${errorList(errors)}
<form method="post" action="/admin/priorities" class="stack">
<label for="family">Donor</label><select id="family" name="family"><option value="">Choose a donor</option>${options}</select>
<label for="text">The donor's words <span class="hint">exactly as the page gives them</span></label><textarea id="text" name="text">${E(values.text ?? "")}</textarea>
<label for="section">Section or heading <span class="hint">optional</span></label><input type="text" id="section" name="section" value="${E(values.section ?? "")}">
<label for="kind">Source <span class="hint">what kind of page it is, for example a voter guide on the organisation's own site</span></label><input type="text" id="kind" name="kind" value="${E(values.kind ?? "")}">
<label for="url">Source URL</label><input type="text" id="url" name="url" value="${E(values.url ?? "")}">
<label for="pageDate">Date of the page <span class="hint">YYYY-MM-DD</span></label><input type="text" id="pageDate" name="pageDate" value="${E(values.pageDate ?? "")}">
<label for="retrieved">Date you read it <span class="hint">YYYY-MM-DD; today when left empty</span></label><input type="text" id="retrieved" name="retrieved" value="${E(values.retrieved ?? "")}">
<label for="phrases">Phrases to look for <span class="hint">optional; separated by commas</span></label><input type="text" id="phrases" name="phrases" value="${E(values.phrases ?? "")}">
<p><button type="submit">Save priority</button></p></form>
<h2>Saved priorities (${priorities.length})</h2>
${rows ? `<table class="log"><thead><tr><th>Donor</th><th>Section</th><th>Words</th><th>Source</th><th>Dates</th><th>Looked for</th></tr></thead><tbody>${rows}</tbody></table>` : "<p>None saved yet.</p>"}`);
}

export function plainNotFound(): string {
  return layout("Not found", `<h1>Not found</h1><p>There is nothing at this address.</p><p><a href="/">See the cards</a></p>`);
}

export function plainError(): string {
  return layout("Something went wrong", `<h1>Something went wrong</h1><p>The error was logged. <a href="/">Back to the cards</a></p>`);
}

