import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { HomeOutlined, LoginOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Flex, Form, Input, Typography } from "antd";
import { setToken } from "../auth";
import { useSafeTalkApi } from "../client/ClientContext";

export interface ILoginFormValues {
  readonly login: string;
  readonly password: string;
}

export default function LoginPage(): React.ReactElement {
  const api = useSafeTalkApi();
  const nav = useNavigate();
  const [form] = Form.useForm<ILoginFormValues>();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onFinish(values: ILoginFormValues) {
    setError(null);
    setBusy(true);
    try {
      const token = await api.login({ login: values.login.trim(), password: values.password });
      setToken(token);
      nav("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Flex justify="center" align="center" style={{ minHeight: "100vh", padding: 24 }}>
      <Card style={{ width: 400, maxWidth: "100%" }} title="Вход в кабинет">
        <Typography.Paragraph type="secondary" style={{ marginTop: 0 }}>
          <Button type="link" href="/" icon={<HomeOutlined />} style={{ padding: 0, height: "auto" }}>
            На главную
          </Button>
        </Typography.Paragraph>

        {error ? (
          <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />
        ) : null}

        <Form<ILoginFormValues>
          className="login-form-rounded"
          form={form}
          layout="vertical"
          onFinish={onFinish}
          requiredMark="optional"
        >
          <Form.Item
            name="login"
            label="Email"
            rules={[
              { required: true, message: "Введите email" },
              { type: "email", message: "Некорректный email" },
            ]}
          >
            <Input autoComplete="username" placeholder="you@example.com" size="large" style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="password" label="Пароль" rules={[{ required: true, message: "Введите пароль" }]}>
            <Input.Password
              className="login-password-rounded"
              autoComplete="current-password"
              placeholder="Пароль"
              size="large"
              style={{ width: "100%" }}
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 8 }}>
            <Button type="primary" htmlType="submit" block loading={busy} icon={<LoginOutlined />}>
              Войти
            </Button>
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="link" block onClick={() => nav("/register")} style={{ padding: 0 }}>
              Регистрация нового пользователя
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </Flex>
  );
}
