export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

let csrfToken = "";
export function setCsrfToken(token: string) { csrfToken = token; }

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.method && !["GET", "HEAD", "OPTIONS"].includes(init.method.toUpperCase())) {
    headers.set("Content-Type", "application/x-www-form-urlencoded;charset=UTF-8");
  }
  const response = await fetch(path, {
    credentials: "same-origin",
    ...init,
    headers,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401) window.location.assign(`/web/login?redirect=${encodeURIComponent(location.pathname)}`);
    throw new ApiError(data?.error?.message ?? `Request failed (${response.status})`, response.status);
  }
  return data as T;
}

export function apiMutation<T>(path: string, method: "POST" | "DELETE", payload: unknown): Promise<T> {
  const body = new URLSearchParams({ csrf_token: csrfToken, payload: JSON.stringify(payload) });
  return api<T>(path, { method, body });
}
