/** Цвет «минус / опасность» в духе лендинга (`--danger`). */
export const CREDITS_NEGATIVE_COLOR = "#ff6b6b";

export interface IFormattedCredits {
  /** Текст для `Statistic` / подписей: 2 знака после точки, группы через запятую; при отрицательном — ведущий пробел и минус. */
  readonly display: string;
  readonly isNegative: boolean;
}

function parseCreditsNumber(raw: string): number | null {
  const trimmed = raw.trim().replace(/\s/g, "");
  if (trimmed === "") {
    return null;
  }
  const normalized = trimmed.replace(/,/g, "");
  const n = Number(normalized);
  return Number.isFinite(n) ? n : null;
}

/**
 * Формат: `6,410.00`; отрицательные — ` -6,410.00` (пробел перед минусом), красный через `valueStyle`.
 */
export function formatCredits(raw: string | null | undefined): IFormattedCredits {
  if (raw === null || raw === undefined) {
    return { display: "—", isNegative: false };
  }
  const s = String(raw);
  const n = parseCreditsNumber(s);
  if (n === null) {
    return { display: s.trim() === "" ? "—" : s, isNegative: false };
  }

  const formattedAbs = Math.abs(n).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  if (n < 0) {
    return { display: ` -${formattedAbs}`, isNegative: true };
  }
  return { display: formattedAbs, isNegative: false };
}

/**
 * Любая денежная сумма / кредиты в UI: ровно 2 знака после десятичной точки, разделитель тысяч как в `formatCredits`.
 */
export function formatMoney2(raw: string | null | undefined): string {
  if (raw === null || raw === undefined) {
    return "—";
  }
  const s = String(raw);
  const n = parseCreditsNumber(s);
  if (n === null) {
    const t = s.trim();
    return t === "" ? "—" : t;
  }
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * Сумма в журнале: явный «+» для зачислений, «−» для списаний, всегда 2 знака после точки.
 */
export function formatSignedMoney2(raw: string | null | undefined): string {
  if (raw === null || raw === undefined) {
    return "—";
  }
  const n = parseCreditsNumber(String(raw).trim().replace(/^\+/, ""));
  if (n === null) {
    const t = String(raw).trim();
    return t === "" ? "—" : t;
  }
  const abs = Math.abs(n).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  if (n > 0) {
    return `+${abs}`;
  }
  if (n < 0) {
    return `-${abs}`;
  }
  return abs;
}

/**
 * Запись журнала: в API `amount` для debit/credit хранится положительным, знак выводим по `kind`.
 */
export function formatLedgerAmountByKind(kind: string, raw: string | null | undefined): string {
  if (raw === null || raw === undefined) {
    return "—";
  }
  const n = parseCreditsNumber(String(raw).trim().replace(/^\+/, ""));
  if (n === null) {
    const t = String(raw).trim();
    return t === "" ? "—" : t;
  }
  const abs = Math.abs(n).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  if (kind === "debit") {
    return `-${abs}`;
  }
  if (kind === "credit") {
    return `+${abs}`;
  }
  return abs;
}
