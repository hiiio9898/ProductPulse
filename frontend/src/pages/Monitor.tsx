import { useEffect, useState } from "react";
import { Card, Table, Tag, Button, Space, message, Empty, Spin } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { getPriceAlerts, refreshAllPrices, type PriceAlert } from "../api/price";

export default function Monitor() {
  const { t } = useTranslation();
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await getPriceAlerts();
      setAlerts(res.items);
    } catch {
      message.error(t("monitor.empty"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshAllPrices();
      message.success(t("monitor.refresh"));
      setTimeout(loadData, 3000);
    } catch {
      message.error(t("monitor.refresh"));
    } finally {
      setRefreshing(false);
    }
  };

  const columns = [
    { title: t("monitor.product"), dataIndex: "title", key: "title", ellipsis: true },
    {
      title: t("monitor.price1688"), dataIndex: "price_1688", key: "price_1688", width: 100,
      render: (v: number | null) => v ? `\u00a5${v}` : "-",
    },
    {
      title: t("monitor.change"), dataIndex: "price_change_percent", key: "change", width: 100,
      render: (v: number) => (
        <span style={{ color: v > 0 ? "#ff4d4f" : "#52c41a", fontWeight: 600 }}>
          {v > 0 ? "\u2191" : "\u2193"} {Math.abs(v).toFixed(1)}%
        </span>
      ),
    },
    {
      title: t("monitor.alert"), dataIndex: "alert", key: "alert", width: 120,
      render: (v: string) => {
        const meta: Record<string, { color: string }> = {
          cost_alert: { color: "red" },
          price_drop: { color: "green" },
        };
        return <Tag color={meta[v]?.color || "default"}>{t(`monitor.alerts.${v}`, { defaultValue: v })}</Tag>;
      },
    },
    { title: t("footer.lastUpdated"), dataIndex: "snapshot_date", key: "date", width: 110 },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Button type="primary" icon={<ReloadOutlined spin={refreshing} />} loading={refreshing} onClick={handleRefresh}>
            {t("monitor.refresh")}
          </Button>
        </Space>
      </Card>

      <Card title={`${t("monitor.title")} (${alerts.length})`}>
        {loading ? <Spin /> : alerts.length === 0 ? (
          <Empty description={t("monitor.empty")} />
        ) : (
          <Table dataSource={alerts} columns={columns} rowKey="product_id" size="middle" pagination={false} />
        )}
      </Card>
    </div>
  );
}
