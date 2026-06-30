import { create } from "zustand";

import type { ModelMeshStats } from "@/lib/geometry-stats";
import type { SeamPosition3d } from "@/lib/seam-manifest";
import { cancelAllJobPolls } from "@/lib/job-poll-session";
import type { StudioProjectSnapshot } from "@/lib/project-storage";
import { persistLastProjectId } from "@/lib/project-storage";
import { scheduleProjectSettingsSync } from "@/lib/project-settings-sync";
import {
  DEFAULT_PROJECT_SETTINGS,
  type CraftabilityScore,
  type ColorMode,
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
  activeProcessJobId: string | null;
  processedModelUrl: string | null;
  unfoldSvgUrl: string | null;
  unfoldPdfUrl: string | null;
  unfoldZipUrl: string | null;
  exportRevision: number;
  exportedColorMode: ColorMode | null;
  status: ProjectStatus;
  settings: ProjectSettings;
  stats: ProcessStats | null;
  meshStats: ModelMeshStats | null;
  craftability: CraftabilityScore | null;
  logs: string[];
  error: string | null;
  jobPhase: "idle" | "ai_generation" | "papercraft_process";
  jobProgress: number;
  jobMessage: string;
  selectedSeamMeshEdge: string | null;
  selectedSeamHighlight: SeamPosition3d | null;
  seamInspectorMode: boolean;
  showOverlapHeatmap: boolean;
  setSourceType: (sourceType: SourceType) => void;
  setLocalSamplePreview: (payload: {
    sourceFileUrl: string;
    fileName: string;
    unfoldSvgUrl?: string | null;
    stats?: ProcessStats | null;
    craftability?: CraftabilityScore | null;
  }) => void;
  setUploadResult: (payload: {
    projectId: string;
    sourceFileUrl: string;
    fileName: string;
  }) => void;
  setGenerationResult: (payload: GenerationPayload) => void;
  setAsyncGenerationPending: (payload: AsyncGenerationPayload) => void;
  setActiveJobId: (jobId: string | null) => void;
  setActiveProcessJobId: (jobId: string | null) => void;
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
  beginPapercraftProcessing: () => void;
  completePapercraftProcessing: (payload: {
    processedModelUrl: string | null;
    unfoldSvgUrl: string | null;
    unfoldPdfUrl: string | null;
    unfoldZipUrl: string | null;
    stats: ProcessStats | null;
    craftability: CraftabilityScore | null;
    status: ProjectStatus;
  }) => void;
  restoreProject: (saved: StudioProjectSnapshot) => void;
  addLog: (message: string) => void;
  setError: (message: string | null) => void;
  setJobProgress: (payload: {
    phase: "idle" | "ai_generation" | "papercraft_process";
    progress: number;
    message: string;
  }) => void;
  clearJobProgress: () => void;
  setSelectedSeamHighlight: (payload: {
    meshEdge: string | null;
    position3d: SeamPosition3d | null;
  }) => void;
  setSeamInspectorMode: (enabled: boolean) => void;
  setShowOverlapHeatmap: (enabled: boolean) => void;
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
  activeProcessJobId: null,
  processedModelUrl: null,
  unfoldSvgUrl: null,
  unfoldPdfUrl: null,
  unfoldZipUrl: null,
  exportRevision: 0,
  exportedColorMode: null,
  status: "created" as ProjectStatus,
  settings: DEFAULT_PROJECT_SETTINGS,
  stats: null,
  meshStats: null,
  craftability: null,
  logs: [] as string[],
  error: null,
  jobPhase: "idle" as const,
  jobProgress: 0,
  jobMessage: "",
  selectedSeamMeshEdge: null,
  selectedSeamHighlight: null,
  seamInspectorMode: false,
  showOverlapHeatmap: false,
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
    exportRevision: 0,
    exportedColorMode: null,
    error: null,
  };
}

function touchProjectSession(projectId: string): void {
  persistLastProjectId(projectId);
}

