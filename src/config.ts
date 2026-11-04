// Settings read from the environment. A missing one stops the start: nothing here has a stand-in value.

export interface Config {
  port: number;
  /** The directory the site keeps everything durable under: JSON records and the generated static pages. */
  dataDir: string;
  adminToken: string;
  contactEmail: string;
  dataSfAppToken: string;
  /** How long after a start the first scheduled fetch may run, when one is due. */
  refreshDelayMs: number;
}

export function loadConfig(env: Record<string, string | undefined> = process.env): Config {
  const missing = ["DATA_DIR", "ADMIN_TOKEN", "FETCH_CONTACT_EMAIL"].filter((name) => !env[name]?.trim());
  if (missing.length) throw new Error(`missing settings: ${missing.join(", ")}`);
  const port = Number(env.PORT || 8080);
  if (!Number.isInteger(port) || port <= 0) throw new Error(`PORT is not a port number: ${env.PORT}`);
  const delay = Number(env.REFRESH_START_DELAY_SECONDS || 600);
  if (!Number.isFinite(delay) || delay < 0) throw new Error(`REFRESH_START_DELAY_SECONDS is not a number: ${env.REFRESH_START_DELAY_SECONDS}`);
  return {
    port,
    dataDir: env.DATA_DIR!.trim(),
    adminToken: env.ADMIN_TOKEN!.trim(),
    contactEmail: env.FETCH_CONTACT_EMAIL!.trim(),
    dataSfAppToken: (env.DATASF_APP_TOKEN || "").trim(),
    refreshDelayMs: delay * 1000,
  };
}
