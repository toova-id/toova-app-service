export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...init,
    headers: { Accept: "application/json", ...init.headers },
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401) window.location.assign(`/web/login?redirect=${encodeURIComponent(location.pathname)}`);
    throw new ApiError(data?.error?.message ?? `Request failed (${response.status})`, response.status);
  }
  return data as T;
}
