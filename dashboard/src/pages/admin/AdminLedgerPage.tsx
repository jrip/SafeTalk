import { App, Space, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useCallback, useEffect, useState } from "react";
import type { ILedgerEntry } from "../../client/contracts";
import { useSafeTalkApi } from "../../client/ClientContext";
import { formatLedgerAmountByKind } from "../../formatCredits";

function ledgerKindRu(kind: string): string {
  switch (kind) {
    case "debit":
      return "Списание";
    case "credit":
      return "Пополнение";
    default:
      return kind;
  }
}

export default function AdminLedgerPage() {
  const { message } = App.useApp();
  const api = useSafeTalkApi();
  const [rows, setRows] = useState<readonly ILedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.listAdminLedger(800));
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

  const cols: ColumnsType<ILedgerEntry> = [
    {
      title: "Дата и время",
      dataIndex: "created_at",
      width: 180,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm:ss"),
    },
    {
      title: "Пользователь (id)",
      dataIndex: "user_id",
      ellipsis: false,
      render: (v: string) => (
        <Typography.Text code copyable style={{ wordBreak: "break-all", whiteSpace: "normal" }}>
          {v}
        </Typography.Text>
      ),
    },
    { title: "Операция", dataIndex: "kind", width: 120, render: (k: string) => ledgerKindRu(k) },
    {
      title: "Сумма",
      dataIndex: "amount",
      width: 120,
      align: "right",
      render: (v: string, row: ILedgerEntry) => formatLedgerAmountByKind(row.kind, v),
    },
    {
      title: "task_id",
      dataIndex: "task_id",
      ellipsis: true,
      render: (v: string | null) => v ?? "—",
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 0, fontWeight: 600, fontSize: 15 }}>
        Журнал операций по балансу — все пользователи (последние записи).
      </Typography.Title>
      <Table
        rowKey="id"
        loading={loading}
        columns={cols}
        dataSource={[...rows]}
        pagination={{ pageSize: 20 }}
        style={{ width: "100%" }}
      />
    </Space>
  );
}
