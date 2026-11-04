// Small text helpers: escaping, dollars, slugs and whole-word highlighting. The words of a quote or a donor are
// never rewritten: highlighting only adds tags around them.

const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };

export function escapeHtml(text: string): string {
  return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export function decodeEntities(text: string): string {
  return text.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (whole, body: string) => {
    if (body[0] === "#") {
      const code = body[1].toLowerCase() === "x" ? parseInt(body.slice(2), 16) : parseInt(body.slice(1), 10);
      return Number.isFinite(code) && code > 0 && code < 0x110000 ? String.fromCodePoint(code) : whole;
    }
    return NAMED[body.toLowerCase()] ?? whole;
  });
}

/** Tags removed, entities decoded, whitespace collapsed. */
export function plainText(markup: string): string {
  return decodeEntities(markup.replace(/<[^>]+>/g, " ")).split(/\s+/).filter(Boolean).join(" ");
}

export function dollars(value: number): string {
  const digits = Math.round(Math.abs(value)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return (value < 0 ? "-$" : "$") + digits;
}

export function slugify(text: string, max = 60): string {
  const slug = text
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug.slice(0, max).replace(/-+$/, "");
}

export function escapeRegex(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Whole-word, case-insensitive match of any term (longest first); null when there are no terms. */
export function termRegex(terms: string[]): RegExp | null {
  const clean = terms.map((t) => t.trim()).filter(Boolean);
  if (!clean.length) return null;
  const alternatives = [...clean].sort((a, b) => b.length - a.length).map(escapeRegex).join("|");
  return new RegExp(`(?<![A-Za-z0-9_])(?:${alternatives})(?![A-Za-z0-9_])`, "gi");
}

/** `text` escaped, with each literal occurrence of a term wrapped in <mark>. */
export function marked(text: string, terms: string[]): string {
  const rx = termRegex(terms);
  if (!rx) return escapeHtml(text);
  let out = "";
  let pos = 0;
  for (const m of text.matchAll(rx)) {
    const at = m.index ?? 0;
    out += escapeHtml(text.slice(pos, at)) + "<mark>" + escapeHtml(m[0]) + "</mark>";
    pos = at + m[0].length;
  }
  return out + escapeHtml(text.slice(pos));
}

export function hasTerm(text: string, term: string): boolean {
  const rx = termRegex([term]);
  return rx ? rx.test(text) : false;
}

/** Typographic quotes and dashes straightened, whitespace collapsed (the donor's words as stored). */
export function squash(text: string): string {
  return text
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201c\u201d]/g, '"')
    .replace(/[\u2013\u2014]/g, "-")
    .replace(/\u00a0/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
}

export function today(now: Date = new Date()): string {
  return now.toISOString().slice(0, 10);
}

export function isIsoDate(text: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return false;
  const d = new Date(text + "T00:00:00Z");
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === text;
}

export function isStamp(text: string): boolean {
  return /^\d\d:\d\d:\d\d$/.test(text);
}
