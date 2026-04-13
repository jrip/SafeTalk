/** Контракты ответов/запросов backend — только `interface`, явные поля. */

export interface ILoginCredentials {
  readonly login: string;
  readonly password: string;
}

export interface IRegisterPayload {
  readonly login: string;
  readonly password: string;
  readonly name: string;
}

export interface IVerifyEmailPayload {
  readonly login: string;
  readonly code: string;
}

export interface IUserProfile {
  readonly id: string;
  readonly name: string;
  readonly role: string;
  readonly allow_negative_balance: boolean;
  readonly identities: readonly string[];
}

export interface IAdminUserRow {
  readonly id: string;
  readonly name: string;
  readonly role: string;
  readonly allow_negative_balance: boolean;
  readonly primary_email: string | null;
  readonly token_count: string;
}

export interface IAdminStats {
  readonly users_count: number;
  readonly history_records_count: number;
  readonly ledger_entries_count: number;
  readonly total_tokens_in_balances: string;
}

/** Тело `PATCH /users/me` — см. `UpdateMeRequest` в backend. */
export interface IUpdateMyProfilePayload {
  readonly name: string;
}

export interface IRegisterResult extends IUserProfile {
  /** Демо: код верификации из ответа API (см. backend TODO). */
  readonly temporary_only_for_test_todo?: string;
}

export interface IBalanceSnapshot {
  readonly user_id: string;
  readonly token_count: string;
}

export interface IMlCatalogItem {
  readonly id: string;
  readonly slug: string;
  readonly name: string;
  readonly description: string;
  readonly price_per_character: string;
  readonly is_default: boolean;
}

export interface ICreatePredictionPayload {
  readonly modelId: string;
  readonly text: string;
}

export interface IPredictionTaskDetail {
  readonly task_id: string;
  readonly user_id: string;
  readonly model_id: string;
  readonly text: string;
  readonly status: string;
  readonly charged_tokens: string;
  readonly created_at: string;
  readonly completed_at: string | null;
  readonly result_summary: string | null;
  readonly is_toxic: boolean | null;
  readonly toxicity_probability: string | null;
  readonly toxicity_breakdown: Readonly<Record<string, number>> | null;
}

export interface IHistoryEntry {
  readonly id: string;
  readonly user_id: string;
  readonly request: string;
  readonly result: string;
  readonly created_at: string;
  readonly ml_model_id: string | null;
  readonly ml_task_id: string | null;
  readonly tokens_charged: string | null;
}

export interface ILedgerEntry {
  readonly id: string;
  readonly user_id: string;
  readonly kind: string;
  readonly amount: string;
  readonly task_id: string | null;
  readonly created_at: string;
}

export interface IPollPredictionOptions {
  readonly intervalMs?: number;
  readonly deadlineMs?: number;
}
