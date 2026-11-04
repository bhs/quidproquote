// One JSON line per event on standard output, written as it happens.

export type LogFn = (fields: Record<string, unknown>) => void;

export const logLine: LogFn = (fields) => {
  process.stdout.write(JSON.stringify({ time: new Date().toISOString(), level: "info", ...fields }) + "\n");
};
