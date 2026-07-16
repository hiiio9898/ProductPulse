import { useEffect, useState } from "react";
import { Card, Table, Tag, Button, Space, message, Empty, Spin } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { getPriceAlerts, refreshAllPrices, type PriceAlert } from "../api/price";

export default function Monitor() {
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await getPriceAlerts();
      setAlerts(res.items);
    } catch {
      message.error("预警加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshAllPrices();
      message.success("价格刷新任务已提交");
      setTimeout(loadData, 3000);
    } catch {
      message.error("刷新失败");
    } finally {
      setRefreshing(false);
    }
  };

  const alertMeta: Record<string, { color: string; text: string }> = {
    cost_alert: { color: "red", text: "成本上涨预警" },
    price_drop: { color: "green", text: "降价利好" },
  };

  const columns = [
    { title: "产品", dataIndex: "title", key: "title", ellipsis: true },
    {
      title: "1688 价格", dataIndex: "price_1688", key: "price_1688", width: 100,
      render: (v: number | null) => v ? `¥${v}` : "-",
    },
    {
      title: "变动幅度", dataIndex: "price_change_percent", key: "change", width: 100,
      render: (v: number) => (
        <span style={{ color: v > 0 ? "#ff4d4f" : "#52c41a", fontWeight: 600 }}>
          {v > 0 ? "↑" : "↓"} {Math.abs(v).toFixed(1)}%
        </span>
      ),
    },
    {
      title: "预警类型", dataIndex: "alert", key: "alert", width: 120,
      render: (v: string) => {
        const meta = alertMeta[v] || { color: "default", text: v };
        return <Tag color={meta.color}>{meta.text}</Tag>;
      },
    },
    { title: "快照日期", dataIndex: "snapshot_date", key: "date", width: 110 },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Button type="primary" icon={<ReloadOutlined spin={refreshing} />} loading={refreshing} onClick={handleRefresh}>
            刷新全部价格
          </Button>
          <span style={{ color: "#8c8c8c" }}>刷新已关联 1688 的产品拿货价，变动 ≥5% 自动预警</span>
        </Space>
      </Card>

      <Card title={`价格预警（${alerts.length}）`}>
        {loading ? <Spin /> : alerts.length === 0 ? (
          <Empty description="暂无价格预警，所有关联产品价格稳定" />
        ) : (
          <Table dataSource={alerts} columns={columns} rowKey="product_id" size="middle" pagination={false} />
        )}
      </Card>
    </div>
  );
}