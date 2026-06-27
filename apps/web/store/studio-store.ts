import { create } from "zustand";

import type { ModelMeshStats } from "@/lib/geometry-stats";
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
  sourceFileName: string | null;
  sourceFileUrl: string | null;
  processedModelUrl: string | null;
  unfoldSvgUrl: string | null;
  unfoldPdfUrl: string | null;
  status: ProjectStatus;
  settings: ProjectSettings;
  stats: ProcessStats | null;
  meshStats: ModelMeshStats | null;
  craftability: CraftabilityScore | null;
  logs: string[];
  error: string | null;
  setUploadResult: (payload: {
    projectId: string;
    sourceFileUrl: string;
    fileName: string;
  }) => void;
  setStatus: (status: ProjectStatus) => void;
  updateSettings: (partial: Partial<ProjectSettings>) => void;
  setMeshStats: (stats: ModelMeshStats | null) => void;
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
  sourceFileName: null,
  sourceFileUrl: null,
  processedModelUrl: null,
  unfoldSvgUrl: null,
  unfoldPdfUrl: null,
  status: "created" as ProjectStatus,
  settings: DEFAULT_PROJECT_SETTINGS,
  stats: null,
  meshStats: null,
  craftability: null,
  logs: [] as string[],
  error: null,
};

export const useStudioStore = create<StudioState>((set) => ({
  ...initialState,
  setUploadResult: ({ projectId, sourceFileUrl, fileName }) =>
    set({
      projectId,
      sourceFileUrl,
      sourceFileName: fileName,
      projectName: fileName.replace(/\.[^.]+$/, ""),
      status: "uploaded",
      meshStats: null,
      stats: null,
      craftability: null,
      unfoldSvgUrl: null,
      unfoldPdfUrl: null,
      processedModelUrl: null,
      error: null,
    }),
  setStatus: (status) => set({ status }),
  updateSettings: (partial) =>
    set((state) => ({ settings: { ...state.settings, ...partial } })),
  setMeshStats: (meshStats) => set({ meshStats }),
  setResults: (payload) => set(payload),
  addLog: (message) =>
    set((state) => ({
      logs: [...state.logs, `[${new Date().toLocaleTimeString()}] ${message}`],
    })),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));
