// Sign-in by the ADMIN_TOKEN: the token entered on the sign-in form is compared in constant time, and a signed
// cookie (an expiry and an HMAC of it under a key derived from the token) carries the session. Changing the
// token ends every session.

import { createHash, createHmac, timingSafeEqual } from "node:crypto";

export const COOKIE = "pairing_admin";
export const SESSION_MS = 12 * 60 * 60 * 1000;

const digest = (text: string): Buffer => createHash("sha256").update(text).digest();

export function tokenMatches(entered: string, adminToken: string): boolean {
  return timingSafeEqual(digest(entered), digest(adminToken));
}

function sign(expires: string, adminToken: string): string {
  return createHmac("sha256", digest(`session:${adminToken}`)).update(expires).digest("hex");
}

export function makeSession(adminToken: string, now = Date.now()): string {
  const expires = String(now + SESSION_MS);
  return `${expires}.${sign(expires, adminToken)}`;
}

export function sessionValid(cookieValue: string | undefined, adminToken: string, now = Date.now()): boolean {
  if (!cookieValue) return false;
  const [expires, mac] = cookieValue.split(".");
  if (!expires || !mac || !/^\d+$/.test(expires) || Number(expires) < now) return false;
  const expected = Buffer.from(sign(expires, adminToken), "hex");
  const given = Buffer.from(mac, "hex");
  return given.length === expected.length && timingSafeEqual(given, expected);
}

export function readCookie(header: string | undefined, name: string): string | undefined {
  for (const part of (header ?? "").split(";")) {
    const at = part.indexOf("=");
    if (at > 0 && part.slice(0, at).trim() === name) return decodeURIComponent(part.slice(at + 1).trim());
  }
  return undefined;
}

export function sessionCookie(value: string, secure: boolean): string {
  return `${COOKIE}=${encodeURIComponent(value)}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${SESSION_MS / 1000}${secure ? "; Secure" : ""}`;
}

export function clearedCookie(): string {
  return `${COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0`;
}
