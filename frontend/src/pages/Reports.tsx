import { useEffect, useState } from "react";
import { Card, Button, DatePicker, Spin, Empty, Tag, Space, message, Typography } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import dayjs from "dayjs";
import { getReportByDate, triggerGenerate, type DailyReportData } from "../api/reports";

const { Text } = Typography;

const sections = [
  { key: "recommendations", title: "今日推荐", color: "#52c41a" },
  { key: "trend_analysis", title: "趋势解读", color: "#1890ff" },
  { key: "risk_alerts", title: "风险提示", color: "#ff4d4f" },
  { key: "action_suggestions", title: "行动建议", color: "#faad14" },
] as const;

export default function Reports() {
  const [report, setReport] = useState<DailyReportData | null>(null);
  const [date, setDate] = useState(dayjs());
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

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
      message.success("日报生成任务已提交，请稍后刷新查看");
      setTimeout(() => loadReport(date), 5000);
    } catch {
      message.error("生成失败");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <Spin size="large" />;

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Text>选择日期：</Text>
          <DatePicker value={date} onChange={(d) => d && setDate(d)} allowClear={false} />
          <Button type="primary" icon={<ReloadOutlined spin={generating} />} loading={generating} onClick={handleRegenerate}>
            重新生成
          </Button>
        </Space>
      </Card>

      {report ? (
        <>
          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Tag color="blue">{report.model_used}</Tag>
              <Text type="secondary">生成耗时 {report.generation_time_ms}ms</Text>
              <Text type="secondary">{report.report_date}</Text>
            </Space>
          </Card>
          {sections.map((sec) => (
            <Card key={sec.key} title={<span style={{ color: sec.color }}>{sec.title}</span>} style={{ marginBottom: 16 }}>
              <ReactMarkdown>{report[sec.key] || "暂无内容"}</ReactMarkdown>
            </Card>
          ))}
        </>
      ) : (
        <Empty description="该日期暂无 AI 日报，点击「重新生成」创建">
          <Button type="primary" onClick={handleRegenerate} loading={generating}>生成日报</Button>
        </Empty>
      )}
    </div>
  );
}