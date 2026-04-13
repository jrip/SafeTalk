import { InboxOutlined, SendOutlined } from "@ant-design/icons";
import type { UploadProps } from "antd";
import { Alert, App, Button, Card, Descriptions, Form, Input, Select, Space, Switch, Table, Typography, Upload } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { IMlCatalogItem, IPredictionTaskDetail } from "../client/contracts";
import { useSafeTalkApi } from "../client/ClientContext";
import { formatMoney2 } from "../formatCredits";

const { TextArea } = Input;
const MAX_LINE_LEN = 8000;

export interface IValidatedLine {
  key: string;
  lineNo: number;
  text: string;
  ok: boolean;
  reason?: string;
}

export interface IBatchRow extends IValidatedLine {
  taskId?: string;
  status?: string;
  error?: string;
  charged?: string;
  summary?: string;
}

function validateLines(raw: string): IValidatedLine[] {
  const parts = raw.split(/\r?\n/);
  const out: IValidatedLine[] = [];
  let lineNo = 0;
  for (const rawLine of parts) {
    lineNo += 1;
    const text = rawLine.replace(/\r$/, "");
    const trimmed = text.trim();
    if (!trimmed) {
      out.push({
        key: String(lineNo),
        lineNo,
        text: rawLine || "(пусто)",
        ok: false,
        reason: "Пустая строка — не отправляется",
      });
      continue;
    }
    if (text.length > MAX_LINE_LEN) {
      out.push({
        key: String(lineNo),
        lineNo,
        text: `${text.slice(0, 80)}…`,
        ok: false,
        reason: `Строка длиннее ${MAX_LINE_LEN} символов`,
      });
      continue;
    }
    out.push({ key: String(lineNo), lineNo, text, ok: true });
  }
  return out;
}

