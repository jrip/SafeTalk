import { App, Card, Col, Row, Space, Statistic, Typography } from "antd";
import { useCallback, useEffect, useState } from "react";
import type { IAdminStats } from "../../client/contracts";
import { useSafeTalkApi } from "../../client/ClientContext";
import { formatMoney2 } from "../../formatCredits";

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) {
    return value;
  }
  return d.toLocaleString("ru-RU");
}

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
        <Col xs={24} sm={12} md={8}>
          <Card loading={loading}>
            <Statistic title="Пользователей всего" value={stats?.users_count ?? "—"} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card loading={loading}>
            <Statistic title="Из них админов" value={stats?.admins_count ?? "—"} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card loading={loading}>
            <Statistic title="Последняя регистрация" value={formatDateTime(stats?.last_registration_at)} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card loading={loading}>
            <Statistic title="Всего денег внесено" value={stats ? formatMoney2(stats.total_credits) : "—"} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card loading={loading}>
            <Statistic title="Всего денег потрачено" value={stats ? formatMoney2(stats.total_debits) : "—"} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card loading={loading}>
            <Statistic
              title="Сумма положительных балансов"
              value={stats ? formatMoney2(stats.positive_balances_sum) : "—"}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card loading={loading}>
            <Statistic title="Задач ML всего" value={stats?.ml_tasks_total ?? "—"} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card loading={loading}>
            <Statistic title="В работе" value={stats?.ml_tasks_pending ?? "—"} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card loading={loading}>
            <Statistic title="Закончено" value={stats?.ml_tasks_completed ?? "—"} />
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
