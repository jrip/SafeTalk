import { SafetyCertificateOutlined } from "@ant-design/icons";
import { App, Button, Card, Form, Input, Typography } from "antd";
import { useLocation, useNavigate } from "react-router-dom";
import { isUnknownRecord } from "../client/http";
import { useSafeTalkApi } from "../client/ClientContext";

export interface IVerifyEmailFormValues {
  readonly login: string;
  readonly code: string;
}

export interface IVerifyEmailRouteState {
  readonly login?: string;
  readonly code?: string;
}

function readVerifyEmailRouteState(raw: unknown): IVerifyEmailRouteState {
  if (!isUnknownRecord(raw)) {
    return {};
  }
  const login = raw.login;
  const code = raw.code;
  return {
    ...(typeof login === "string" ? { login } : {}),
    ...(typeof code === "string" ? { code } : {}),
  };
}

export default function VerifyEmailPage() {
  const { message } = App.useApp();
  const api = useSafeTalkApi();
  const nav = useNavigate();
  const loc = useLocation();
  const st = readVerifyEmailRouteState(loc.state);

  async function onFinish(v: IVerifyEmailFormValues) {
    try {
      await api.verifyEmail({ login: v.login.trim(), code: v.code.trim() });
      message.success("Email подтверждён. Войдите в систему.");
      nav("/login", { replace: true });
    } catch (e) {
      message.error(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div style={{ maxWidth: 440, margin: "48px auto", padding: "0 16px" }}>
      <Card title="Подтверждение email">
        <Typography.Paragraph type="secondary">
          <Typography.Link onClick={() => nav("/login")}>Ко входу</Typography.Link> ·{" "}
          <Typography.Link onClick={() => nav("/register")}>Назад к регистрации</Typography.Link>
        </Typography.Paragraph>
        <Form<IVerifyEmailFormValues>
          layout="vertical"
          onFinish={onFinish}
          initialValues={{ login: st.login ?? "", code: st.code ?? "" }}
          requiredMark="optional"
        >
          <Form.Item name="login" label="Email" rules={[{ required: true }, { type: "email" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="code" label="Код из письма" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" icon={<SafetyCertificateOutlined />} block>
              Подтвердить
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
