// The roster of officials and the donor families the site reads. Both ship with the code (reference/).

import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import type { Family, Official } from "./types.ts";

async function readReference<T>(name: string): Promise<T> {
  const path = fileURLToPath(new URL(`../reference/${name}`, import.meta.url));
  return JSON.parse(await readFile(path, "utf-8")) as T;
}

export async function loadRoster(): Promise<Official[]> {
  return (await readReference<{ officials: Official[] }>("roster.json")).officials;
}

export async function loadFamilies(): Promise<Family[]> {
  return (await readReference<{ families: Family[] }>("families.json")).families;
}

export function fixturePath(name: string): string {
  return fileURLToPath(new URL(`../fixtures/${name}`, import.meta.url));
}
