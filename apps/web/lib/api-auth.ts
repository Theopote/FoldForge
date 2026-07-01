/** Client-side API key helpers (optional; required when backend auth is enabled). */

export function getApiKey(): string | undefined {
  return process.env.NEXT_PUBLIC_FOLDFORGE_API_KEY;
}

export function apiAuthHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  const key = getApiKey();
  if (key) {
    headers.set("Authorization", `Bearer ${key}`);
  }
  return headers;
}

/** Append access_token for Three.js loaders that cannot set request headers. */
export function withStorageAuth(url: string): string {
  const key = getApiKey();
  if (!key) {
    return url;
  }
  const needsToken =
    url.startsWith("/storage/") ||
    (url.startsWith("/api/projects/") && url.includes("/export/"));
  if (!needsToken) {
    return url;
  }
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}access_token=${encodeURIComponent(key)}`;
}
