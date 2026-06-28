/** Layout and process job errors surfaced to the user. */

export class ProcessJobCancelledError extends Error {
  override name = "ProcessJobCancelledError";

  constructor(message = "Processing cancelled.") {
    super(message);
  }
}

export function isProcessJobCancelled(error: unknown): boolean {
  return error instanceof ProcessJobCancelledError;
}

/** Prefer the backend error string; keep layout-fit messages readable. */
export function formatProcessJobError(error: unknown, fallback: string): string {
  if (isProcessJobCancelled(error)) {
    return error.message;
  }
  if (error instanceof Error && error.message && error.message !== "Processing failed.") {
    return error.message;
  }
  return fallback;
}
