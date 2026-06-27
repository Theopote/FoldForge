import { create } from "zustand";

import {
  DEFAULT_PROJECT_SETTINGS,
  type CraftabilityScore,
  type ProcessStats,
  type ProjectSettings,
  type ProjectStatus,
} from "@/types";

type StudioState = {
  projectId: string | null;
  projectName: string;
  sourceFileUrl: string | null;
  processedModelUrl: string | null;
  unfoldSvgUrl: string | null;
  unfoldPdfUrl: string | null;
  status: ProjectStatus;
  settings: ProjectSettings;
  stats: ProcessStats | null;
  craftability: CraftabilityScore | null;
  logs: string[];
  error: string | null;
  setProjectId: (id: string | null) => void;
  setSourceFileUrl: (url: string | null) => void;
  setStatus: (status: ProjectStatus) => void;
  updateSettings: (partial: Partial<ProjectSettings>) => void;
  setResults: (payload: {
    processedModelUrl?: string | null;
    unfoldSvgUrl?: string | null;
    unfoldPdfUrl?: string | null;
    stats?: ProcessStats | null;
    craftability?: CraftabilityScore | null;
  }) => void;
  addLog: (message: string) => void;
  setError: (message: string | null) => void;
  reset: () => void;
};

const initialState = {
  projectId: null,
  projectName: "Untitled Project",
  sourceFileUrl: null,
  processedModelUrl: null,
  unfoldSvgUrl: null,
  unfoldPdfUrl: null,
  status: "created" as ProjectStatus,
  settings: DEFAULT_PROJECT_SETTINGS,
  stats: null,
  craftability: null,
  logs: [] as string[],
  error: null,
};

export const useStudioStore = create<StudioState>((set) => ({
  ...initialState,
  setProjectId: (projectId) => set({ projectId }),
  setSourceFileUrl: (sourceFileUrl) => set({ sourceFileUrl, status: "uploaded" }),
  setStatus: (status) => set({ status }),
  updateSettings: (partial) =>
    set((state) => ({ settings: { ...state.settings, ...partial } })),
  setResults: (payload) => set(payload),
  addLog: (message) =>
    set((state) => ({
      logs: [...state.logs, `[${new Date().toLocaleTimeString()}] ${message}`],
    })),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));
