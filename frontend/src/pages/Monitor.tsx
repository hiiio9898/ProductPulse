import { useEffect, useState } from "react";
import { Card, Table, Tag, Button, Space, Segmented, message, Empty, Spin, Tooltip } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { getPriceAlerts, getMonitoredProducts, refreshAllPrices, type PriceAlert, type MonitoredProduct } from "../api/price";
import Sparkline from "../components/Sparkline";

export default function Monitor() {
  const { t } = useTranslation();
  const [view, setView] = useState<string>("all");
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [monitored, setMonitored] = useState<MonitoredProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      if (view === "alerts") {
        const res = await getPriceAlerts();
        setAlerts(res.items);
      } else {
        const res = await getMonitoredProducts();
        setMonitored(res.items);
      }
    } catch {
      message.error(t("products.loadFailed"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [view]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshAllPrices();
      message.success(t("monitor.refresh"));
      setTimeout(loadData, 3000);
    } catch {
      message.error(t("products.loadFailed"));
    } finally {
      setRefreshing(false);
    }
  };

  const alertMeta: Record<string, { color: string }> = {
    cost_alert: { color: "red" },
    price_drop: { color: "green" },
  };

  const alertColumns = [
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
      render: (v: string) => <Tag color={alertMeta[v]?.color || "default"}>{t(`monitor.alerts.${v}`, { defaultValue: v })}</Tag>,
    },
    { title: t("footer.lastUpdated"), dataIndex: "snapshot_date", key: "date", width: 110 },
  ];

  const allColumns = [
    { title: t("monitor.product"), dataIndex: "title", key: "title", ellipsis: true, width: 280 },
    {
      title: t("products.platform"), dataIndex: "platform", key: "platform", width: 90,
      render: (v: string) => <Tag color={v === "tiktok" ? "magenta" : "orange"}>{(v || "amazon").toUpperCase()}</Tag>,
    },
    {
      title: t("monitor.price1688"), dataIndex: "price_1688", key: "price_1688", width: 100,
      render: (v: number | null) => v ? `\u00a5${v}` : "-",
    },
    {
      title: t("monitor.change"), dataIndex: "price_change_percent", key: "change", width: 100,
      render: (v: number | null) => v === null || v === undefined
        ? "-"
        : <span style={{ color: v > 0 ? "#ff4d4f" : "#52c41a", fontWeight: 600 }}>{v > 0 ? "\u2191" : "\u2193"} {Math.abs(v).toFixed(1)}%</span>,
    },
    {
      title: t("monitor.trend"), key: "trend", width: 150,
      render: (_: unknown, record: MonitoredProduct) => (
        <Tooltip title={record.trend.map((p) => `${p.date}: \u00a5${p.price_1688 ?? "-"}`).join("\n")}>
          <Sparkline data={record.trend.map((p) => p.price_1688)} />
        </Tooltip>
      ),
    },
    {
      title: t("monitor.alert"), dataIndex: "alert", key: "alert", width: 110,
      render: (v: string | null) => v ? <Tag color={alertMeta[v]?.color || "default"}>{t(`monitor.alerts.${v}`, { defaultValue: v })}</Tag> : <span style={{ color: "#bfbfbf" }}>-</span>,
    },
    { title: t("footer.lastUpdated"), dataIndex: "snapshot_date", key: "date", width: 110 },
  ];

  const dataSource = view === "alerts" ? alerts : monitored;
  const total = dataSource.length;

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Segmented
            value={view}
            onChange={(v) => setView(v as string)}
            options={[
              { label: t("monitor.all", { defaultValue: "全部在监" }), value: "all" },
              { label: t("monitor.alertsOnly", { defaultValue: "仅预警" }), value: "alerts" },
            ]}
          />
          <Button type="primary" icon={<ReloadOutlined spin={refreshing} />} loading={refreshing} onClick={handleRefresh}>
            {t("monitor.refresh")}
          </Button>
        </Space>
      </Card>

      <Card title={`${t("monitor.title")} (${total})`}>
        {loading ? <Spin /> : total === 0 ? (
          <Empty description={t("monitor.empty")} />
        ) : (
          <Table dataSource={dataSource as any[]} columns={view === "alerts" ? alertColumns : allColumns} rowKey="product_id" size="middle" pagination={{ pageSize: 20 }} />
        )}
      </Card>
    </div>
  );
}