export default function PredictPage() {
  const { message } = App.useApp();
  const api = useSafeTalkApi();
  const [models, setModels] = useState<readonly IMlCatalogItem[]>([]);
  const [modelId, setModelId] = useState<string | undefined>();
  const [text, setText] = useState("");
  const [batchMode, setBatchMode] = useState(false);
  const [parsed, setParsed] = useState<IValidatedLine[]>([]);
  const [batchRows, setBatchRows] = useState<IBatchRow[]>([]);
  const [lastResult, setLastResult] = useState<IPredictionTaskDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [allowNegative, setAllowNegative] = useState(false);

  const selectedModel = useMemo(() => models.find((m) => m.id === modelId), [models, modelId]);

  const loadModels = useCallback(async () => {
    try {
      const list = await api.listMlModels();
      setModels(list);
      const def = list.find((m) => m.is_default) ?? list[0];
      if (def) {
        setModelId(def.id);
      }
    } catch (e) {
      message.error(e instanceof Error ? e.message : String(e));
    }
  }, [api, message]);

  useEffect(() => {
    void loadModels();
  }, [loadModels]);

  useEffect(() => {
    let c = false;
    (async () => {
      try {
        const me = await api.getCurrentUser();
        if (!c) {
          setAllowNegative(me.allow_negative_balance);
        }
      } catch {
        if (!c) {
          setAllowNegative(false);
        }
      }
    })();
    return () => {
      c = true;
    };
  }, [api]);

  function onParse() {
    const rows = validateLines(text);
    setParsed(rows);
    setBatchRows(rows.map((r) => ({ ...r })));
    const rejected = rows.filter((r) => !r.ok).length;
    const accepted = rows.filter((r) => r.ok).length;
    message.info(`Разбор: принято строк — ${accepted}, отклонено — ${rejected}`);
  }

  async function ensureBalanceForCharge(totalCharge: number): Promise<boolean> {
    if (allowNegative) {
      return true;
    }
    const b = await api.getMyBalance();
    const have = Number(b.token_count);
    if (have < totalCharge) {
      message.error(
        `Недостаточно кредитов: нужно примерно ${formatMoney2(String(totalCharge))}, на балансе ${formatMoney2(b.token_count)}. Пополните баланс.`,
      );
      return false;
    }
    return true;
  }

  async function runSingle() {
    if (!modelId) {
      message.warning("Выберите модель");
      return;
    }
    const t = text.trim();
    if (!t) {
      message.warning("Введите текст");
      return;
    }
    const price = Number(selectedModel?.price_per_character ?? 0);
    const charge = t.length * price;
    if (!(await ensureBalanceForCharge(charge))) {
      return;
    }
    setBusy(true);
    setLastResult(null);
    const hide = message.loading("Выполняется запрос…", 0);
    try {
      const taskId = await api.createPredictionTask({ modelId, text: t });
      const detail = await api.pollPredictionTask(taskId);
      setLastResult(detail);
      if (detail.status === "failed") {
        message.error("Задача завершилась с ошибкой");
      } else {
        message.success(`Готово. Списано кредитов: ${formatMoney2(detail.charged_tokens)}`);
      }
    } catch (e) {
      message.error(e instanceof Error ? e.message : String(e));
    } finally {
      hide();
      setBusy(false);
    }
  }

  async function runBatch() {
    if (!modelId) {
      message.warning("Выберите модель");
      return;
    }
    if (!parsed.length) {
      message.warning("Сначала нажмите «Разобрать»");
      return;
    }
    const okLines = parsed.filter((r) => r.ok);
    if (okLines.length === 0) {
      message.warning("Нет ни одной допустимой строки после валидации.");
      return;
    }
    const price = Number(selectedModel?.price_per_character ?? 0);
    const totalChars = okLines.reduce((s, r) => s + r.text.length, 0);
    const totalCharge = totalChars * price;
    if (!(await ensureBalanceForCharge(totalCharge))) {
      return;
    }

    setBusy(true);
    setLastResult(null);
    const next: IBatchRow[] = parsed.map((r) => ({ ...r }));

    try {
      for (let i = 0; i < next.length; i += 1) {
        const row = next[i];
        if (!row.ok) {
          continue;
        }
        try {
          const taskId = await api.createPredictionTask({ modelId, text: row.text });
          row.taskId = taskId;
          row.status = "pending";
          setBatchRows([...next]);
          const detail = await api.pollPredictionTask(taskId);
          row.status = detail.status;
          row.charged = detail.charged_tokens;
          row.summary = detail.result_summary ?? undefined;
          row.error = detail.status === "failed" ? "Ошибка выполнения ML" : undefined;
          setBatchRows([...next]);
        } catch (e) {
          row.status = "error";
          row.error = e instanceof Error ? e.message : String(e);
          setBatchRows([...next]);
        }
      }
      message.success("Пакетная отправка завершена");
    } finally {
      setBusy(false);
    }
  }

  const parseColumns: ColumnsType<IValidatedLine> = [
    { title: "№", dataIndex: "lineNo", width: 56 },
    { title: "Фрагмент", dataIndex: "text", ellipsis: true },
    {
      title: "Валидация",
      key: "v",
      width: 130,
      render: (_, r) =>
        r.ok ? (
          <Typography.Text type="success">к обработке</Typography.Text>
        ) : (
          <Typography.Text type="danger">отклонено</Typography.Text>
        ),
    },
    { title: "Комментарий", dataIndex: "reason", ellipsis: true },
  ];

  const batchColumns: ColumnsType<IBatchRow> = [
    { title: "№", dataIndex: "lineNo", width: 56 },
    { title: "Фрагмент", dataIndex: "text", ellipsis: true },
    {
      title: "Валидация",
      key: "v",
      width: 110,
      render: (_, r) => (r.ok ? "OK" : "—"),
    },
    { title: "task_id", dataIndex: "taskId", width: 120, ellipsis: true },
    { title: "Статус ML", dataIndex: "status", width: 100 },
    {
      title: "Списание",
      dataIndex: "charged",
      width: 120,
      align: "right",
      render: (v: string | undefined) => (v == null ? "—" : formatMoney2(v)),
    },
    { title: "Ошибка", dataIndex: "error", ellipsis: true },
  ];

  const uploadDraggerProps = {
    accept: ".txt,text/plain",
    maxCount: 1,
    showUploadList: true,
    beforeUpload: (file: File) => {
      const reader = new FileReader();
      reader.onload = () => {
        const s = typeof reader.result === "string" ? reader.result : "";
        setText(s);
        message.success(`Файл «${file.name}» загружен в поле`);
      };
      reader.readAsText(file, "UTF-8");
      return false;
    },
  } satisfies UploadProps;

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 16, fontWeight: 600, fontSize: 15 }}>
        Проверка текста на токсичность: модель, ввод или файл, затем отправка и результат.
      </Typography.Title>

      <Card title="Параметры">
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Form.Item label="Модель" style={{ marginBottom: 0 }}>
            <Select
              style={{ maxWidth: 480, width: "100%" }}
              options={models.map((m) => ({
                value: m.id,
                label: `${m.name} (${formatMoney2(m.price_per_character)} за символ)`,
              }))}
              value={modelId}
              onChange={setModelId}
              loading={!models.length}
            />
          </Form.Item>
          {selectedModel ? (
            <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
              {selectedModel.description}
            </Typography.Paragraph>
          ) : null}
        </Space>
      </Card>

      <Card title="Данные">
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Upload.Dragger {...uploadDraggerProps}>
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">Загрузить .txt в поле ниже</p>
            <p className="ant-upload-hint">Текст из файла появится в поле ниже</p>
          </Upload.Dragger>
          <TextArea
            rows={batchMode ? 12 : 8}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Текст для одной задачи или несколько строк в режиме ниже"
          />
          <Space align="center" wrap>
            <Typography.Text>Несколько строк</Typography.Text>
            <Switch checked={batchMode} onChange={setBatchMode} />
          </Space>
        </Space>
      </Card>

      {batchMode ? (
        <Card title="Разбор и пакетная отправка">
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Space wrap>
              <Button onClick={onParse}>Разобрать</Button>
              <Button type="primary" icon={<SendOutlined />} onClick={() => void runBatch()} disabled={busy} loading={busy}>
                Отправить все допустимые строки
              </Button>
            </Space>
            {parsed.length ? (
              <Alert type="info" showIcon message="Строки «отклонено» в обработку не отправляются." />
            ) : null}
            <Table size="small" pagination={false} columns={parseColumns} dataSource={parsed} rowKey="key" />
            {batchRows.some((r) => r.taskId) ? (
              <Table size="small" columns={batchColumns} dataSource={batchRows} rowKey="key" pagination={false} />
            ) : null}
          </Space>
        </Card>
      ) : (
        <Card title="Отправка одной задачи">
          <Button type="primary" icon={<SendOutlined />} onClick={() => void runSingle()} disabled={busy} loading={busy}>
            Отправить запрос
          </Button>
        </Card>
      )}

      {lastResult && !batchMode ? (
        <Card title="Результат последнего запроса">
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="Статус">{lastResult.status}</Descriptions.Item>
            <Descriptions.Item label="Списано кредитов">{formatMoney2(lastResult.charged_tokens)}</Descriptions.Item>
            <Descriptions.Item label="Токсичность (is_toxic)">
              {lastResult.is_toxic === null ? "—" : lastResult.is_toxic ? "да" : "нет"}
            </Descriptions.Item>
            <Descriptions.Item label="Вероятность">{lastResult.toxicity_probability ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="Сводка">
              <Typography.Paragraph style={{ whiteSpace: "pre-wrap", marginBottom: 0 }}>
                {lastResult.result_summary ?? "—"}
              </Typography.Paragraph>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      ) : null}
    </Space>
  );
}
