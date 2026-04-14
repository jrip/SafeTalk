import type {
  IBalanceSnapshot,
  IAdminStats,
  IAdminUserRow,
  ICreatePredictionPayload,
  IHistoryEntry,
  ILedgerEntry,
  ILoginCredentials,
  IMlCatalogItem,
  IPollPredictionOptions,
  IPredictionTaskDetail,
  IAdminPatchUserPayload,
  IRegisterPayload,
  IRegisterResult,
  IUpdateMyProfilePayload,
  IUserProfile,
  IVerifyEmailPayload,
} from "./contracts";
import type { IRequestContext } from "./http";
import { isUnknownRecord, requestJson, requestVoid } from "./http";
import type { ISafeTalkApiClient } from "./ISafeTalkApiClient";

function parseAdminUserRow(row: unknown): IAdminUserRow {
  if (!isUnknownRecord(row)) {
    throw new Error("Некорректная запись в ответе /admin/users");
  }
  return {
    id: String(row.id ?? ""),
    name: String(row.name ?? ""),
    role: String(row.role ?? "user"),
    allow_negative_balance: Boolean(row.allow_negative_balance),
    primary_email:
      row.primary_email === null || row.primary_email === undefined ? null : String(row.primary_email),
    token_count: String(row.token_count ?? "0"),
  };
}

export interface ICreateSafeTalkApiClientDeps {
  readonly getAccessToken: () => string | null;
  /**
   * Пустая строка — относительные пути (nginx / Vite proxy).
   * Иначе полный origin, например `http://127.0.0.1:8000` (см. `VITE_API_ORIGIN`).
   */
  readonly apiOrigin?: string;
}

