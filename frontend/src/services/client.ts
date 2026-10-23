/** Thin fetch wrapper that unwraps the API error envelope. */

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId: string;
  readonly fields: { field: string; message: string }[];

  constructor(
    message: string,
    options: {
      code?: string;
      status?: number;
      requestId?: string;
      fields?: { field: string; message: string }[];
    } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.code = options.code ?? "REQUEST_FAILED";
    this.status = options.status ?? 0;
    this.requestId = options.requestId ?? "";
    this.fields = options.fields ?? [];
  }
}

const BASE = "/api";

export interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  /** Treat these statuses as success and return the parsed body anyway. */
  allowStatus?: number[];
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal, allowStatus = [] } = options;

  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      signal,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new ApiError("Cannot reach the BattleVerse server. Is the backend running?", {
      code: "NETWORK_ERROR",
    });
  }

  if (!response.ok && !allowStatus.includes(response.status)) {
    throw await toApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError("The server sent a response we could not read.", {
      code: "BAD_RESPONSE",
      status: response.status,
    });
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  const envelope = payload as
    | {
        error?: {
          code?: string;
          message?: string;
          request_id?: string;
          details?: { fields?: { field: string; message: string }[] };
        };
        detail?: string;
      }
    | null;

  const error = envelope?.error;
  const message =
    error?.message ??
    (typeof envelope?.detail === "string" ? envelope.detail : undefined) ??
    defaultMessageFor(response.status);

  return new ApiError(message, {
    code: error?.code ?? `HTTP_${response.status}`,
    status: response.status,
    requestId: error?.request_id ?? "",
    fields: error?.details?.fields ?? [],
  });
}

function defaultMessageFor(status: number): string {
  if (status === 404) return "We could not find that.";
  if (status === 409) return "That action conflicts with the current state.";
  if (status === 429) return "Too many requests — give it a moment and retry.";
  if (status >= 500) return "The server had a problem. Please try again.";
  return "Request failed.";
}

export const get = <T>(path: string, signal?: AbortSignal) =>
  request<T>(path, { signal });

export const post = <T>(path: string, body?: unknown, signal?: AbortSignal) =>
  request<T>(path, { method: "POST", body: body ?? {}, signal });