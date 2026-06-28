/** EventSource URL auth — browsers cannot set Authorization on SSE. */

import { getApiKey } from "@/lib/api-auth";

export function withEventStreamAuth(path: string): string {
  const key = getApiKey();
  if (!key) return path;

  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}access_token=${encodeURIComponent(key)}`;
}