export function createSafeTalkApiClient(deps: ICreateSafeTalkApiClientDeps): ISafeTalkApiClient {
  const ctx: IRequestContext = {
    apiOrigin: deps.apiOrigin ?? "",
    getAccessToken: deps.getAccessToken,
  };

  return {
    async login(credentials: ILoginCredentials): Promise<string> {
      const data = await requestJson<{ access_token: string }>(ctx, "/auth/login", {
        method: "POST",
        body: { login: credentials.login, password: credentials.password },
        auth: false,
      });
      if (!data.access_token) {
        throw new Error("Нет access_token в ответе");
      }
      return data.access_token;
    },

    async register(payload: IRegisterPayload): Promise<IRegisterResult> {
      return requestJson<IRegisterResult>(ctx, "/auth/register", {
        method: "POST",
        body: { login: payload.login, password: payload.password, name: payload.name },
        auth: false,
      });
    },

    async verifyEmail(payload: IVerifyEmailPayload): Promise<void> {
      await requestVoid(ctx, "/auth/verify-email", {
        method: "POST",
        body: { login: payload.login, code: payload.code },
        auth: false,
      });
    },

    async getCurrentUser(): Promise<IUserProfile> {
      return requestJson<IUserProfile>(ctx, "/users/me", { method: "GET", auth: true });
    },

    async getAdminUser(userId: string): Promise<IUserProfile> {
      return requestJson<IUserProfile>(ctx, `/admin/users/${encodeURIComponent(userId)}`, { method: "GET", auth: true });
    },

    async updateMyProfile(payload: IUpdateMyProfilePayload): Promise<IUserProfile> {
      return requestJson<IUserProfile>(ctx, "/users/me", {
        method: "PATCH",
        body: { name: payload.name },
        auth: true,
      });
    },

    async getMyBalance(): Promise<IBalanceSnapshot> {
      return requestJson<IBalanceSnapshot>(ctx, "/balance/me", { method: "GET", auth: true });
    },

    async topUpMyBalance(amountDecimalString: string): Promise<IBalanceSnapshot> {
      return requestJson<IBalanceSnapshot>(ctx, "/balance/me/topup", {
        method: "POST",
        body: { amount: amountDecimalString },
        auth: true,
      });
    },

    async listMlModels(): Promise<readonly IMlCatalogItem[]> {
      return requestJson<IMlCatalogItem[]>(ctx, "/predict/models", { method: "GET", auth: true });
    },

    async createPredictionTask(payload: ICreatePredictionPayload): Promise<string> {
      const data = await requestJson<{ task_id?: string }>(ctx, "/predict", {
        method: "POST",
        body: { model_id: payload.modelId, text: payload.text },
        auth: true,
      });
      if (!data.task_id) {
        throw new Error("Нет task_id в ответе");
      }
      return data.task_id;
    },

    async getPredictionTask(taskId: string): Promise<IPredictionTaskDetail> {
      return requestJson<IPredictionTaskDetail>(ctx, `/predict/${encodeURIComponent(taskId)}`, {
        method: "GET",
        auth: true,
      });
    },

    async pollPredictionTask(
      taskId: string,
      options?: IPollPredictionOptions,
    ): Promise<IPredictionTaskDetail> {
      const intervalMs = options?.intervalMs ?? 1000;
      const deadlineMs = options?.deadlineMs ?? 120_000;
      const end = Date.now() + deadlineMs;
      let last: IPredictionTaskDetail | null = null;
      while (Date.now() < end) {
        last = await this.getPredictionTask(taskId);
        if (last.status === "completed" || last.status === "failed") {
          return last;
        }
        await new Promise((r) => setTimeout(r, intervalMs));
      }
      throw new Error(
        `Таймаут ожидания задачи ${taskId}, последний статус: ${last?.status ?? "нет ответа"}`,
      );
    },

    async listMyHistory(): Promise<readonly IHistoryEntry[]> {
      return requestJson<IHistoryEntry[]>(ctx, "/history/me", { method: "GET", auth: true });
    },

    async listMyLedger(): Promise<readonly ILedgerEntry[]> {
      return requestJson<ILedgerEntry[]>(ctx, "/balance/me/ledger", { method: "GET", auth: true });
    },

    async listAdminUsers(): Promise<readonly IAdminUserRow[]> {
      const raw = await requestJson<unknown>(ctx, "/admin/users", { method: "GET", auth: true });
      if (!Array.isArray(raw)) {
        throw new Error("Ответ /admin/users: ожидался массив");
      }
      return raw.map(parseAdminUserRow);
    },

    async getAdminStats(): Promise<IAdminStats> {
      return requestJson<IAdminStats>(ctx, "/admin/stats", { method: "GET", auth: true });
    },

    async listAdminLedger(limit?: number): Promise<readonly ILedgerEntry[]> {
      const q = limit != null ? `?limit=${encodeURIComponent(String(limit))}` : "";
      return requestJson<ILedgerEntry[]>(ctx, `/admin/ledger${q}`, { method: "GET", auth: true });
    },

    async listAdminHistory(limit?: number): Promise<readonly IHistoryEntry[]> {
      const q = limit != null ? `?limit=${encodeURIComponent(String(limit))}` : "";
      return requestJson<IHistoryEntry[]>(ctx, `/admin/history${q}`, { method: "GET", auth: true });
    },

    async getAdminMlTask(taskId: string): Promise<IPredictionTaskDetail> {
      return requestJson<IPredictionTaskDetail>(ctx, `/admin/ml-tasks/${encodeURIComponent(taskId)}`, {
        method: "GET",
        auth: true,
      });
    },

    async adminTopUpUserBalance(userId: string, amountDecimalString: string): Promise<IBalanceSnapshot> {
      return requestJson<IBalanceSnapshot>(ctx, `/admin/users/${encodeURIComponent(userId)}/topup`, {
        method: "POST",
        body: { amount: amountDecimalString },
        auth: true,
      });
    },

    async adminSpendUserBalance(userId: string, amountDecimalString: string): Promise<IBalanceSnapshot> {
      return requestJson<IBalanceSnapshot>(ctx, `/admin/users/${encodeURIComponent(userId)}/spend`, {
        method: "POST",
        body: { amount: amountDecimalString },
        auth: true,
      });
    },

    async adminPatchUser(userId: string, payload: IAdminPatchUserPayload): Promise<IUserProfile> {
      const body: Record<string, string | boolean> = {};
      if (payload.name !== undefined) {
        body.name = payload.name;
      }
      if (payload.allow_negative_balance !== undefined) {
        body.allow_negative_balance = payload.allow_negative_balance;
      }
      return requestJson<IUserProfile>(ctx, `/admin/users/${encodeURIComponent(userId)}`, {
        method: "PATCH",
        body,
        auth: true,
      });
    },
  };
}
