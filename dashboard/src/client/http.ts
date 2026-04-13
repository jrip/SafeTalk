export function isUnknownRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object";
}

export async function readApiErrorBody(res: Response): Promise<string> {
  let parsed: unknown;
  try {
    parsed = await res.json();
  } catch {
    return res.statusText;
  }
  if (!isUnknownRecord(parsed)) {
    return res.statusText;
  }
  const msg = parsed.message;
  if (typeof msg === "string" && msg.length > 0) {
    return msg;
  }
  const det = parsed.detail;
  if (typeof det === "string") {
    return det;
  }
  return res.statusText;
}

export interface IRequestContext {
  readonly apiOrigin: string;
  readonly getAccessToken: () => string | null;
}

/** Плоское JSON-тело для наших ручек (без `any`). */
export interface IJsonRequestBody {
  readonly [key: string]: string | number | boolean | null;
}

export interface IJsonRequestInit {
  readonly method?: string;
  readonly body?: IJsonRequestBody;
  readonly auth?: boolean;
}

function buildUrl(ctx: IRequestContext, path: string): string {
  const base = ctx.apiOrigin.replace(/\/$/, "");
  if (!base) {
    return path.startsWith("/") ? path : `/${path}`;
  }
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

function headersFor(ctx: IRequestContext, withJsonBody: boolean, withAuth: boolean): Headers {
  const h = new Headers();
  if (withJsonBody) {
    h.set("Content-Type", "application/json");
  }
  if (withAuth) {
    const token = ctx.getAccessToken();
    if (token) {
      h.set("Authorization", `Bearer ${token}`);
    }
  }
  return h;
}

function parseJsonFromText<T>(text: string): T {
  return JSON.parse(text) as T;
}

export async function requestVoid(ctx: IRequestContext, path: string, init: IJsonRequestInit): Promise<void> {
  const method = init.method ?? "POST";
  const hasBody = init.body !== undefined;
  const res = await fetch(buildUrl(ctx, path), {
    method,
    headers: headersFor(ctx, hasBody, init.auth ?? false),
    body: hasBody ? JSON.stringify(init.body) : undefined,
  });
  if (!res.ok) {
    throw new Error(await readApiErrorBody(res));
  }
  await res.text();
}

export async function requestJson<T>(ctx: IRequestContext, path: string, init: IJsonRequestInit): Promise<T> {
  const method = init.method ?? "GET";
  const hasBody = init.body !== undefined;
  const res = await fetch(buildUrl(ctx, path), {
    method,
    headers: headersFor(ctx, hasBody, init.auth ?? false),
    body: hasBody ? JSON.stringify(init.body) : undefined,
  });
  if (!res.ok) {
    throw new Error(await readApiErrorBody(res));
  }
  const text = await res.text();
  if (!text.trim()) {
    throw new Error("Пустой успешный ответ от API");
  }
  return parseJsonFromText<T>(text);
}
