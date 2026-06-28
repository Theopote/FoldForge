import { create } from "zustand";

import type { ModelMeshStats } from "@/lib/geometry-stats";
import type { SavedStudioProject } from "@/lib/project-storage";
import {
  persistStudioProject,
  studioStateToSavedProject,
} from "@/lib/project-storage";
import {
  DEFAULT_PROJECT_SETTINGS,
  type CraftabilityScore,
  type ProcessStats,
  type ProjectSettings,
  type ProjectStatus,
  type SourceType,
} from "@/types";

type GenerationPayload = {
  projectId: string;
  sourceFileUrl: string;
  fileName: string;
  sourceType: SourceType;
  sourcePrompt?: string | null;
  sourceImageUrl?: string | null;
  aiProvider?: string | null;
  enhancedPrompt?: string | null;
};

type AsyncGenerationPayload = {
  projectId: string;
  projectName: string;
  jobId: string;
  sourceType: SourceType;
  sourcePrompt?: string | null;
  sourceImageUrl?: string | null;
  aiProvider?: string | null;
};

type StudioState = {
  projectId: string | null;
  projectName: string;
  sourceType: SourceType;
  sourceFileName: string | null;
  sourceFileUrl: string | null;
  sourcePrompt: string | null;
  sourceImageUrl: string | null;
  aiProvider: string | null;
  enhancedPrompt: string | null;
  activeJobId: string | null;
  processedModelUrl: string | null;
  unfoldSvgUrl: string | null;
  unfoldPdfUrl: string | null;
  unfoldZipUrl: string | null;
  status: ProjectStatus;
  settings: ProjectSettings;
  stats: ProcessStats | null;
  meshStats: ModelMeshStats | null;
  craftability: CraftabilityScore | null;
  logs: string[];
  error: string | null;
  setSourceType: (sourceType: SourceType) => void;
  setUploadResult: (payload: {
    projectId: string;
    sourceFileUrl: string;
    fileName: string;
  }) => void;
  setGenerationResult: (payload: GenerationPayload) => void;
  setAsyncGenerationPending: (payload: AsyncGenerationPayload) => void;
  setActiveJobId: (jobId: string | null) => void;
  setStatus: (status: ProjectStatus) => void;
  updateSettings: (partial: Partial<ProjectSettings>) => void;
  setMeshStats: (stats: ModelMeshStats | null) => void;
  setResults: (payload: {
    processedModelUrl?: string | null;
    unfoldSvgUrl?: string | null;
    unfoldPdfUrl?: string | null;
    unfoldZipUrl?: string | null;
    stats?: ProcessStats | null;
    craftability?: CraftabilityScore | null;
  }) => void;
  restoreProject: (saved: SavedStudioProject) => void;
  addLog: (message: string) => void;
  setError: (message: string | null) => void;
  reset: () => void;
};

const initialState = {
  projectId: null,
  projectName: "Untitled Project",
  sourceType: "upload_3d" as SourceType,
  sourceFileName: null,
  sourceFileUrl: null,
  sourcePrompt: null,
  sourceImageUrl: null,
  aiProvider: null,
  enhancedPrompt: null,
  activeJobId: null,
  processedModelUrl: null,
  unfoldSvgUrl: null,
  unfoldPdfUrl: null,
  unfoldZipUrl: null,
  status: "created" as ProjectStatus,
  settings: DEFAULT_PROJECT_SETTINGS,
  stats: null,
  meshStats: null,
  craftability: null,
  logs: [] as string[],
  error: null,
};

function applyGenerationReset() {
  return {
    meshStats: null,
    stats: null,
    craftability: null,
    unfoldSvgUrl: null,
    unfoldPdfUrl: null,
    unfoldZipUrl: null,
    processedModelUrl: null,
    error: null,
  };
}

function persistState(state: StudioState): void {
  persistStudioProject(studioStateToSavedProject(state));
}