export const useStudioStore = create<StudioState>((set) => ({
  ...initialState,
  setSourceType: (sourceType) => set({ sourceType }),
  setLocalSamplePreview: ({
    sourceFileUrl,
    fileName,
    unfoldSvgUrl = null,
    stats = null,
    craftability = null,
  }) =>
    set(() => {
      cancelAllJobPolls();
      const hasOfflineUnfold = Boolean(unfoldSvgUrl);
      return {
        projectId: null,
        sourceFileUrl,
        sourceFileName: fileName,
        projectName: fileName.replace(/\.[^.]+$/, ""),
        sourceType: "upload_3d" as SourceType,
        sourcePrompt: null,
        sourceImageUrl: null,
        aiProvider: null,
        enhancedPrompt: null,
        activeJobId: null,
        activeProcessJobId: null,
        status: hasOfflineUnfold ? "ready" as ProjectStatus : "uploaded" as ProjectStatus,
        ...applyGenerationReset(),
        unfoldSvgUrl,
        exportRevision: hasOfflineUnfold ? 1 : 0,
        exportedColorMode: hasOfflineUnfold ? "line_art" as ColorMode : null,
        stats,
        craftability,
      };
    }),
  setUploadResult: ({ projectId, sourceFileUrl, fileName }) =>
    set(() => {
      cancelAllJobPolls();
      touchProjectSession(projectId);
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
        activeProcessJobId: null,
        status: "uploaded" as ProjectStatus,
        ...applyGenerationReset(),
      };
    }),
  setGenerationResult: (payload) =>
    set(() => {
      cancelAllJobPolls();
      touchProjectSession(payload.projectId);
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
        activeProcessJobId: null,
        status: "uploaded" as ProjectStatus,
        ...applyGenerationReset(),
      };
    }),
  setAsyncGenerationPending: (payload) =>
    set(() => {
      cancelAllJobPolls();
      touchProjectSession(payload.projectId);
      return {
        projectId: payload.projectId,
        projectName: payload.projectName,
        sourceType: payload.sourceType,
        sourcePrompt: payload.sourcePrompt ?? null,
        sourceImageUrl: payload.sourceImageUrl ?? null,
        aiProvider: payload.aiProvider ?? null,
        enhancedPrompt: null,
        activeJobId: payload.jobId,
        activeProcessJobId: null,
        sourceFileUrl: null,
        sourceFileName: null,
        status: "processing" as ProjectStatus,
        ...applyGenerationReset(),
      };
    }),
  setActiveJobId: (activeJobId) => set({ activeJobId }),
  setActiveProcessJobId: (activeProcessJobId) => set({ activeProcessJobId }),
  setStatus: (status) => set({ status }),
  updateSettings: (partial) =>
    set((state) => {
      const settings = { ...state.settings, ...partial };
      if (state.projectId) {
        scheduleProjectSettingsSync(state.projectId, settings);
      }
      return { settings };
    }),
  setMeshStats: (meshStats) => set({ meshStats }),
  setResults: (payload) => set(payload),
  beginPapercraftProcessing: () =>
    set({
      status: "processing" as ProjectStatus,
      activeProcessJobId: null,
      processedModelUrl: null,
      unfoldSvgUrl: null,
      unfoldPdfUrl: null,
      unfoldZipUrl: null,
      stats: null,
      craftability: null,
      error: null,
    }),
  completePapercraftProcessing: (payload) =>
    set((state) => ({
      ...payload,
      activeProcessJobId: null,
      exportRevision: state.exportRevision + 1,
      exportedColorMode: state.settings.colorMode,
    })),
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
      activeProcessJobId: saved.activeProcessJobId ?? null,
      processedModelUrl: saved.processedModelUrl,
      unfoldSvgUrl: saved.unfoldSvgUrl,
      unfoldPdfUrl: saved.unfoldPdfUrl,
      unfoldZipUrl: saved.unfoldZipUrl,
      status: saved.status,
      settings: saved.settings,
      stats: saved.stats,
      craftability: saved.craftability,
      exportRevision: saved.unfoldSvgUrl ? 1 : 0,
      exportedColorMode:
        saved.status === "ready" ? saved.settings.colorMode : null,
      error: null,
    }),
  addLog: (message) =>
    set((state) => ({
      logs: [...state.logs, `[${new Date().toLocaleTimeString()}] ${message}`],
    })),
  setError: (error) => set({ error }),
  setJobProgress: ({ phase, progress, message }) =>
    set({ jobPhase: phase, jobProgress: progress, jobMessage: message }),
  clearJobProgress: () =>
    set({ jobPhase: "idle", jobProgress: 0, jobMessage: "" }),
  setSelectedSeamHighlight: ({ meshEdge, position3d }) =>
    set({ selectedSeamMeshEdge: meshEdge, selectedSeamHighlight: position3d }),
  setSeamInspectorMode: (seamInspectorMode) =>
    set({ seamInspectorMode, ...(seamInspectorMode ? {} : { showOverlapHeatmap: false }) }),
  setShowOverlapHeatmap: (showOverlapHeatmap) => set({ showOverlapHeatmap }),
  reset: () => set(initialState),
}));
