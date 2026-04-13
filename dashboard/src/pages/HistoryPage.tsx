import { ReloadOutlined } from "@ant-design/icons";
import { App, Button, Card, Modal, Space, Spin, Table, Tabs, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { IHistoryEntry, ILedgerEntry, IMlCatalogItem, IPredictionTaskDetail } from "../client/contracts";
import { useSafeTalkApi } from "../client/ClientContext";
import { formatMoney2, formatSignedMoney2 } from "../formatCredits";

export default function HistoryPage() {
  const { message } = App.useApp();
  const api = useSafeTalkApi();
  const [hist, setHist] = useState<readonly IHistoryEntry[]>([]);
  const [ledger, setLedger] = useState<readonly ILedgerEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [historyDetail, setHistoryDetail] = useState<IHistoryEntry | null>(null);
  const [ledgerDetail, setLedgerDetail] = useState<ILedgerEntry | null>(null);
  const [taskDetail, setTaskDetail] = useState<IPredictionTaskDetail | null>(null);
  const [taskLoading, setTaskLoading] = useState(false);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [mlModels, setMlModels] = useState<readonly IMlCatalogItem[]>([]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [h, l] = await Promise.all([api.listMyHistory(), api.listMyLedger()]);
      setHist(h);
      setLedger(l);
      try {
        setMlModels(await api.listMlModels());
      } catch {
        setMlModels([]);
      }
    } catch (e) {
      message.error(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [api, message]);

  function modelTitleById(modelId: string | null | undefined): string {
    if (!modelId) {
      return "—";
    }
    const m = mlModels.find((x) => x.id === modelId);
    return m?.name ?? modelId;
  }

  function taskDetailTableRows(d: IPredictionTaskDetail): readonly { key: string; field: string; value: ReactNode }[] {
    const breakdown =
      d.toxicity_breakdown && Object.keys(d.toxicity_breakdown).length > 0
        ? Object.entries(d.toxicity_breakdown)
            .map(([k, v]) => `${k}: ${v}`)
            .join("\n")
        : null;
    return [
      {
        key: "task_id",
        field: "ID задачи",
        value: (
          <Typography.Text code copyable>
            {d.task_id}
          </Typography.Text>
        ),
      },
      { key: "status", field: "Статус", value: d.status },
      { key: "model", field: "Модель", value: modelTitleById(d.model_id) },
      { key: "charged", field: "Списано кредитов", value: formatMoney2(d.charged_tokens) },
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
        field: "Текст запроса",
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

  function ledgerOperationLabel(kind: string): string {
    switch (kind) {
      case "debit":
        return "Списание";
      case "credit":
        return "Пополнение";
      default:
        return kind;
    }
  }

  function ledgerDetailTableRows(e: ILedgerEntry): readonly { key: string; field: string; value: ReactNode }[] {
    return [
      {
        key: "id",
        field: "ID записи",
        value: (
          <Typography.Text code copyable>
            {e.id}
          </Typography.Text>
        ),
      },
      {
        key: "user_id",
        field: "ID пользователя",
        value: (
          <Typography.Text code copyable>
            {e.user_id}
          </Typography.Text>
        ),
      },
      { key: "kind", field: "Операция", value: ledgerOperationLabel(e.kind) },
      { key: "amount", field: "Сумма", value: formatSignedMoney2(e.amount) },
      {
        key: "task_id",
        field: "ID задачи ML",
        value: e.task_id ? (
          <Typography.Text code copyable>
            {e.task_id}
          </Typography.Text>
        ) : (
          "—"
        ),
      },
      {
        key: "created_at",
        field: "Дата и время",
        value: dayjs(e.created_at).format("YYYY-MM-DD HH:mm:ss"),
      },
    ];
  }

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    const taskId = historyDetail?.ml_task_id?.trim();
    if (!taskId) {
      setTaskDetail(null);
      setTaskError(null);
      setTaskLoading(false);
      return;
    }
    let cancelled = false;
    setTaskLoading(true);
    setTaskError(null);
    setTaskDetail(null);
    void api
      .getPredictionTask(taskId)
      .then((d) => {
        if (!cancelled) {
          setTaskDetail(d);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setTaskError(e instanceof Error ? e.message : String(e));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setTaskLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [api, historyDetail]);

  const histCols: ColumnsType<IHistoryEntry> = [
    {
      title: "Дата и время",
      dataIndex: "created_at",
      width: 170,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm:ss"),
    },
    {
      title: "Тип / запрос",
      key: "req",
      ellipsis: true,
      render: (_, r) => (
        <Typography.Text ellipsis title={r.request}>
          {r.request.slice(0, 120)}
          {r.request.length > 120 ? "…" : ""}
        </Typography.Text>
      ),
    },
    {
      title: "Результат (фрагмент)",
      dataIndex: "result",
      ellipsis: true,
      render: (v: string) => (v.length > 100 ? `${v.slice(0, 100)}…` : v),
    },
    {
      title: "Списание",
      dataIndex: "tokens_charged",
      width: 120,
      align: "right",
      render: (v: string | null) => (v == null ? "—" : formatMoney2(v)),
    },
    {
      title: "Статус",
      key: "st",
      width: 110,
      render: (_, r) => (r.result === "PENDING" ? "ожидание" : "завершено"),
    },
  ];

  const ledgerCols: ColumnsType<ILedgerEntry> = [
    {
      title: "Дата и время",
      dataIndex: "created_at",
      width: 190,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm:ss"),
    },
    {
      title: "Операция",
      dataIndex: "kind",
      width: 140,
      render: (k: string) => ledgerOperationLabel(k),
    },
    {
      title: "Сумма",
      dataIndex: "amount",
      width: 160,
      align: "right",
      render: (v: string) => formatSignedMoney2(v),
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Space align="start" style={{ justifyContent: "space-between", width: "100%" }} wrap>
        <div>
          <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 0, fontWeight: 600, fontSize: 15 }}>
            История запросов к сервису и движений по балансу.
          </Typography.Title>
        </div>
        <Button icon={<ReloadOutlined />} onClick={() => void loadAll()} loading={loading}>
          Обновить
        </Button>
      </Space>

      <Card>
        <Tabs
          items={[
            {
              key: "ml",
              label: "ML и предсказания",
              children: (
                <Table
                  rowKey="id"
                  loading={loading}
                  columns={histCols}
                  dataSource={[...hist]}
                  pagination={{ pageSize: 15, showSizeChanger: true }}
                  onRow={(record) => ({
                    onClick: () => setHistoryDetail(record),
                    style: { cursor: "pointer" },
                  })}
                />
              ),
            },
            {
              key: "ledger",
              label: "Операции по балансу",
              children: (
                <Table
                  rowKey="id"
                  loading={loading}
                  columns={ledgerCols}
                  dataSource={[...ledger]}
                  pagination={{ pageSize: 15, showSizeChanger: true }}
                  onRow={(record) => ({
                    onClick: () => setLedgerDetail(record),
                    style: { cursor: "pointer" },
                  })}
                />
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="Задача ML"
        open={historyDetail !== null}
        onCancel={() => {
          setHistoryDetail(null);
          setTaskDetail(null);
          setTaskError(null);
        }}
        footer={null}
        width={820}
        destroyOnClose
      >
        {historyDetail ? (
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            {historyDetail.ml_task_id ? (
              <>
                {taskLoading ? (
                  <Spin size="small" />
                ) : taskError ? (
                  <Typography.Text type="danger">{taskError}</Typography.Text>
                ) : taskDetail ? (
                  <Table
                    bordered
                    size="small"
                    pagination={false}
                    rowKey="key"
                    columns={[
                      { title: "Поле", dataIndex: "field", width: 220 },
                      {
                        title: "Значение",
                        dataIndex: "value",
                        render: (v: ReactNode) => v,
                      },
                    ]}
                    dataSource={[...taskDetailTableRows(taskDetail)]}
                  />
                ) : null}
              </>
            ) : (
              <Typography.Text type="secondary">К записи не привязана задача ML.</Typography.Text>
            )}
          </Space>
        ) : null}
      </Modal>

      <Modal
        title="Операция по балансу"
        open={ledgerDetail !== null}
        onCancel={() => setLedgerDetail(null)}
        footer={null}
        width={640}
        destroyOnClose
      >
        {ledgerDetail ? (
          <Table
            bordered
            size="small"
            pagination={false}
            rowKey="key"
            columns={[
              { title: "Поле", dataIndex: "field", width: 200 },
              { title: "Значение", dataIndex: "value", render: (v: ReactNode) => v },
            ]}
            dataSource={[...ledgerDetailTableRows(ledgerDetail)]}
          />
        ) : null}
      </Modal>
    </Space>
  );
}
