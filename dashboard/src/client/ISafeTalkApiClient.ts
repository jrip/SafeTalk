import type {
  IBalanceSnapshot,
  ICreatePredictionPayload,
  IAdminStats,
  IAdminUserRow,
  IHistoryEntry,
  ILedgerEntry,
  ILoginCredentials,
  IMlCatalogItem,
  IPollPredictionOptions,
  IPredictionTaskDetail,
  IRegisterPayload,
  IRegisterResult,
  IAdminPatchUserPayload,
  IUpdateMyProfilePayload,
  IUserProfile,
  IVerifyEmailPayload,
} from "./contracts";

/**
 * Единая точка доступа к HTTP API SafeTalk.
 * Реализация — `createSafeTalkApiClient`; в UI — `useSafeTalkApi()` из `ClientContext`.
 */
export interface ISafeTalkApiClient {
  login(credentials: ILoginCredentials): Promise<string>;
  register(payload: IRegisterPayload): Promise<IRegisterResult>;
  verifyEmail(payload: IVerifyEmailPayload): Promise<void>;
  getCurrentUser(): Promise<IUserProfile>;
  getAdminUser(userId: string): Promise<IUserProfile>;
  updateMyProfile(payload: IUpdateMyProfilePayload): Promise<IUserProfile>;
  getMyBalance(): Promise<IBalanceSnapshot>;
  topUpMyBalance(amountDecimalString: string): Promise<IBalanceSnapshot>;
  listMlModels(): Promise<readonly IMlCatalogItem[]>;
  createPredictionTask(payload: ICreatePredictionPayload): Promise<string>;
  getPredictionTask(taskId: string): Promise<IPredictionTaskDetail>;
  pollPredictionTask(taskId: string, options?: IPollPredictionOptions): Promise<IPredictionTaskDetail>;
  listMyHistory(): Promise<readonly IHistoryEntry[]>;
  listMyLedger(): Promise<readonly ILedgerEntry[]>;
  listAdminUsers(): Promise<readonly IAdminUserRow[]>;
  getAdminStats(): Promise<IAdminStats>;
  listAdminLedger(limit?: number): Promise<readonly ILedgerEntry[]>;
  listAdminHistory(limit?: number): Promise<readonly IHistoryEntry[]>;
  getAdminMlTask(taskId: string): Promise<IPredictionTaskDetail>;
  adminTopUpUserBalance(userId: string, amountDecimalString: string): Promise<IBalanceSnapshot>;
  /** Списание токенов с кошелька пользователя (админ, POST `/balance/{id}/spend`). */
  adminSpendUserBalance(userId: string, amountDecimalString: string): Promise<IBalanceSnapshot>;
  adminPatchUser(userId: string, payload: IAdminPatchUserPayload): Promise<IUserProfile>;
}
