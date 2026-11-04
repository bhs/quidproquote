// Starts the site: regenerates the static pages from the records, serves them with the maintainer's pages, and
// starts the daily fetch.

import { createServer } from "node:http";
import { createApp } from "./app.ts";
import { loadConfig } from "./config.ts";
import { DataSf } from "./datasf.ts";
import { Fetcher } from "./fetcher.ts";
import { logLine } from "./log.ts";
import { loadFamilies, loadRoster } from "./reference.ts";
import { runRefresh } from "./refresh.ts";
import { startScheduler } from "./scheduler.ts";
import { publishSite } from "./site.ts";
import { Store } from "./store.ts";

const config = loadConfig();
const store = new Store(config.dataDir);
const roster = await loadRoster();
const families = await loadFamilies();
const site = await publishSite(store);
logLine({ msg: `site built: ${site.published} cards published, ${site.unpublished} unpublished` });

const fetcher = new Fetcher({ contactEmail: config.contactEmail });
const datasf = new DataSf(fetcher, config.dataSfAppToken);
const scheduler = startScheduler({
  store, firstDelayMs: config.refreshDelayMs, log: logLine,
  run: () => runRefresh({ store, fetcher, datasf, roster, families }),
});

const server = createServer(createApp({ config, ctx: { store, roster, families }, scheduler }));
server.listen(config.port, "0.0.0.0", () => logLine({ msg: `listening on port ${config.port}` }));

for (const signal of ["SIGTERM", "SIGINT"] as const) {
  process.on(signal, () => {
    scheduler.stop();
    server.close(() => process.exit(0));
  });
}
