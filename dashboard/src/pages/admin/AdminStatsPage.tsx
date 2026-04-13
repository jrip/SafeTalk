import { App, Card, Col, Row, Space, Statistic, Typography } from "antd";
import { useCallback, useEffect, useState } from "react";
import type { IAdminStats } from "../../client/contracts";
import { useSafeTalkApi } from "../../client/ClientContext";
import { formatMoney2 } from "../../formatCredits";

export default function AdminStatsPage() {
  const { message } = App.useApp();
  const api = useSafeTalkApi();
  const [stats, setStats] = useState<IAdminStats | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setStats(await api.getAdminStats());
    } catch (e) {
      message.error(e instanceof Error ? e.message : String(e));
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [api, message]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 0, fontWeight: 600, fontSize: 15 }}>
        Сводная статистика (админ).
      </Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic title="Пользователей" value={stats?.users_count ?? "—"} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic title="Записей в истории ML" value={stats?.history_records_count ?? "—"} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic title="Строк в журнале баланса" value={stats?.ledger_entries_count ?? "—"} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic
              title="Сумма кредитов на всех кошельках"
              value={stats ? formatMoney2(stats.total_tokens_in_balances) : "—"}
            />
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
