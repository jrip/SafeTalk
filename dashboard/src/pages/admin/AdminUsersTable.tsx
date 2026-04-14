import { Table } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useMemo } from "react";
import type { IAdminUserRow } from "../../client/contracts";
import { formatMoney2 } from "../../formatCredits";

export interface IAdminUsersTableProps {
  readonly rows: readonly IAdminUserRow[];
  readonly loading: boolean;
  readonly onOpenUser: (row: IAdminUserRow) => void;
}

export function AdminUsersTable(props: IAdminUsersTableProps) {
  const { rows, loading, onOpenUser } = props;

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
    ],
    [],
  );

  return (
    <Table<IAdminUserRow>
      rowKey="id"
      loading={loading}
      columns={columns}
      dataSource={[...rows]}
      pagination={{ pageSize: 12 }}
      onRow={(record) => ({
        onClick: () => onOpenUser(record),
        style: { cursor: "pointer" },
      })}
    />
  );
}
