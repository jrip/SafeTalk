import { ReloadOutlined } from "@ant-design/icons";
import { App, Button, Card, Space, Spin, Table, Tabs, Typography } from "antd";
import { DraggableModal } from "../components/DraggableModal";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { IHistoryEntry, ILedgerEntry, IMlCatalogItem, IPredictionTaskDetail } from "../client/contracts";
import { useSafeTalkApi } from "../client/ClientContext";
import { formatLedgerAmountByKind } from "../formatCredits";
import { mlTaskDetailTableRows, modelTitleById } from "../ml/mlTaskDetailTableRows";

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
      { key: "amount", field: "Сумма", value: formatLedgerAmountByKind(e.kind, e.amount) },
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
      width: 180,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm:ss"),
    },
    {
      title: "ID задачи",
      key: "req_id",
      width: 200,
      ellipsis: true,
      render: (_, r) => {
        const id = r.ml_task_id?.trim() || r.id;
        return (
          <Typography.Text code copyable ellipsis title={id}>
            {id}
          </Typography.Text>
        );
      },
    },
    {
      title: "Кусок текста",
      key: "snippet",
      ellipsis: true,
      render: (_, r) => (
        <Typography.Text ellipsis title={r.request}>
          {r.request.slice(0, 120)}
          {r.request.length > 120 ? "…" : ""}
        </Typography.Text>
      ),
    },
    {
      title: "Статус",
      key: "st",
      width: 120,
      render: (_, r) => (r.result === "PENDING" ? "ожидание" : "завершено"),
    },
    {
      title: "Тип операции",
      key: "op_type",
      width: 160,
      ellipsis: true,
      render: (_, r) =>
        r.ml_model_id ? modelTitleById(r.ml_model_id, mlModels) : "Предсказание токсичности",
    },
    {
      title: "Сумма списания",
      dataIndex: "tokens_charged",
      width: 130,
      align: "right",
      render: (v: string | null) => (v == null ? "—" : formatLedgerAmountByKind("debit", v)),
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
      render: (v: string, row: ILedgerEntry) => formatLedgerAmountByKind(row.kind, v),
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Space align="start" style={{ justifyContent: "space-between", width: "100%" }} wrap>
        <div>
          <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 0, fontWeight: 600, fontSize: 15 }}>
            История проверок ML и операций по балансу.
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

      <DraggableModal
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
                    dataSource={[...mlTaskDetailTableRows(taskDetail, mlModels)]}
                  />
                ) : null}
              </>
            ) : (
              <Typography.Text type="secondary">К записи не привязана задача ML.</Typography.Text>
            )}
          </Space>
        ) : null}
      </DraggableModal>

      <DraggableModal
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
      </DraggableModal>
    </Space>
  );
}