export const useStudioStore = create<StudioState>((set) => ({
  ...initialState,
  setSourceType: (sourceType) => set({ sourceType }),
  setUploadResult: ({ projectId, sourceFileUrl, fileName }) =>
    set((state) => {
      const next: StudioState = {
        ...state,
        projectId,
        sourceFileUrl,
        sourceFileName: fileName,
        projectName: fileName.replace(/\.[^.]+$/, ""),
        sourceType: "upload_3d",
        sourcePrompt: null,
        sourceImageUrl: null,
        aiProvider: null,
        enhancedPrompt: null,
        activeJobId: null,
        status: "uploaded",
        ...applyGenerationReset(),
      };
      persistState(next);
      return {
        projectId,
        sourceFileUrl,
        sourceFileName: fileName,
        projectName: fileName.replace(/\.[^.]+$/, ""),
        sourceType: "upload_3d" as SourceType,
        sourcePrompt: null,
        sourceImageUrl: null,
        aiProvider: null,
        enhancedPrompt: null,
        activeJobId: null,
        status: "uploaded" as ProjectStatus,
        ...applyGenerationReset(),
      };
    }),
  setGenerationResult: (payload) =>
    set((state) => {
      const next: StudioState = {
        ...state,
        projectId: payload.projectId,
        sourceFileUrl: payload.sourceFileUrl,
        sourceFileName: payload.fileName,
        projectName: payload.fileName.replace(/\.[^.]+$/, ""),
        sourceType: payload.sourceType,
        sourcePrompt: payload.sourcePrompt ?? null,
        sourceImageUrl: payload.sourceImageUrl ?? null,
        aiProvider: payload.aiProvider ?? null,
        enhancedPrompt: payload.enhancedPrompt ?? null,
        activeJobId: null,
        status: "uploaded",
        ...applyGenerationReset(),
      };
      persistState(next);
      return {
        projectId: payload.projectId,
        sourceFileUrl: payload.sourceFileUrl,
        sourceFileName: payload.fileName,
        projectName: payload.fileName.replace(/\.[^.]+$/, ""),
        sourceType: payload.sourceType,
        sourcePrompt: payload.sourcePrompt ?? null,
        sourceImageUrl: payload.sourceImageUrl ?? null,
        aiProvider: payload.aiProvider ?? null,
        enhancedPrompt: payload.enhancedPrompt ?? null,
        activeJobId: null,
        status: "uploaded" as ProjectStatus,
        ...applyGenerationReset(),
      };
    }),
  setAsyncGenerationPending: (payload) =>
    set((state) => {
      const next: StudioState = {
        ...state,
        projectId: payload.projectId,
        projectName: payload.projectName,
        sourceType: payload.sourceType,
        sourcePrompt: payload.sourcePrompt ?? null,
        sourceImageUrl: payload.sourceImageUrl ?? null,
        aiProvider: payload.aiProvider ?? null,
        enhancedPrompt: null,
        activeJobId: payload.jobId,
        sourceFileUrl: null,
        sourceFileName: null,
        status: "processing",
        ...applyGenerationReset(),
      };
      persistState(next);
      return {
        projectId: payload.projectId,
        projectName: payload.projectName,
        sourceType: payload.sourceType,
        sourcePrompt: payload.sourcePrompt ?? null,
        sourceImageUrl: payload.sourceImageUrl ?? null,
        aiProvider: payload.aiProvider ?? null,
        enhancedPrompt: null,
        activeJobId: payload.jobId,
        sourceFileUrl: null,
        sourceFileName: null,
        status: "processing" as ProjectStatus,
        ...applyGenerationReset(),
      };
    }),
  setActiveJobId: (activeJobId) =>
    set((state) => {
      const next: StudioState = { ...state, activeJobId };
      persistState(next);
      return { activeJobId };
    }),
  setStatus: (status) =>
    set((state) => {
      const next: StudioState = { ...state, status };
      persistState(next);
      return { status };
    }),
  updateSettings: (partial) =>
    set((state) => {
      const settings = { ...state.settings, ...partial };
      const next: StudioState = { ...state, settings };
      persistState(next);
      return { settings };
    }),
  setMeshStats: (meshStats) => set({ meshStats }),
  setResults: (payload) =>
    set((state) => {
      const next: StudioState = { ...state, ...payload };
      persistState(next);
      return payload;
    }),
  restoreProject: (saved) =>
    set({
      projectId: saved.projectId,
      projectName: saved.projectName,
      sourceType: saved.sourceType ?? "upload_3d",
      sourceFileName: saved.sourceFileName,
      sourceFileUrl: saved.sourceFileUrl,
      sourcePrompt: saved.sourcePrompt ?? null,
      sourceImageUrl: saved.sourceImageUrl ?? null,
      aiProvider: saved.aiProvider ?? null,
      enhancedPrompt: saved.enhancedPrompt ?? null,
      activeJobId: saved.activeJobId ?? null,
      processedModelUrl: saved.processedModelUrl,
      unfoldSvgUrl: saved.unfoldSvgUrl,
      unfoldPdfUrl: saved.unfoldPdfUrl,
      unfoldZipUrl: saved.unfoldZipUrl,
      status: saved.status,
      settings: saved.settings,
      stats: saved.stats,
      craftability: saved.craftability,
      error: null,
    }),
  addLog: (message) =>
    set((state) => ({
      logs: [...state.logs, `[${new Date().toLocaleTimeString()}] ${message}`],
    })),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));
