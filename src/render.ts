// The static pages: the card list, one page per card, and the plain notice shown where a card was unpublished.
// A card has three zones: the money in (one line per committee, never summed) with the donor's priority beneath
// it, the official, and the official's exact words. Beneath them sit the reading, the doubt badge and the
// sources. Nothing on a card says why anyone said or gave anything.

import { escapeHtml as E, marked } from "./text.ts";
import type { Card, CommitteeLine, FilingRow, Statement } from "./types.ts";

export const NO_CAUSE = "No cause is claimed.";
export const SITE_NAME = "Pairing cards";

export const CSS = `
body{font:15px/1.45 system-ui,sans-serif;margin:0;background:#f4f1ea;color:#222}
main{max-width:1180px;margin:0 auto;padding:1rem}
header.site,footer.site{max-width:1180px;margin:0 auto;padding:.6rem 1rem;font-size:.9rem}
header.site a{font-weight:700;color:#222;text-decoration:none}
h1{font-size:1.4rem} .lede{max-width:70ch}
ol.cards{list-style:none;padding:0;margin:0}
.card{background:#fff;border:1px solid #bbb;border-radius:8px;margin:1.2rem 0;padding:.8rem 1rem}
.card h2,.card h1{font-size:1.1rem;margin:.1rem 0 .3rem}
.card h2 a{color:inherit}
.zones{display:grid;grid-template-columns:1.25fr .6fr 1fr;gap:.9rem}
@media(max-width:820px){.zones{grid-template-columns:1fr}}
.zone h3{font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:#555;margin:.1rem 0 .4rem}
.money{border-left:4px solid #2f6f4f;padding:.2rem .6rem;margin:.4rem 0;background:#f3f8f5}
.money .amt{font-weight:700}
.money.outside{border-color:#a33;background:#fbf1f1}
.small{font-size:.85rem;color:#444}
.bubble{background:#eef2fb;border:1px solid #9fb3e0;border-radius:14px;padding:.6rem .8rem;margin-top:.8rem}
.bubble blockquote,.quote{margin:.4rem 0;padding:0}
.official{text-align:center;align-self:center}
.official .name{font-size:1.15rem;font-weight:700}
.quote{border-left:4px solid #777;padding-left:.7rem;font-family:Georgia,serif}
mark{background:#ffe066;padding:0 .1em}
.strip{margin-top:.8rem;background:#f7f7f7;border:1px dashed #999;padding:.5rem .7rem}
.badge{display:inline-block;border-radius:3px;padding:.05rem .45rem;font-weight:700;font-size:.8rem;color:#fff;margin-right:.4rem}
.badge.low{background:#2f6f4f}.badge.medium{background:#b07a00}.badge.high{background:#a33}
.sources{margin-top:.6rem;font-size:.85rem;color:#333;border-top:1px solid #ddd;padding-top:.4rem}
table.filings{border-collapse:collapse;width:100%;font-size:.8rem;margin:.3rem 0}
table.filings th,table.filings td{border:1px solid #cfd8d2;padding:.15rem .35rem;text-align:left;vertical-align:top}
table.filings td.num{text-align:right;white-space:nowrap}
tr.not-counted td{color:#666;font-style:italic}
details{margin:.4rem 0} summary{cursor:pointer}
ul.cuerows{list-style:none;padding:0;margin:.3rem 0}
ul.cuerows li{font-family:ui-monospace,monospace;font-size:.82rem}
.permalink{font-size:.85rem;color:#444;margin:.1rem 0 .6rem}
`;

