import { withStorageAuth } from "@/lib/api-auth";

export function instructionExportUrls(projectId: string) {
  const txt = `/storage/exports/${projectId}.instructions.txt`;
  const pdf = `/storage/exports/${projectId}.instructions.pdf`;
  return {
    txt,
    pdf,
    txtAuth: withStorageAuth(txt),
    pdfAuth: withStorageAuth(pdf),
  };
}

export function instructionPreviewUrl(projectId: string, revision: number): string {
  const { txtAuth } = instructionExportUrls(projectId);
  const separator = txtAuth.includes("?") ? "&" : "?";
  return `${txtAuth}${separator}v=${revision}`;
}
