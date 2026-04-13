import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createSafeTalkApiClient } from "./createSafeTalkApiClient";

describe("createSafeTalkApiClient", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("login returns access_token", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ access_token: "tok-1" }), { status: 200 }),
    );
    const api = createSafeTalkApiClient({ getAccessToken: () => null });
    await expect(api.login({ login: "u@x.y", password: "secret" })).resolves.toBe("tok-1");
    expect(fetch).toHaveBeenCalledWith(
      "/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ login: "u@x.y", password: "secret" }),
      }),
    );
  });

  it("login throws when access_token missing", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 200 }));
    const api = createSafeTalkApiClient({ getAccessToken: () => null });
    await expect(api.login({ login: "u@x.y", password: "secret" })).rejects.toThrow("Нет access_token в ответе");
  });

  it("verifyEmail uses POST without requiring JSON body", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("", { status: 200 }));
    const api = createSafeTalkApiClient({ getAccessToken: () => null });
    await expect(
      api.verifyEmail({ login: "u@x.y", code: "123456" }),
    ).resolves.toBeUndefined();
    expect(fetch).toHaveBeenCalledWith(
      "/auth/verify-email",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ login: "u@x.y", code: "123456" }),
      }),
    );
  });

  it("updateMyProfile PATCH /users/me with name", async () => {
    const updated = {
      id: "u1",
      name: "Новое имя",
      role: "user",
      allow_negative_balance: false,
      identities: ["email:a@b.c"],
    };
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(updated), { status: 200 }));
    const api = createSafeTalkApiClient({ getAccessToken: () => "t" });
    await expect(api.updateMyProfile({ name: "Новое имя" })).resolves.toEqual(updated);
    expect(fetch).toHaveBeenCalledWith(
      "/users/me",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ name: "Новое имя" }),
      }),
    );
  });

  it("getCurrentUser sends Authorization when token present", async () => {
    const profile = {
      id: "u1",
      name: "User",
      role: "user",
      allow_negative_balance: false,
      identities: ["email"],
    };
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));
    const api = createSafeTalkApiClient({ getAccessToken: () => "my-token" });
    await expect(api.getCurrentUser()).resolves.toEqual(profile);
    const init = vi.mocked(fetch).mock.calls[0][1] as RequestInit;
    const headers = init.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer my-token");
  });

  it("createPredictionTask returns task_id", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ task_id: "task-9" }), { status: 200 }),
    );
    const api = createSafeTalkApiClient({ getAccessToken: () => "t" });
    await expect(api.createPredictionTask({ modelId: "m1", text: "hi" })).resolves.toBe("task-9");
    expect(fetch).toHaveBeenCalledWith(
      "/predict",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ model_id: "m1", text: "hi" }),
      }),
    );
  });

  it("createPredictionTask throws when task_id missing", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 200 }));
    const api = createSafeTalkApiClient({ getAccessToken: () => "t" });
    await expect(api.createPredictionTask({ modelId: "m1", text: "hi" })).rejects.toThrow("Нет task_id в ответе");
  });
});
