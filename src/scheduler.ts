// An in-process daily scheduler. It wakes after a delay at start and then once a day, and runs the job only when
// the fetch log says the last refresh is more than a day old, so a restart does not fetch again.

import type { LogFn } from "./log.ts";
import type { Store } from "./store.ts";

export const DAY_MS = 24 * 60 * 60 * 1000;

export interface Scheduler {
  stop(): void;
  nextRunAt(): Date | undefined;
  running(): boolean;
}

export function startScheduler(options: {
  store: Store;
  run: () => Promise<unknown>;
  firstDelayMs: number;
  intervalMs?: number;
  log: LogFn;
}): Scheduler {
  const interval = options.intervalMs ?? DAY_MS;
  let timer: NodeJS.Timeout | undefined;
  let next: Date | undefined;
  let stopped = false;
  let running = false;

  const schedule = (delayMs: number): void => {
    if (stopped) return;
    next = new Date(Date.now() + delayMs);
    timer = setTimeout(() => void tick(), delayMs);
    timer.unref();
  };

  const tick = async (): Promise<void> => {
    if (stopped) return;
    try {
      const last = await options.store.lastRefreshAt();
      const dueIn = last ? last.getTime() + interval - Date.now() : 0;
      if (dueIn > 0) {
        schedule(dueIn);
        return;
      }
      running = true;
      options.log({ msg: "scheduled refresh starts" });
      await options.run();
      options.log({ msg: "scheduled refresh finished" });
    } catch (err) {
      options.log({ level: "error", msg: "scheduled refresh failed", error: (err as Error).message, stack: (err as Error).stack });
    } finally {
      running = false;
    }
    schedule(interval);
  };

  schedule(options.firstDelayMs);
  return {
    stop() {
      stopped = true;
      if (timer) clearTimeout(timer);
      next = undefined;
    },
    nextRunAt: () => next,
    running: () => running,
  };
}
