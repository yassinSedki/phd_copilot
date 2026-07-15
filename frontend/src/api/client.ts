import { useAuthStore } from "@/store/auth";

const BASE = "/api";

export class ApiError extends Error {
  status: number;
  detail?: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

interface ErrorBody {
  detail?: unknown;
}

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(resp: Response): Promise<T> {
  if (resp.status === 401) {
    useAuthStore.getState().logout();
  }

  const isJson = (resp.headers.get("content-type") || "").includes("application/json");
  const data = isJson ? await resp.json() : await resp.text();

  if (!resp.ok) {
    const detail = isJson ? (data as ErrorBody).detail : undefined;
    const message = typeof detail === "string" && detail ? detail : resp.statusText || `HTTP ${resp.status}`;
    throw new ApiError(resp.status, typeof message === "string" ? message : JSON.stringify(message), data);
  }
  return data as T;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers = authHeaders();
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(resp);
}

async function requestForm<T>(method: string, path: string, form: FormData): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, { method, headers: authHeaders(), body: form });
  return handleResponse<T>(resp);
}

/** For binary downloads (PDFs, etc). A plain `<a href="/api/...">` never
 * sends the Authorization header — auth is Bearer-token, not cookie-based —
 * so any authenticated download endpoint 401s when linked to directly.
 * This fetches with the header attached and hands back a Blob + the
 * server's suggested filename for the caller to trigger a save with. */
async function requestBlob(path: string): Promise<{ blob: Blob; filename: string | null }> {
  const resp = await fetch(`${BASE}${path}`, { method: "GET", headers: authHeaders() });
  if (resp.status === 401) {
    useAuthStore.getState().logout();
  }
  if (!resp.ok) {
    let detail: unknown;
    if ((resp.headers.get("content-type") || "").includes("application/json")) {
      detail = await resp.json().catch(() => undefined);
    }
    const message =
      (detail && typeof detail === "object" && "detail" in detail && typeof (detail as ErrorBody).detail === "string"
        ? ((detail as ErrorBody).detail as string)
        : undefined) ?? resp.statusText ?? `HTTP ${resp.status}`;
    throw new ApiError(resp.status, message, detail);
  }
  const disposition = resp.headers.get("content-disposition") || "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  return { blob: await resp.blob(), filename: match?.[1] ?? null };
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
  postForm: <T>(path: string, form: FormData) => requestForm<T>("POST", path, form),
  getBlob: requestBlob,
};
