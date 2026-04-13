import { CheckOutlined, CloseOutlined, CopyOutlined, EditOutlined, UserOutlined } from "@ant-design/icons";
import { App, Button, Card, Descriptions, Input, Space, Spin, Typography, theme } from "antd";
import { useCallback, useEffect, useState } from "react";
import type { IUserProfile } from "../client/contracts";
import { useSafeTalkApi } from "../client/ClientContext";
import { identitiesWithoutTypePrefixes } from "../identityDisplay";

/** Одинаковый зазор между текстом и иконкой (копирование / редактирование). */
const PROFILE_TEXT_ICON_GAP = 2;

export default function AccountPage() {
  const { message } = App.useApp();
  const { token } = theme.useToken();
  const api = useSafeTalkApi();
  const [me, setMe] = useState<IUserProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingName, setEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState("");
  const [savingName, setSavingName] = useState(false);

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const u = await api.getCurrentUser();
      setMe(u);
      setEditingName(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  async function saveNameFromDraft() {
    const name = nameDraft.trim();
    if (name.length === 0) {
      message.warning("Введите непустое имя");
      return;
    }
    setSavingName(true);
    try {
      const updated = await api.updateMyProfile({ name });
      setMe(updated);
      setEditingName(false);
      message.success("Имя сохранено");
    } catch (e) {
      message.error(e instanceof Error ? e.message : String(e));
    } finally {
      setSavingName(false);
    }
  }

  function cancelNameEdit() {
    setEditingName(false);
    if (me) {
      setNameDraft(me.name);
    }
  }

  async function copyUserId(id: string) {
    try {
      await navigator.clipboard.writeText(id);
      message.success("ID скопирован");
    } catch {
      message.error("Не удалось скопировать ID");
    }
  }

  return (
    <div>
      <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 16, fontWeight: 600, fontSize: 15 }}>
        Ваши данные
      </Typography.Title>

      <Card>
        <Spin spinning={loading}>
          {error ? (
            <Typography.Text type="danger">{error}</Typography.Text>
          ) : me ? (
            <Descriptions title="Пользователь" extra={<UserOutlined />} bordered column={1} size="middle">
              <Descriptions.Item label="ID">
                <Space size={PROFILE_TEXT_ICON_GAP} align="center" wrap>
                  <Typography.Text code>{me.id}</Typography.Text>
                  <Button
                    type="text"
                    size="small"
                    icon={<CopyOutlined />}
                    style={{ color: token.colorLink }}
                    onClick={() => void copyUserId(me.id)}
                    aria-label="Копировать ID"
                  />
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Имя">
                {editingName ? (
                  <Space size={PROFILE_TEXT_ICON_GAP} wrap align="center">
                    <Input
                      value={nameDraft}
                      onChange={(e) => setNameDraft(e.target.value)}
                      placeholder="Имя"
                      maxLength={256}
                      style={{ maxWidth: 320 }}
                      disabled={savingName}
                      onPressEnter={() => void saveNameFromDraft()}
                    />
                    <Button
                      type="primary"
                      icon={<CheckOutlined />}
                      loading={savingName}
                      onClick={() => void saveNameFromDraft()}
                      aria-label="Сохранить имя"
                    />
                    <Button
                      type="text"
                      icon={<CloseOutlined />}
                      onClick={cancelNameEdit}
                      disabled={savingName}
                      aria-label="Отмена"
                    />
                  </Space>
                ) : (
                  <Space size={PROFILE_TEXT_ICON_GAP} align="center" wrap>
                    <span>{me.name}</span>
                    <Button
                      type="text"
                      size="small"
                      icon={<EditOutlined />}
                      style={{ color: token.colorLink }}
                      onClick={() => {
                        setNameDraft(me.name);
                        setEditingName(true);
                      }}
                      aria-label="Редактировать имя"
                    />
                  </Space>
                )}
              </Descriptions.Item>
              {me.role === "admin" ? <Descriptions.Item label="Роль">{me.role}</Descriptions.Item> : null}
              <Descriptions.Item label="Идентичности">
                {identitiesWithoutTypePrefixes(me.identities)}
              </Descriptions.Item>
              {me.allow_negative_balance ? (
                <Descriptions.Item label="Отрицательный баланс разрешён">Да</Descriptions.Item>
              ) : null}
            </Descriptions>
          ) : null}
        </Spin>
      </Card>
    </div>
  );
}
