import { useEffect, useState } from "react";
import { Card, Button, DatePicker, Spin, Empty, Tag, Space, message, Typography } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import { getReportByDate, triggerGenerate, type DailyReportData } from "../api/reports";

const { Text } = Typography;

export default function Reports() {
  const { t } = useTranslation();
  const [report, setReport] = useState<DailyReportData | null>(null);
  const [date, setDate] = useState(dayjs());
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  const sections = [
    { key: "recommendations", title: t("reports.recommendations"), color: "#52c41a" },
    { key: "trend_analysis", title: t("reports.trendAnalysis"), color: "#1890ff" },
    { key: "risk_alerts", title: t("reports.riskAlerts"), color: "#ff4d4f" },
    { key: "action_suggestions", title: t("reports.actionSuggestions"), color: "#faad14" },
  ] as const;

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

  useEffect(() => { loadReport(date); }, [date]);

  const handleRegenerate = async () => {
    setGenerating(true);
    try {
      await triggerGenerate(date.format("YYYY-MM-DD"));
      message.success(t("reports.generating"));
      setTimeout(() => loadReport(date), 5000);
    } catch {
      message.error(t("reports.empty"));
    } finally {
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
