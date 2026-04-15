import { afterEach, describe, expect, it, vi } from "vitest";
import { isUnknownRecord, readApiErrorBody, requestJson, requestVoid, type IRequestContext } from "./http";

const ctx: IRequestContext = { apiOrigin: "", getAccessToken: () => null };

describe("isUnknownRecord", () => {
  it("returns false for null and primitives", () => {
    expect(isUnknownRecord(null)).toBe(false);
    expect(isUnknownRecord(undefined)).toBe(false);
    expect(isUnknownRecord("x")).toBe(false);
    expect(isUnknownRecord(1)).toBe(false);
  });

  it("returns true for plain objects and arrays", () => {
    expect(isUnknownRecord({})).toBe(true);
    expect(isUnknownRecord({ a: 1 })).toBe(true);
    expect(isUnknownRecord([])).toBe(true);
  });
});

describe("readApiErrorBody", () => {
  it("prefers string message when present", async () => {
    const res = new Response(JSON.stringify({ message: "bad request" }), {
      status: 400,
      statusText: "Bad Request",
    });
    await expect(readApiErrorBody(res)).resolves.toBe("bad request");
  });

  it("falls back to detail when message missing", async () => {
    const res = new Response(JSON.stringify({ detail: "not found" }), {
      status: 404,
      statusText: "Not Found",
    });
    await expect(readApiErrorBody(res)).resolves.toBe("not found");
  });

  it("uses statusText when JSON is not an object", async () => {
    const res = new Response(JSON.stringify("oops"), { status: 500, statusText: "Server Error" });
    await expect(readApiErrorBody(res)).resolves.toBe("Server Error");
  });

  it("uses statusText when JSON parse fails", async () => {
    const res = new Response("not-json", { status: 502, statusText: "Bad Gateway" });
    await expect(readApiErrorBody(res)).resolves.toBe("Bad Gateway");
  });
});

describe("requestJson / requestVoid", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("requestJson parses successful body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true, n: 2 }), { status: 200 })),
    );
    await expect(requestJson<{ ok: boolean; n: number }>(ctx, "/x", { method: "GET", auth: false })).resolves.toEqual({
      ok: true,
      n: 2,
    });
    expect(fetch).toHaveBeenCalledWith(
      "/x",
      expect.objectContaining({ method: "GET", headers: expect.any(Headers) }),
    );
  });

  it("requestJson throws on empty successful body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 200 })));
    await expect(requestJson<unknown>(ctx, "/x", { method: "GET", auth: false })).rejects.toThrow(
      "Пустой успешный ответ от API",
    );
  });

  it("requestJson throws with API error message when not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ message: "nope" }), { status: 400, statusText: "Bad Request" }),
      ),
    );
    await expect(requestJson<unknown>(ctx, "/x", { method: "GET", auth: false })).rejects.toThrow("nope");
  });

  it("requestVoid resolves on ok with empty body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 200 })));
    await expect(requestVoid(ctx, "/auth/verify-email", { method: "POST", body: { a: "1" }, auth: false })).resolves.toBeUndefined();
  });

  it("buildUrl joins apiOrigin without trailing slash", async () => {
    const originCtx: IRequestContext = { apiOrigin: "http://127.0.0.1:8000/", getAccessToken: () => null };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ ping: 1 }), { status: 200 })),
    );
    await requestJson<{ ping: number }>(originCtx, "/users/me", { method: "GET", auth: false });
    expect(fetch).toHaveBeenCalledWith("http://127.0.0.1:8000/users/me", expect.anything());
  });
});
