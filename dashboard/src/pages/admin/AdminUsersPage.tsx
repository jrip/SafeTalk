import { App, Space, Typography } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";
import type { IAdminUserRow } from "../../client/contracts";
import { useSafeTalkApi } from "../../client/ClientContext";
import { AdminUsersTable } from "./AdminUsersTable";

/** Страница маршрута: данные и мутации только через `ISafeTalkApiClient` из контекста. */
export default function AdminUsersPage() {
  const { message } = App.useApp();
  const api = useSafeTalkApi();
  const [rows, setRows] = useState<readonly IAdminUserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [amounts, setAmounts] = useState<Readonly<Record<string, number>>>({});
  const cancelledRef = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listAdminUsers();
      if (cancelledRef.current) {
        return;
      }
      setRows(list);
      setAmounts((prev) => {
        const next: Record<string, number> = { ...prev };
        for (const r of list) {
          if (next[r.id] == null) {
            next[r.id] = 100;
          }
        }
        return next;
      });
    } catch (e) {
      if (!cancelledRef.current) {
        message.error(e instanceof Error ? e.message : String(e));
        setRows([]);
      }
    } finally {
      if (!cancelledRef.current) {
        setLoading(false);
      }
    }
  }, [api, message]);

  useEffect(() => {
    cancelledRef.current = false;
    void load();
    return () => {
      cancelledRef.current = true;
    };
  }, [load]);

  const onAmountChange = useCallback((userId: string, value: number) => {
    setAmounts((prev) => ({ ...prev, [userId]: value }));
  }, []);

  const onTopupClick = useCallback(
    async (userId: string) => {
      const amt = amounts[userId] ?? 100;
      if (!amt || amt <= 0) {
        message.warning("Введите сумму больше нуля");
        return;
      }
      try {
        await api.adminTopUpUserBalance(userId, String(amt));
        message.success("Баланс пополнен");
        await load();
      } catch (e) {
        message.error(e instanceof Error ? e.message : String(e));
      }
    },
    [amounts, api, load, message],
  );

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 0, fontWeight: 600, fontSize: 15 }}>
        Пользователи — балансы и пополнение (админ).
      </Typography.Title>
      <AdminUsersTable
        rows={rows}
        loading={loading}
        amounts={amounts}
        onAmountChange={onAmountChange}
        onTopupClick={onTopupClick}
      />
    </Space>
  );
}
