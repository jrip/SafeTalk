import type {
  IBalanceSnapshot,
  ICreatePredictionPayload,
  IHistoryEntry,
  ILedgerEntry,
  ILoginCredentials,
  IMlCatalogItem,
  IPollPredictionOptions,
  IPredictionTaskDetail,
  IRegisterPayload,
  IRegisterResult,
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
  updateMyProfile(payload: IUpdateMyProfilePayload): Promise<IUserProfile>;
  getMyBalance(): Promise<IBalanceSnapshot>;
  topUpMyBalance(amountDecimalString: string): Promise<IBalanceSnapshot>;
  listMlModels(): Promise<readonly IMlCatalogItem[]>;
  createPredictionTask(payload: ICreatePredictionPayload): Promise<string>;
  getPredictionTask(taskId: string): Promise<IPredictionTaskDetail>;
  pollPredictionTask(taskId: string, options?: IPollPredictionOptions): Promise<IPredictionTaskDetail>;
  listMyHistory(): Promise<readonly IHistoryEntry[]>;
  listMyLedger(): Promise<readonly ILedgerEntry[]>;
}
