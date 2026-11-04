// The one way the site reads other people's servers: slowly (a pause between requests), with a user agent
// that says what the site is and how to reach its maintainer, retried a few times. A request that still fails
// raises FetchError. Nothing here turns a failed request into an empty answer.

export class FetchError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FetchError";
  }
}

export type FetchImpl = (url: string, init?: RequestInit) => Promise<Response>;

export interface FetcherOptions {
  contactEmail: string;
  pauseMs?: number;
  retries?: number;
  timeoutMs?: number;
  fetchImpl?: FetchImpl;
  sleep?: (ms: number) => Promise<void>;
  headers?: Record<string, string>;
}

export function userAgent(contactEmail: string): string {
  return `SFPairingCards/0.1 (research site on San Francisco officials and campaign money; slow, polite fetching; contact: ${contactEmail})`;
}

export class Fetcher {
  readonly userAgent: string;
  private readonly pauseMs: number;
  private readonly retries: number;
  private readonly timeoutMs: number;
  private readonly fetchImpl: FetchImpl;
  private readonly sleep: (ms: number) => Promise<void>;
  private readonly extraHeaders: Record<string, string>;
  private lastAt = 0;

  constructor(options: FetcherOptions) {
    if (!options.contactEmail) throw new Error("a fetcher needs a contact email for its user agent");
    this.userAgent = userAgent(options.contactEmail);
    this.pauseMs = options.pauseMs ?? 2000;
    this.retries = options.retries ?? 3;
    this.timeoutMs = options.timeoutMs ?? 60_000;
    this.fetchImpl = options.fetchImpl ?? ((url, init) => fetch(url, init));
    this.sleep = options.sleep ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
    this.extraHeaders = options.headers ?? {};
  }

  /** The text of a URL (a POST when `form` is given). Throws FetchError after the retries. */
  async text(url: string, form?: Record<string, string>, headers: Record<string, string> = {}): Promise<string> {
    let last = "";
    for (let attempt = 0; attempt < this.retries; attempt++) {
      const wait = this.lastAt + this.pauseMs - Date.now();
      if (wait > 0) await this.sleep(wait);
      this.lastAt = Date.now();
      try {
        const init: RequestInit = {
          method: form ? "POST" : "GET",
          headers: { "User-Agent": this.userAgent, ...this.extraHeaders, ...headers },
          body: form ? new URLSearchParams(form) : undefined,
          signal: AbortSignal.timeout(this.timeoutMs),
        };
        const res = await this.fetchImpl(url, init);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.text();
      } catch (err) {
        last = `${(err as Error).name}: ${(err as Error).message}`;
        await this.sleep(2000 * (attempt + 1));
      }
    }
    throw new FetchError(`${last} (${url.slice(0, 200)})`);
  }
}
