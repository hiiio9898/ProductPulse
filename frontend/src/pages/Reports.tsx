import { useEffect, useState, useRef } from "react";
import { Card, Button, DatePicker, Spin, Empty, Tag, Space, message, Typography, Alert } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import { getReportByDate, triggerGenerate, getGenerateProgress, type DailyReportData, type GenerateProgress } from "../api/reports";

const { Text } = Typography;

export default function Reports() {
  const { t } = useTranslation();
  const [report, setReport] = useState<DailyReportData | null>(null);
  const [date, setDate] = useState(dayjs());
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState<GenerateProgress | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const sections = report ? [
    { key: "recommendations", title: t("reports.recommendations"), color: "#52c41a" },
    { key: "trend_analysis", title: t("reports.trendAnalysis"), color: "#1890ff" },
    { key: "risk_alerts", title: t("reports.riskAlerts"), color: "#ff4d4f" },
    { key: "action_suggestions", title: t("reports.actionSuggestions"), color: "#faad14" },
  ] as const : [];

  const loadReport = async (d: dayjs.Dayjs) => {
    setLoading(true);
    try {
      const data = await getReportByDate(d.format("YYYY-MM-DD"));
      setReport(data);
    } catch {
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const startPolling = (taskId: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const prog = await getGenerateProgress(taskId);
        setProgress(prog);
        if (prog.status === "success" || prog.status === "failed") {
          stopPolling();
          setGenerating(false);
          if (prog.status === "success") {
            message.success(t("reports.title") + " OK");
            loadReport(date);
          } else {
            message.error(prog.message || "Failed");
          }
        }
      } catch { /* ignore */ }
    }, 2000);
  };

  useEffect(() => { loadReport(date); }, [date]);
  useEffect(() => () => stopPolling(), []);

  const handleRegenerate = async () => {
    setGenerating(true);
    setProgress({ status: "pending", message: "Submitting..." });
    try {
      const result = await triggerGenerate(date.format("YYYY-MM-DD"), true);
      startPolling(result.task_id);
    } catch {
      message.error(t("reports.empty"));
      setGenerating(false);
    }
  };

  if (loading) return <Spin size="large" />;

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <DatePicker value={date} onChange={(d) => d && setDate(d)} allowClear={false} />
          <Button type="primary" icon={<ReloadOutlined spin={generating} />} loading={generating} onClick={handleRegenerate}>
            {report ? t("reports.regenerate") : t("reports.generate")}
          </Button>
        </Space>
      </Card>

      {generating && progress && (
        <Card style={{ marginBottom: 16 }}>
          {progress.status === "retrying" ? (
            <Alert
              type="warning"
              showIcon
              message={`${t("reports.generating")} - ${progress.model || ""}`}
              description={`Rate limited, retrying (${progress.attempt}/${progress.max_retries})... Please wait.`}
            />
          ) : progress.status === "pending" ? (
            <Alert type="info" showIcon message={progress.message || t("reports.generating")} />
          ) : progress.status === "failed" ? (
            <Alert type="error" showIcon message={progress.message || "Failed"} />
          ) : null}
        </Card>
      )}

      {report ? (
        <>
          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Tag color="blue">{report.model_used}</Tag>
              <Text type="secondary">{t("reports.modelUsed")}: {report.generation_time_ms}ms</Text>
              <Text type="secondary">{report.report_date}</Text>
            </Space>
          </Card>
          {sections.map((sec) => (
            <Card key={sec.key} title={<span style={{ color: sec.color }}>{sec.title}</span>} style={{ marginBottom: 16 }}>
              <ReactMarkdown>{report[sec.key] || "-"}</ReactMarkdown>
            </Card>
          ))}
        </>
      ) : (
        <Empty description={t("reports.empty")}>
          <Button type="primary" onClick={handleRegenerate} loading={generating}>{t("reports.generate")}</Button>
        </Empty>
      )}
    </div>
  );
}
