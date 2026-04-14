import {
  App,
  Button,
  Checkbox,
  Descriptions,
  Input,
  InputNumber,
  Modal,
  Space,
  Spin,
  Typography,
} from "antd";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { IAdminUserRow, IUserProfile } from "../../client/contracts";
import { useSafeTalkApi } from "../../client/ClientContext";
import { formatMoney2 } from "../../formatCredits";
import { AdminUsersTable } from "./AdminUsersTable";

/** Страница маршрута: данные и мутации только через `ISafeTalkApiClient` из контекста. */
export default function AdminUsersPage() {
  const { message, modal } = App.useApp();
  const api = useSafeTalkApi();
  const [rows, setRows] = useState<readonly IAdminUserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const cancelledRef = useRef(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [profile, setProfile] = useState<IUserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [draftAllowNegative, setDraftAllowNegative] = useState(false);
  const [topupAmount, setTopupAmount] = useState(100);
  const [debitAmount, setDebitAmount] = useState(100);
  const [savingProfile, setSavingProfile] = useState(false);
  const [toppingUp, setToppingUp] = useState(false);
  const [debiting, setDebiting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listAdminUsers();
      if (cancelledRef.current) {
        return;
      }
      setRows(list);
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

  const rowById = useMemo(() => {
    const m = new Map<string, IAdminUserRow>();
    for (const r of rows) {
      m.set(r.id, r);
    }
    return m;
  }, [rows]);

  const selectedRow = selectedId ? rowById.get(selectedId) ?? null : null;

  const openUser = useCallback(
    async (row: IAdminUserRow) => {
      setSelectedId(row.id);
      setDraftName(row.name);
      setDraftAllowNegative(row.allow_negative_balance);
      setTopupAmount(100);
      setDebitAmount(100);
      setProfile(null);
      setModalOpen(true);
      setProfileLoading(true);
      try {
        const p = await api.getAdminUser(row.id);
        if (cancelledRef.current) {
          return;
        }
        setProfile(p);
        setDraftName(p.name);
        setDraftAllowNegative(p.allow_negative_balance);
      } catch (e) {
        if (!cancelledRef.current) {
          message.error(e instanceof Error ? e.message : String(e));
        }
      } finally {
        if (!cancelledRef.current) {
          setProfileLoading(false);
        }
      }
    },
    [api, message],
  );

  const closeModal = useCallback(() => {
    setModalOpen(false);
    setSelectedId(null);
    setProfile(null);
  }, []);

  const onSaveProfile = useCallback(async () => {
    if (!selectedId) {
      return;
    }
    const name = draftName.trim();
    if (!name) {
      message.warning("Имя не может быть пустым");
      return;
    }
    setSavingProfile(true);
    try {
      const updated = await api.adminPatchUser(selectedId, {
        name,
        allow_negative_balance: draftAllowNegative,
      });
      if (cancelledRef.current) {
        return;
      }
      setProfile(updated);
      setDraftName(updated.name);
      setDraftAllowNegative(updated.allow_negative_balance);
      message.success("Сохранено");
      await load();
    } catch (e) {
      if (!cancelledRef.current) {
        message.error(e instanceof Error ? e.message : String(e));
      }
    } finally {
      if (!cancelledRef.current) {
        setSavingProfile(false);
      }
    }
  }, [api, draftAllowNegative, draftName, load, message, selectedId]);

  const runTopup = useCallback(async () => {
    if (!selectedId) {
      return;
    }
    setToppingUp(true);
    try {
      await api.adminTopUpUserBalance(selectedId, String(topupAmount));
      if (cancelledRef.current) {
        return;
      }
      message.success("Баланс пополнен");
      await load();
    } catch (e) {
      if (!cancelledRef.current) {
        message.error(e instanceof Error ? e.message : String(e));
      }
      throw e;
    } finally {
      if (!cancelledRef.current) {
        setToppingUp(false);
      }
    }
  }, [api, load, message, selectedId, topupAmount]);

  const onTopupClick = useCallback(() => {
    if (!selectedId) {
      return;
    }
    if (!topupAmount || topupAmount <= 0) {
      message.warning("Введите сумму больше нуля");
      return;
    }
    modal.confirm({
      title: "Подтверждение",
      content: `Вы уверены, что хотите пополнить баланс на ${topupAmount}?`,
      okText: "Да, пополнить",
      cancelText: "Отмена",
      onOk: () => runTopup(),
    });
  }, [modal, runTopup, selectedId, topupAmount, message]);

  const runDebit = useCallback(async () => {
    if (!selectedId) {
      return;
    }
    setDebiting(true);
    try {
      await api.adminSpendUserBalance(selectedId, String(debitAmount));
      if (cancelledRef.current) {
        return;
      }
      message.success("Сумма снята с баланса");
      await load();
    } catch (e) {
      if (!cancelledRef.current) {
        message.error(e instanceof Error ? e.message : String(e));
      }
      throw e;
    } finally {
      if (!cancelledRef.current) {
        setDebiting(false);
      }
    }
  }, [api, debitAmount, load, message, selectedId]);

  const onDebitClick = useCallback(() => {
    if (!selectedId) {
      return;
    }
    if (!debitAmount || debitAmount <= 0) {
      message.warning("Введите сумму больше нуля");
      return;
    }
    modal.confirm({
      title: "Подтверждение",
      content: `Вы уверены, что хотите снять с баланса ${debitAmount}?`,
      okText: "Да, снять",
      okButtonProps: { danger: true },
      cancelText: "Отмена",
      onOk: () => runDebit(),
    });
  }, [debitAmount, message, modal, runDebit, selectedId]);

  const balanceText = formatMoney2(selectedRow?.token_count ?? null);

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 0, fontWeight: 600, fontSize: 15 }}>
        Пользователи (админ). Нажмите на строку, чтобы открыть карточку.
      </Typography.Title>
      <AdminUsersTable rows={rows} loading={loading} onOpenUser={openUser} />

      <Modal
        title="Пользователь"
        open={modalOpen}
        onCancel={closeModal}
        footer={null}
        width={560}
        destroyOnClose
      >
        {selectedRow == null ? null : (
          <Spin spinning={profileLoading}>
            <Space direction="vertical" size="middle" style={{ width: "100%" }}>
              <Descriptions column={1} size="small" bordered>
                <Descriptions.Item label="ID">{selectedRow.id}</Descriptions.Item>
                <Descriptions.Item label="Email">{selectedRow.primary_email ?? "—"}</Descriptions.Item>
                <Descriptions.Item label="Роль">{selectedRow.role}</Descriptions.Item>
                <Descriptions.Item label="Баланс">{balanceText}</Descriptions.Item>
                <Descriptions.Item label="Идентификаторы">
                  {profile?.identities?.length
                    ? profile.identities.join(", ")
                    : profileLoading
                      ? "…"
                      : "—"}
                </Descriptions.Item>
              </Descriptions>

              <div>
                <Typography.Text type="secondary" style={{ display: "block", marginBottom: 6 }}>
                  Имя
                </Typography.Text>
                <Input value={draftName} onChange={(e) => setDraftName(e.target.value)} placeholder="Имя" />
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 12,
                  flexWrap: "wrap",
                }}
              >
                <Checkbox checked={draftAllowNegative} onChange={(e) => setDraftAllowNegative(e.target.checked)}>
                  Разрешить уход баланса в минус
                </Checkbox>
                <Button type="primary" loading={savingProfile} onClick={() => void onSaveProfile()}>
                  Сохранить имя и настройки
                </Button>
              </div>

              <div>
                <Typography.Text type="secondary" style={{ display: "block", marginBottom: 6 }}>
                  Пополнение и снятие баланса
                </Typography.Text>
                <Space wrap align="start" size="middle">
                  <Space direction="vertical" size={4}>
                    <Typography.Text type="secondary">Пополнение</Typography.Text>
                    <Space wrap>
                      <InputNumber
                        min={1}
                        value={topupAmount}
                        onChange={(v) => setTopupAmount(Number(v) || 1)}
                        style={{ width: 140 }}
                      />
                      <Button type="primary" loading={toppingUp} onClick={onTopupClick}>
                        Пополнить
                      </Button>
                    </Space>
                  </Space>
                  <Space direction="vertical" size={4}>
                    <Typography.Text type="secondary">Снятие</Typography.Text>
                    <Space wrap>
                      <InputNumber
                        min={1}
                        value={debitAmount}
                        onChange={(v) => setDebitAmount(Number(v) || 1)}
                        style={{ width: 140 }}
                      />
                      <Button danger loading={debiting} onClick={onDebitClick}>
                        Снять
                      </Button>
                    </Space>
                  </Space>
                </Space>
              </div>
            </Space>
          </Spin>
        )}
      </Modal>
    </Space>
  );
}
