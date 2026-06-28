import { withStorageAuth } from "@/lib/api-auth";

/** Authenticated unfold asset URL with a stable cache-bust revision. */
export function unfoldPreviewUrl(url: string, revision: number): string {
  const authed = withStorageAuth(url);
  const separator = authed.includes("?") ? "&" : "?";
  return `${authed}${separator}v=${revision}`;
}
