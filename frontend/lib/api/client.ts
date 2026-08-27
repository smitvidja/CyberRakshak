export type ApiErrorCode =
  | "FORBIDDEN"
  | "NETWORK_ERROR"
  | "NOT_FOUND"
  | "SERVER_ERROR"
  | "UNAUTHORIZED"
  | "UNKNOWN_ERROR"
  | "VALIDATION_ERROR";

export type ApiError = {
  code: ApiErrorCode | string;
  details?: Record<string, unknown>;
  message?: string;
  status?: number;
};

export type ApiResult<T> =
  | {data: T; message?: string; ok: true}
  | {error: ApiError; ok: false};

export type ApiRequestOptions = {
  accessToken?: string;
  headers?: HeadersInit;
  signal?: AbortSignal;
};

export type ApiClient = {
  delete<T>(path: string, options?: ApiRequestOptions): Promise<ApiResult<T>>;
  get<T>(path: string, options?: ApiRequestOptions): Promise<ApiResult<T>>;
  patch<T>(path: string, body?: BodyInit | null, options?: ApiRequestOptions): Promise<ApiResult<T>>;
  post<T>(path: string, body?: BodyInit | null, options?: ApiRequestOptions): Promise<ApiResult<T>>;
  put<T>(path: string, body?: BodyInit | null, options?: ApiRequestOptions): Promise<ApiResult<T>>;
  request<T>(path: string, init?: RequestInit, options?: ApiRequestOptions): Promise<ApiResult<T>>;
};

type ApiEnvelope<T> = {
  data?: T;
  error?: {code?: string; details?: Record<string, unknown>; message?: string};
  message?: string;
  success?: boolean;
};

const API_PREFIX = "/api/v1";

function normalizeBaseUrl(baseUrl: string) {
  return baseUrl.replace(/\/$/, "");
}

function buildUrl(baseUrl: string, path: string) {
  return normalizeBaseUrl(baseUrl) + API_PREFIX + (path.startsWith("/") ? path : "/" + path);
}

function asError(error: unknown): ApiError {
  if (error instanceof Error && error.name === "AbortError") {
    return {code: "NETWORK_ERROR"};
  }

  return {code: "NETWORK_ERROR"};
}

function parseEnvelope<T>(payload: unknown, status: number): ApiResult<T> {
  const envelope = payload as ApiEnvelope<T> | null;

  if (envelope?.success === true && "data" in envelope) {
    return {data: envelope.data as T, message: envelope.message, ok: true};
  }

  // A 2xx response with no body (e.g. 204 No Content from a DELETE) has no envelope to parse -
  // that is still a success, not a failure. Without this, every no-body-response endpoint (evidence
  // and warrior-report deletion included) would be reported as failed even though it worked.
  if (status >= 200 && status < 300 && envelope === null) {
    return {data: undefined as T, ok: true};
  }

  const fallbackCode = status === 401 ? "UNAUTHORIZED" : status === 403 ? "FORBIDDEN" : status === 404 ? "NOT_FOUND" : status >= 500 ? "SERVER_ERROR" : "UNKNOWN_ERROR";

  return {
    error: {
      code: envelope?.error?.code ?? fallbackCode,
      details: envelope?.error?.details,
      status
    },
    ok: false
  };
}

function jsonBody(body: unknown) {
  return JSON.stringify(body);
}

export function createApiClient(baseUrl = process.env.NEXT_PUBLIC_API_URL): ApiClient {
  if (!baseUrl) {
    throw new Error("NEXT_PUBLIC_API_URL must be configured before API requests are made.");
  }

  const resolvedBaseUrl = baseUrl;

  async function request<T>(path: string, init: RequestInit = {}, options: ApiRequestOptions = {}): Promise<ApiResult<T>> {
    const headers = new Headers(init.headers);
    new Headers(options.headers).forEach((value, key) => headers.set(key, value));
    const hasBody = init.body !== undefined && init.body !== null;

    if (hasBody && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    if (options.accessToken) {
      headers.set("Authorization", "Bearer " + options.accessToken);
    }

    try {
      const response = await fetch(buildUrl(resolvedBaseUrl, path), {
        ...init,
        credentials: "include",
        headers,
        signal: options.signal
      });
      const payload = await response.json().catch(() => null);

      return parseEnvelope<T>(payload, response.status);
    } catch (error) {
      return {error: asError(error), ok: false};
    }
  }

  return {
    request,
    get: (path, options) => request(path, {method: "GET"}, options),
    post: (path, body, options) => request(path, {body, method: "POST"}, options),
    put: (path, body, options) => request(path, {body, method: "PUT"}, options),
    patch: (path, body, options) => request(path, {body, method: "PATCH"}, options),
    delete: (path, options) => request(path, {method: "DELETE"}, options)
  };
}

export const apiClient = {
  delete: <T>(path: string, options?: ApiRequestOptions) => createApiClient().delete<T>(path, options),
  get: <T>(path: string, options?: ApiRequestOptions) => createApiClient().get<T>(path, options),
  patch: <T>(path: string, body?: unknown, options?: ApiRequestOptions) => createApiClient().patch<T>(path, body === undefined ? null : jsonBody(body), options),
  post: <T>(path: string, body?: unknown, options?: ApiRequestOptions) => createApiClient().post<T>(path, body === undefined ? null : jsonBody(body), options),
  put: <T>(path: string, body?: unknown, options?: ApiRequestOptions) => createApiClient().put<T>(path, body === undefined ? null : jsonBody(body), options),
  upload: <T>(path: string, body: FormData, options?: ApiRequestOptions) => createApiClient().post<T>(path, body, options)
};
