import { withStorageAuth } from "@/lib/api-auth";

export function instructionExportUrls(projectId: string) {
  const txt = `/storage/exports/${projectId}.instructions.txt`;
  const pdf = `/storage/exports/${projectId}.instructions.pdf`;
  const stepsSvg = `/storage/exports/${projectId}.assembly-steps.svg`;
  return {
    txt,
    pdf,
    stepsSvg,
    txtAuth: withStorageAuth(txt),
    pdfAuth: withStorageAuth(pdf),
    stepsSvgAuth: withStorageAuth(stepsSvg),
  };
}

export function instructionPreviewUrl(projectId: string, revision: number): string {
  const { txtAuth } = instructionExportUrls(projectId);
  const separator = txtAuth.includes("?") ? "&" : "?";
  return `${txtAuth}${separator}v=${revision}`;
}

export function assemblyStepsPreviewUrl(projectId: string, revision: number): string {
  const { stepsSvgAuth } = instructionExportUrls(projectId);
  const separator = stepsSvgAuth.includes("?") ? "&" : "?";
  return `${stepsSvgAuth}${separator}v=${revision}`;
}
