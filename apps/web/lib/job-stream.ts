/** SSE job progress with polling fallback. */

import { withEventStreamAuth } from "@/lib/event-stream-auth";
import { isAbortError, throwIfAborted } from "@/lib/poll-utils";

export type StreamOptions = {
  timeoutMs?: number;
  signal?: AbortSignal;
  onMessage?: (payload: Record<string, unknown>) => void;
};

export function streamJobEvents<T extends Record<string, unknown>>(
  path: string,
  options: StreamOptions & {
    isTerminal: (payload: T) => boolean;
    isFailure: (payload: T) => Error | null;
  },
): Promise<T> {
  const { timeoutMs = 900_000, signal, onMessage, isTerminal, isFailure } = options;

  if (typeof EventSource === "undefined") {
    return Promise.reject(new Error("EventSource unavailable"));
  }

  return new Promise((resolve, reject) => {
    const url = withEventStreamAuth(path);
    const source = new EventSource(url);

    const timeout = window.setTimeout(() => {
      cleanup();
      reject(new Error("Job stream timed out."));
    }, timeoutMs);

    const onAbort = () => {
      cleanup();
      reject(new DOMException("Aborted", "AbortError"));
    };

    const cleanup = () => {
      window.clearTimeout(timeout);
      signal?.removeEventListener("abort", onAbort);
      source.close();
    };

    if (signal) {
      if (signal.aborted) {
        cleanup();
        reject(new DOMException("Aborted", "AbortError"));
        return;
      }
      signal.addEventListener("abort", onAbort, { once: true });
    }

    source.onmessage = (event: MessageEvent<string>) => {
      throwIfAborted(signal);

      let payload: T;
      try {
        payload = JSON.parse(event.data) as T;
      } catch {
        return;
      }

      onMessage?.(payload);

      const failure = isFailure(payload);
      if (failure) {
        cleanup();
        reject(failure);
        return;
      }

      if (isTerminal(payload)) {
        cleanup();
        resolve(payload);
      }
    };

    source.onerror = () => {
      cleanup();
      reject(new Error("Job event stream connection failed."));
    };
  });
}

export async function withStreamOrFallback<T>(
  stream: () => Promise<T>,
  fallback: () => Promise<T>,
  signal?: AbortSignal,
): Promise<T> {
  try {
    return await stream();
  } catch (error) {
    if (isAbortError(error)) throw error;
    return fallback();
  }
}