export function layout(title: string, body: string, extraCss = ""): string {
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${E(title)}</title><style>${CSS}${extraCss}</style></head><body>
<header class="site"><a href="/">${E(SITE_NAME)}</a> <span class="small">San Francisco officials, a donor's own priority and the money</span></header>
<main>
${body}
</main>
<footer class="site small"><a href="/">All cards</a> &middot; <a href="/admin">Maintainer sign-in</a></footer>
</body></html>
`;
}

function range(first: string, last: string): string {
  return first + (last !== first ? ` to ${last}` : "");
}

function filingTable(m: CommitteeLine): string {
  const line = (kind: string, r: FilingRow, counted: boolean): string =>
    `<tr${counted ? "" : ' class="not-counted"'}><td>${E(kind)}</td><td>${E(r.contributionDate)}</td>` +
    `<td>${E(r.filingId)} (v${E(r.version)})</td><td>${E(r.filingDate)}</td><td class="num">${E(r.amountText)}</td>` +
    `<td>${E(r.giver)}</td></tr>`;
  const rows = [
    ...m.rows.map((r) => line("Schedule A", r, true)),
    ...m.repeats.map((r) => line("24-hour report repeating a Schedule A row (not counted)", r, false)),
    ...m.h24Only.map((r) => line("24-hour report with no Schedule A row yet (apart, not in the total)", r, false)),
  ].join("");
  return `<table class="filings"><thead><tr><th>Kind</th><th>Contribution date</th><th>Filing id (version)</th>` +
    `<th>Filing date</th><th>Amount</th><th>Giver as filed</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function committeeBlock(m: CommitteeLine, open: boolean): string {
  const notes: string[] = [];
  if (m.h24Only.length) notes.push(`Also on 24-hour reports with no Schedule A row yet, apart and not in the total: ${m.h24OnlyTotalText}.`);
  if (m.repeats.length) notes.push(`${m.repeats.length} 24-hour repeat${m.repeats.length === 1 ? "" : "s"} of a Schedule A row, listed in the filings, not counted.`);
  const extra = notes.map((n) => `<div class="small"><i>${E(n)}</i></div>`).join("");
  const filings = open
    ? filingTable(m)
    : `<details><summary class="small">The ${m.rows.length + m.repeats.length + m.h24Only.length} filing row${m.rows.length + m.repeats.length + m.h24Only.length === 1 ? "" : "s"}, by filing date</summary>${filingTable(m)}</details>`;
  return `<div class="money"><span class="amt">${E(m.scheduleATotalText)}</span> Schedule A to <b>${E(m.committee)}</b> ` +
    `<span class="small">(filer ${E(m.filer)})</span>` +
    `<div class="small">${E(m.kind)}; ${m.rows.length} row${m.rows.length === 1 ? "" : "s"}, ${E(range(m.first, m.last))}</div>` +
    `<div class="small">Giver${m.givers.length === 1 ? "" : "s"} as filed: ${E(m.givers.join("; "))}</div>${extra}${filings}</div>`;
}

function donorGroups(statements: Statement[]): { url: string; pageDate: string; retrieved: string; kind: string; items: Statement[] }[] {
  const groups: { url: string; pageDate: string; retrieved: string; kind: string; items: Statement[] }[] = [];
  for (const s of statements) {
    const g = groups.find((x) => x.url === s.url);
    if (g) g.items.push(s);
    else groups.push({ url: s.url, pageDate: s.pageDate, retrieved: s.retrieved, kind: s.kind, items: [s] });
  }
  return groups;
}

const quoted = (text: string): string => (text.startsWith('"') ? text : `"${text}"`);

export interface CardMeta {
  publishedAt: string;
  /** True on a card's own page: filings open and the credit's caption rows shown. */
  detail: boolean;
}

export function cardHtml(card: Card, meta: CardMeta): string {
  const T = card.highlight;
  const permalink = `/cards/${card.slug}`;
  const heading = meta.detail
    ? `<h1>${E(card.title)}</h1>`
    : `<h2><a href="${E(permalink)}">${E(card.title)}</a></h2>`;
  const committees = card.money.committees.map((m) => committeeBlock(m, meta.detail)).join("");
  const outside = card.money.outsideSpending.length
    ? card.money.outsideSpending.map((o) =>
        `<div class="money outside"><b>Outside spending, kept apart</b> (form 496; not a gift to any committee above): ` +
        `${E(o.spender)}, ${E(o.stance)}, ${E(o.amountText)}, ${o.filings.length} filing${o.filings.length === 1 ? "" : "s"}, ` +
        `${E(range(o.first, o.last))}</div>`).join("")
    : `<div class="money outside"><b>Outside spending, kept apart:</b> <span class="small">no form 496 report naming this official ` +
      `was filed by a committee the family's names take.</span></div>`;
  const bubble = [`<div class="bubble"><b>${E(card.donor.name)}: stated priority</b><div class="small"><i>${E(card.donor.tie.text)}</i></div>`];
  for (const g of donorGroups(card.donor.statements)) {
    for (const s of g.items) {
      bubble.push(`<div class="small">${marked(s.section, T)}</div><blockquote>${marked(quoted(s.text), T)}</blockquote>`);
    }
    bubble.push(`<div class="small">${E(g.kind)}; ${g.pageDate ? `page dated ${E(g.pageDate)}` : "page undated"}; ` +
      `<a href="${E(g.url)}">source page</a>; retrieved ${E(g.retrieved)}</div>`);
  }
  bubble.push("</div>");
  const q = card.quote;
  const credit = card.speakerCredit;
  const cueRows = credit.cueRows.map((r) => `<li><code>${E(r.stamp)}</code> ${E(r.text)}</li>`).join("");
  const outsideCredit = credit.outside.map((o) => `<li>Outside the transcript: <a href="${E(o.url)}">${E(o.url)}</a>: ${E(o.says)}</li>`).join("");
  const creditBody = `<ul class="cuerows">${cueRows}</ul><p class="small">${E(credit.support)}</p>` +
    (outsideCredit ? `<ul class="small">${outsideCredit}</ul>` : "");
  const creditBlock = meta.detail
    ? `<div class="strip"><b>How the transcript supports that credit</b>${creditBody}</div>`
    : `<details><summary class="small">How the transcript supports that credit</summary>${creditBody}</details>`;
  const s = card.sources;
  const filings = s.filingIds.length ? E(s.filingIds.join(", ")) : "none";
  return `<article class="card" id="card-${E(card.slug)}">${heading}
<div class="permalink">Permanent link: <a href="${E(permalink)}">${E(permalink)}</a> &middot; Published ${E(meta.publishedAt)}</div>
<div class="zones">
<section class="zone"><h3>Money in, then the donor's priority</h3>${committees}
<div class="small">One line per receiving committee; totals are never summed across committees.</div>${outside}${bubble.join("")}</section>
<section class="zone official"><h3>The official</h3><div class="name">${E(card.official.name)}</div><div>${E(card.official.role)}</div>
<p class="small">Named as a San Francisco official from the city's roster.</p></section>
<section class="zone"><h3>The official's exact words</h3><div class="quote">${marked(`"${q.text}"`, T)}</div>
<div class="small">${E(q.meeting)}, ${E(q.date)}, transcript time ${E(range(q.firstStamp, q.lastStamp))}</div>
<div class="small"><a href="${E(q.transcriptUrl)}">Legistar caption transcript</a>, retrieved ${E(q.retrieved)}. Wording is the transcript's; it was not checked against the recording.</div></section>
</div>
<div class="strip"><span class="badge ${credit.doubt}">SPEAKER-CREDIT DOUBT: ${E(credit.doubt.toUpperCase())}</span><b>Reading, not a finding.</b>
In common: ${E(card.reading.inCommon)} Where they differ: ${E(card.reading.differs)} ${E(card.reading.cause)}
Two things shown side by side for a reader to check; nothing here says why anyone said or gave anything, and the order of the dates is not an explanation.
<div class="small">Highlighted: words literally in both the quote and the donor's words (${T.length ? T.map((t) => `"${E(t)}"`).join(", ") : "none of substance, so nothing is highlighted"}). Credit: ${E(credit.reason)}</div></div>
${creditBlock}
<div class="small">${E(card.money.moneyNote)} ${E(card.donor.tie.note)}</div>
<div class="sources"><b>Sources:</b> <a href="${E(s.transcript)}">transcript</a> (${E(q.meeting)}, ${E(q.date)}); donor page${s.donorPages.length === 1 ? "" : "s"}: ${
    s.donorPages.map((u) => `<a href="${E(u)}">${E(u.split("//").pop()!.split("/")[0])}</a>`).join(", ")
  }; filing ids, <a href="${E(s.datasetUrl)}">Transactions dataset</a>: ${filings}; money retrieved ${E(s.moneyRetrieved)}.</div>
</article>`;
}

export interface PublishedCard {
  card: Card;
  publishedAt: string;
}

export function indexHtml(cards: PublishedCard[]): string {
  const body = cards.length
    ? `<ol class="cards">\n${cards.map((c) => `<li>${cardHtml(c.card, { publishedAt: c.publishedAt, detail: false })}</li>`).join("\n")}\n</ol>`
    : `<p>No pairing is published yet.</p>`;
  return layout(
    "Pairing cards: San Francisco officials, a donor's priority and the money",
    `<h1>Pairing cards</h1><p class="lede">One card per pairing. The official's exact words from the city's caption transcript, ` +
      `the donor's own stated priority and the money the donor gave through committees tied to the official are shown side by side. ` +
      `Each card is a reading, not a finding: ${E(NO_CAUSE.toLowerCase())} Nothing here says why anyone said or gave anything.</p>${body}`,
  );
}

export function cardPageHtml(card: Card, publishedAt: string): string {
  return layout(`${card.title}: pairing card`, `<p class="small"><a href="/">&larr; All cards</a></p>${cardHtml(card, { publishedAt, detail: true })}`);
}

export function noticeHtml(): string {
  return layout(
    "This card is not published",
    `<h1>This card is not published</h1><p>The pairing that was shown at this address has been taken down by the maintainer. ` +
      `It is not shown here.</p><p><a href="/">See the cards that are published</a></p>`,
  );
}
