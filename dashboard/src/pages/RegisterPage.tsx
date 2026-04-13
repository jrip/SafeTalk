import { UserAddOutlined } from "@ant-design/icons";
import { App, Button, Card, Form, Input, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { useSafeTalkApi } from "../client/ClientContext";

export interface IRegisterFormValues {
  readonly name: string;
  readonly login: string;
  readonly password: string;
  readonly password2: string;
}

export default function RegisterPage() {
  const { message } = App.useApp();
  const api = useSafeTalkApi();
  const nav = useNavigate();

  async function onFinish(v: IRegisterFormValues) {
    if (v.password !== v.password2) {
      message.error("Пароли не совпадают");
      return;
    }
    try {
      const res = await api.register({
        login: v.login.trim(),
        password: v.password,
        name: v.name.trim(),
      });
      message.success("Регистрация создана. Подтвердите email.");
      nav("/verify-email", {
        replace: false,
        state: { login: v.login.trim(), code: res.temporary_only_for_test_todo ?? "" },
      });
    } catch (e) {
      message.error(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div style={{ maxWidth: 440, margin: "48px auto", padding: "0 16px" }}>
      <Card title="Регистрация">
        <Typography.Paragraph type="secondary">
          Уже есть аккаунт? <Typography.Link onClick={() => nav("/login")}>Войти</Typography.Link>
        </Typography.Paragraph>
        <Form<IRegisterFormValues> layout="vertical" onFinish={onFinish} requiredMark="optional">
          <Form.Item name="name" label="Имя" rules={[{ required: true, message: "Введите имя" }]}>
            <Input autoComplete="name" />
          </Form.Item>
          <Form.Item
            name="login"
            label="Email"
            rules={[
              { required: true, message: "Введите email" },
              { type: "email", message: "Некорректный email" },
            ]}
          >
            <Input autoComplete="email" />
          </Form.Item>
          <Form.Item name="password" label="Пароль" rules={[{ required: true, min: 1, message: "Введите пароль" }]}>
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            name="password2"
            label="Пароль ещё раз"
            rules={[{ required: true, message: "Повторите пароль" }]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" icon={<UserAddOutlined />} block>
              Зарегистрироваться
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
