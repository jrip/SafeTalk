import { Typography } from "antd";
import dayjs from "dayjs";
import type { ReactNode } from "react";
import type { IMlCatalogItem, IPredictionTaskDetail } from "../client/contracts";
import { formatLedgerAmountByKind } from "../formatCredits";

export function modelTitleById(
  modelId: string | null | undefined,
  mlModels: readonly IMlCatalogItem[],
): string {
  if (!modelId) {
    return "—";
  }
  const m = mlModels.find((x) => x.id === modelId);
  return m?.name ?? modelId;
}

export type IMlTaskDetailTableOptions = {
  /** Для админки: показать владельца задачи. */
  readonly includeUserId?: boolean;
};

export function mlTaskDetailTableRows(
  d: IPredictionTaskDetail,
  mlModels: readonly IMlCatalogItem[],
  opts?: IMlTaskDetailTableOptions,
): readonly { key: string; field: string; value: ReactNode }[] {
  const breakdown =
    d.toxicity_breakdown && Object.keys(d.toxicity_breakdown).length > 0
      ? Object.entries(d.toxicity_breakdown)
          .map(([k, v]) => `${k}: ${v}`)
          .join("\n")
      : null;
  const head: { key: string; field: string; value: ReactNode }[] = [
    {
      key: "task_id",
      field: "ID задачи",
      value: (
        <Typography.Text code copyable>
          {d.task_id}
        </Typography.Text>
      ),
    },
  ];
  if (opts?.includeUserId) {
    head.push({
      key: "user_id",
      field: "ID пользователя",
      value: (
        <Typography.Text code copyable>
          {d.user_id}
        </Typography.Text>
      ),
    });
  }
  return [
    ...head,
    { key: "status", field: "Статус", value: d.status },
    { key: "model", field: "Модель", value: modelTitleById(d.model_id, mlModels) },
    { key: "charged", field: "Списано кредитов", value: formatLedgerAmountByKind("debit", d.charged_tokens) },
    {
      key: "created",
      field: "Создано",
      value: dayjs(d.created_at).format("YYYY-MM-DD HH:mm:ss"),
    },
    {
      key: "completed",
      field: "Завершено",
      value: d.completed_at ? dayjs(d.completed_at).format("YYYY-MM-DD HH:mm:ss") : "—",
    },
    {
      key: "text",
        field: "Текст для проверки",
      value: (
        <Typography.Paragraph style={{ whiteSpace: "pre-wrap", marginBottom: 0, maxHeight: 200, overflow: "auto" }}>
          {d.text}
        </Typography.Paragraph>
      ),
    },
    {
      key: "toxic",
      field: "Токсичность",
      value: d.is_toxic === null ? "—" : d.is_toxic ? "да" : "нет",
    },
    {
      key: "prob",
      field: "Вероятность токсичности",
      value: d.toxicity_probability ?? "—",
    },
    {
      key: "breakdown",
      field: "Разбивка по классам",
      value: breakdown ? (
        <Typography.Paragraph style={{ whiteSpace: "pre-wrap", marginBottom: 0, fontFamily: "inherit" }}>
          {breakdown}
        </Typography.Paragraph>
      ) : (
        "—"
      ),
    },
  ];
}
