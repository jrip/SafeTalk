import { Button, InputNumber, Space, Table } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useMemo } from "react";
import type { IAdminUserRow } from "../../client/contracts";
import { formatMoney2 } from "../../formatCredits";

export interface IAdminUsersTableProps {
  readonly rows: readonly IAdminUserRow[];
  readonly loading: boolean;
  readonly amounts: Readonly<Record<string, number>>;
  readonly onAmountChange: (userId: string, value: number) => void;
  readonly onTopupClick: (userId: string) => void;
}

export function AdminUsersTable(props: IAdminUsersTableProps) {
  const { rows, loading, amounts, onAmountChange, onTopupClick } = props;

  const columns: ColumnsType<IAdminUserRow> = useMemo(
    () => [
      {
        title: "Email",
        dataIndex: "primary_email",
        ellipsis: true,
        render: (v: string | null | undefined) => v ?? "—",
      },
      {
        title: "Имя",
        dataIndex: "name",
        ellipsis: true,
      },
      {
        title: "Роль",
        dataIndex: "role",
        width: 100,
      },
      {
        title: "Баланс",
        dataIndex: "token_count",
        width: 130,
        align: "right",
        render: (v: string | undefined) => formatMoney2(v ?? null),
      },
      {
        title: "Пополнение",
        key: "top",
        width: 240,
        render: (_: unknown, record: IAdminUserRow) => (
          <Space size="small" wrap>
            <InputNumber
              min={1}
              value={amounts[record.id] ?? 100}
              onChange={(v) => onAmountChange(record.id, Number(v) || 1)}
              style={{ width: 110 }}
            />
            <Button type="primary" size="small" onClick={() => onTopupClick(record.id)}>
              Пополнить
            </Button>
          </Space>
        ),
      },
    ],
    [amounts, onAmountChange, onTopupClick],
  );

  return (
    <Table<IAdminUserRow>
      rowKey="id"
      loading={loading}
      columns={columns}
      dataSource={[...rows]}
      pagination={{ pageSize: 12 }}
    />
  );
}
