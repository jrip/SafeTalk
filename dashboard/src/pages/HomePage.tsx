import { WalletOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Col, Row, Space, Statistic, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useSafeTalkApi } from "../client/ClientContext";
import { CREDITS_NEGATIVE_COLOR, formatCredits } from "../formatCredits";

const overviewCardBodyFlex = {
  flex: 1,
  display: "flex" as const,
  flexDirection: "column" as const,
  minHeight: 0,
};

const overviewCardFooter = { marginTop: "auto", paddingTop: 8 };

export default function HomePage() {
  const api = useSafeTalkApi();
  const [balance, setBalance] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let c = false;
    (async () => {
      try {
        const b = await api.getMyBalance();
        if (!c) {
          setBalance(b.token_count);
        }
      } catch (e) {
        if (!c) {
          setErr(e instanceof Error ? e.message : String(e));
        }
      }
    })();
    return () => {
      c = true;
    };
  }, [api]);

  const creditsFmt = useMemo(() => formatCredits(balance), [balance]);

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      {err ? <Alert type="error" message={err} showIcon /> : null}

      <Row gutter={[16, 16]} align="stretch">
        <Col xs={24} sm={12} md={8} style={{ display: "flex" }}>
          <Card
            title="Баланс"
            style={{ width: "100%", flex: 1, display: "flex", flexDirection: "column" }}
            styles={{ body: overviewCardBodyFlex }}
          >
            <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
              Кредиты тратятся на проверки текста через ML. При нуле или отрицательном балансе новые проверки недоступны —
              пополните счёт на странице баланса.
            </Typography.Paragraph>
            <Statistic
              prefix={<WalletOutlined />}
              title="Кредиты"
              value={creditsFmt.display}
              valueStyle={creditsFmt.isNegative ? { color: CREDITS_NEGATIVE_COLOR } : undefined}
              loading={balance === null && !err}
            />
            <div style={overviewCardFooter}>
              <Button type="link" style={{ paddingLeft: 0 }}>
                <Link to="/balance">Пополнить</Link>
              </Button>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} style={{ display: "flex" }}>
          <Card
            title="Задача"
            style={{ width: "100%", flex: 1, display: "flex", flexDirection: "column" }}
            styles={{ body: overviewCardBodyFlex }}
          >
            <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
              Проверка текста на токсичность: выбор модели, ввод вручную или загрузка файла, отправка задачи и просмотр
              результата.
            </Typography.Paragraph>
            <div style={overviewCardFooter}>
              <Link to="/predict">Открыть задачу →</Link>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} style={{ display: "flex" }}>
          <Card
            title="История"
            style={{ width: "100%", flex: 1, display: "flex", flexDirection: "column" }}
            styles={{ body: overviewCardBodyFlex }}
          >
            <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
              Журнал задач ML и операций по балансу: что проверяли, сколько списали и когда.
            </Typography.Paragraph>
            <div style={overviewCardFooter}>
              <Link to="/history">Открыть историю →</Link>
            </div>
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
