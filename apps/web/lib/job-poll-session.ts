/** Tracks in-flight job polls so they can be cancelled on navigation or retry. */

type JobPollKind = "process" | "generation";

const controllers: Record<JobPollKind, AbortController | null> = {
  process: null,
  generation: null,
};

/** Abort any prior poll of this kind and return a fresh signal. */
export function beginJobPoll(kind: JobPollKind): AbortSignal {
  controllers[kind]?.abort();
  controllers[kind] = new AbortController();
  return controllers[kind].signal;
}

export function cancelJobPoll(kind: JobPollKind): void {
  controllers[kind]?.abort();
  controllers[kind] = null;
}

export function cancelAllJobPolls(): void {
  for (const kind of Object.keys(controllers) as JobPollKind[]) {
    cancelJobPoll(kind);
  }
}
