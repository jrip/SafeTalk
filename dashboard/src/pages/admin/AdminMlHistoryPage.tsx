import { ReloadOutlined } from "@ant-design/icons";
import { App, Button, Card, Space, Spin, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { IHistoryEntry, IMlCatalogItem, IPredictionTaskDetail } from "../../client/contracts";
import { useSafeTalkApi } from "../../client/ClientContext";
import { DraggableModal } from "../../components/DraggableModal";
import { formatLedgerAmountByKind } from "../../formatCredits";
import { mlTaskDetailTableRows, modelTitleById } from "../../ml/mlTaskDetailTableRows";

export default function AdminMlHistoryPage() {
  const { message } = App.useApp();
  const api = useSafeTalkApi();
  const [rows, setRows] = useState<readonly IHistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [mlModels, setMlModels] = useState<readonly IMlCatalogItem[]>([]);
  const [detail, setDetail] = useState<IHistoryEntry | null>(null);
  const [taskDetail, setTaskDetail] = useState<IPredictionTaskDetail | null>(null);
  const [taskLoading, setTaskLoading] = useState(false);
  const [taskError, setTaskError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [h, models] = await Promise.all([api.listAdminHistory(800), api.listMlModels().catch(() => [])]);
      setRows(h);
      setMlModels(models);
    } catch (e) {
      message.error(e instanceof Error ? e.message : String(e));
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [api, message]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const taskId = detail?.ml_task_id?.trim();
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
      .getAdminMlTask(taskId)
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
  }, [api, detail]);

  const cols: ColumnsType<IHistoryEntry> = [
    {
      title: "Дата и время",
      dataIndex: "created_at",
      width: 180,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm:ss"),
    },
    {
      title: "Пользователь (id)",
      dataIndex: "user_id",
      minWidth: 280,
      ellipsis: false,
      render: (v: string) => (
        <Typography.Text code copyable style={{ wordBreak: "break-all", whiteSpace: "normal" }}>
          {v}
        </Typography.Text>
      ),
    },
    {
      title: "ID запроса",
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

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Space align="start" style={{ justifyContent: "space-between", width: "100%" }} wrap>
        <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 0, fontWeight: 600, fontSize: 15 }}>
          История задач ML — все пользователи.
        </Typography.Title>
        <Button icon={<ReloadOutlined />} onClick={() => void load()} loading={loading}>
          Обновить
        </Button>
      </Space>

      <Card>
        <Table
          rowKey="id"
          loading={loading}
          columns={cols}
          dataSource={[...rows]}
          pagination={{ pageSize: 15, showSizeChanger: true }}
          scroll={{ x: 1200 }}
          onRow={(record) => ({
            onClick: () => setDetail(record),
            style: { cursor: "pointer" },
          })}
        />
      </Card>

      <DraggableModal
        title="Задача ML"
        open={detail !== null}
        onCancel={() => {
          setDetail(null);
          setTaskDetail(null);
          setTaskError(null);
        }}
        footer={null}
        width={820}
        destroyOnClose
      >
        {detail ? (
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Typography.Paragraph style={{ marginBottom: 0 }}>
              <Typography.Text type="secondary">Пользователь: </Typography.Text>
              <Typography.Text code copyable>
                {detail.user_id}
              </Typography.Text>
            </Typography.Paragraph>
            {detail.ml_task_id ? (
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
                      { title: "Значение", dataIndex: "value", render: (v: ReactNode) => v },
                    ]}
                    dataSource={[...mlTaskDetailTableRows(taskDetail, mlModels, { includeUserId: true })]}
                  />
                ) : null}
              </>
            ) : (
              <Typography.Text type="secondary">К записи не привязана задача ML.</Typography.Text>
            )}
          </Space>
        ) : null}
      </DraggableModal>
    </Space>
  );
}
