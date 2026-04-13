import { ReloadOutlined } from "@ant-design/icons";
import { App, Button, Card, Form, InputNumber, Space, Statistic, Typography } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSafeTalkApi } from "../client/ClientContext";
import { CREDITS_NEGATIVE_COLOR, formatCredits } from "../formatCredits";

export interface ITopUpFormValues {
  readonly amount?: number;
}

export default function BalancePage() {
  const { message } = App.useApp();
  const api = useSafeTalkApi();
  const [balance, setBalance] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const b = await api.getMyBalance();
      setBalance(b.token_count);
    } catch (e) {
      message.error(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [api, message]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const creditsFmt = useMemo(() => formatCredits(balance), [balance]);

  async function onTopup(amount: number) {
    if (!amount || amount <= 0) {
      message.warning("Введите сумму больше нуля");
      return;
    }
    try {
      const b = await api.topUpMyBalance(String(amount));
      setBalance(b.token_count);
      message.success("Баланс пополнен");
    } catch (e) {
      message.error(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 16, fontWeight: 600, fontSize: 15 }}>
        Кредиты для проверок: пополнение счёта и текущий баланс.
      </Typography.Title>

      <Card
        title="Текущий баланс"
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => void refresh()} loading={loading}>
            Обновить
          </Button>
        }
      >
        <Statistic
          title="Кредиты"
          value={creditsFmt.display}
          valueStyle={creditsFmt.isNegative ? { color: CREDITS_NEGATIVE_COLOR } : undefined}
          loading={balance === null && loading}
        />
      </Card>

      <Card title="Пополнить баланс">
        <Space wrap>
          {[100, 500, 1000, 5000].map((n) => (
            <Button key={n} type="primary" onClick={() => void onTopup(n)}>
              +{n}
            </Button>
          ))}
        </Space>
        <Form<ITopUpFormValues>
          layout="inline"
          style={{ marginTop: 24 }}
          onFinish={(v) => void onTopup(Number(v.amount))}
        >
          <Form.Item
            name="amount"
            rules={[{ required: true, message: "Сумма" }]}
            style={{ marginBottom: 0 }}
            label="Своя сумма"
          >
            <InputNumber min={1} max={1_000_000_000} style={{ width: 200 }} placeholder="Например, 250" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="default" htmlType="submit">
              Пополнить
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </Space>
  );
}
