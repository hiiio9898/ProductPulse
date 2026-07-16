import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Table, Spin, Empty, message } from "antd";
import { getOverview, type OverviewData, type TrendItem, getTrends } from "../api/dashboard";

export default function Dashboard() {
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
      message.error("数据加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  if (loading) return <Spin size="large" />;
  if (error) {
    return (
      <Empty description="数据加载失败">
        <a onClick={loadData}>点击重试</a>
      </Empty>
    );
  }

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card><Statistic title="今日推荐数" value={overview?.recommendations_today ?? 0} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="预警数量" value={overview?.alerts_count ?? 0} valueStyle={{ color: "#ff4d4f" }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="待匹配 SKU" value={overview?.pending_sku_count ?? 0} valueStyle={{ color: "#faad14" }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="综合评分 TOP1" value={overview?.top_score ?? 0} precision={1} valueStyle={{ color: "#52c41a" }} /></Card>
        </Col>
      </Row>

      <Card title="近 7 天品类趋势">
        {trends.length === 0 ? (
          <Empty description="暂无趋势数据" />
        ) : (
          <Table
            dataSource={trends}
            rowKey="date"
            pagination={false}
            size="small"
            columns={[
              { title: "日期", dataIndex: "date", key: "date" },
              { title: "产品数", dataIndex: "product_count", key: "product_count" },
              { title: "平均月销量", dataIndex: "avg_sales", key: "avg_sales" },
            ]}
          />
        )}
      </Card>

      {overview?.top_product_title && (
        <Card title="TOP1 产品" style={{ marginTop: 16 }}>
          {overview.top_product_title}
        </Card>
      )}
    </div>
  );
}