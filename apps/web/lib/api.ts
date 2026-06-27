/** API response shapes for upload / project endpoints. */

export type UploadModelResponse = {
  projectId: string;
  sourceFileUrl: string;
  status: string;
};

export type ApiErrorBody = {
  detail?: string | Array<{ msg?: string; type?: string }>;
};

/**
 * Parse FastAPI error responses into a user-facing message.
 */
export function parseApiError(body: ApiErrorBody, fallback = "Request failed."): string {
  const { detail } = body;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((item) => item.msg ?? "Validation error").join("; ");
  }
  return fallback;
}

/**
 * Upload a 3D model file to the backend.
 */
export async function uploadModel(file: File): Promise<UploadModelResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/upload-model", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new Error(parseApiError(body, "Upload failed."));
  }

  return response.json() as Promise<UploadModelResponse>;
}
