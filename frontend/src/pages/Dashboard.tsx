import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Table, Spin, Empty, message } from "antd";
import { useTranslation } from "react-i18next";
import { getOverview, type OverviewData, type TrendItem, getTrends } from "../api/dashboard";

export default function Dashboard() {
  const { t } = useTranslation();
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [trends, setTrends] = useState<TrendItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(false);
    try {
      const [ov, tr] = await Promise.all([getOverview(), getTrends()]);
      setOverview(ov);
      setTrends(tr);
    } catch {
      setError(true);
      message.error(t("products.loadFailed"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  if (loading) return <Spin size="large" />;
  if (error) {
    return (
      <Empty description={t("products.loadFailed")}>
        <a onClick={loadData}>{t("common.retry")}</a>
      </Empty>
    );
  }

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card><Statistic title={t("dashboard.recommendations")} value={overview?.recommendations_today ?? 0} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title={t("dashboard.alerts")} value={overview?.alerts_count ?? 0} valueStyle={{ color: "#ff4d4f" }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title={t("dashboard.pending")} value={overview?.pending_sku_count ?? 0} valueStyle={{ color: "#faad14" }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title={t("dashboard.topScore")} value={overview?.top_score ?? 0} precision={1} valueStyle={{ color: "#52c41a" }} /></Card>
        </Col>
      </Row>

      <Card title={t("dashboard.trends")}>
        {trends.length === 0 ? (
          <Empty description={t("dashboard.noProduct")} />
        ) : (
          <Table
            dataSource={trends}
            rowKey="date"
            pagination={false}
            size="small"
            columns={[
              { title: t("footer.lastUpdated"), dataIndex: "date", key: "date" },
              { title: t("products.title"), dataIndex: "product_count", key: "product_count" },
              { title: t("products.monthlySales"), dataIndex: "avg_sales", key: "avg_sales" },
            ]}
          />
        )}
      </Card>

      {overview?.top_product_title && (
        <Card title={`TOP1`} style={{ marginTop: 16 }}>
          {overview.top_product_title}
        </Card>
      )}
    </div>
  );
}
