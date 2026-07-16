import { useEffect, useState } from "react";
import { Table, Card, Select, Space, Button, Tag, InputNumber, Spin, Empty, message } from "antd";
import { SyncOutlined, GlobalOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { getProducts, triggerSync, type ProductItem, type ProductListParams } from "../api/products";

const riskColors: Record<string, string> = { danger: "red", warning: "orange", info: "blue" };

const PLATFORM_SITES: Record<string, { value: string; label: string }[]> = {
  amazon: [
    { value: "US", label: "United States" },
    { value: "JP", label: "Japan" },
    { value: "DE", label: "Germany" },
    { value: "GB", label: "United Kingdom" },
    { value: "FR", label: "France" },
    { value: "IT", label: "Italy" },
    { value: "ES", label: "Spain" },
    { value: "CA", label: "Canada" },
    { value: "AU", label: "Australia" },
  ],
  tiktok: [
    { value: "US", label: "United States" },
    { value: "GB", label: "United Kingdom" },
    { value: "JP", label: "Japan" },
    { value: "ID", label: "Indonesia" },
    { value: "TH", label: "Thailand" },
    { value: "VN", label: "Vietnam" },
    { value: "PH", label: "Philippines" },
    { value: "MY", label: "Malaysia" },
  ],
};

export default function Products() {
  const { t } = useTranslation();
  const [data, setData] = useState<ProductItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [page, setPage] = useState(1);
  const [platform, setPlatform] = useState<string>("amazon");
  const [site, setSite] = useState<string>("US");
  const [filters, setFilters] = useState<ProductListParams>({ sort_by: "score", sort_order: "desc" });

  const loadData = async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await getProducts({ ...filters, platform, page });
      setData(res.items);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [page, filters, platform]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await triggerSync({ platform, site });
      message.success(t("products.syncSuccess"));
    } catch {
      message.error(t("products.syncFailed"));
    } finally {
      setSyncing(false);
    }
  };

  if (loading && data.length === 0) return <Spin size="large" />;
  if (error && data.length === 0) {
    return <Empty description={t("products.loadFailed")}><a onClick={loadData}>{t("common.retry")}</a></Empty>;
  }

  const columns = [
    { title: t("products.title"), dataIndex: "title", key: "title", ellipsis: true, width: 280 },
    {
      title: t("products.platform"), dataIndex: "platform", key: "platform", width: 90,
      render: (v: string) => <Tag color={v === "tiktok" ? "magenta" : "orange"}>{(v || "amazon").toUpperCase()}</Tag>,
    },
    { title: t("products.category"), dataIndex: "category", key: "category", width: 120 },
    { title: t("products.monthlySales"), dataIndex: "monthly_sales", key: "monthly_sales", width: 110, sorter: true },
    {
      title: t("products.price"), dataIndex: "price", key: "price", width: 80,
      render: (v: number | null) => v ? `$${(v / 100).toFixed(2)}` : "-",
    },
    {
      title: t("products.score"), dataIndex: "comprehensive_score", key: "score", width: 80,
      sorter: true, defaultSortOrder: "descend" as const,
      render: (v: number | null) => v ? <span style={{ color: "#52c41a", fontWeight: 600 }}>{v.toFixed(1)}</span> : "-",
    },
    { title: t("products.reviews"), dataIndex: "review_count", key: "review_count", width: 80 },
    {
      title: t("products.risk"), dataIndex: "risk_tags", key: "risk_tags", width: 120,
      render: (tags: string[] | null) => tags?.length
        ? tags.map((tag) => <Tag key={tag} color={riskColors.warning}>{tag}</Tag>)
        : <span style={{ color: "#8c8c8c" }}>-</span>,
    },
    { title: t("products.match"), dataIndex: "match_status", key: "match_status", width: 90 },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            value={platform}
            style={{ width: 140 }}
            onChange={(v) => { setPlatform(v); setSite("US"); setPage(1); }}
            options={[
              { value: "amazon", label: "Amazon" },
              { value: "tiktok", label: "TikTok Shop" },
            ]}
          />
          <Select
            value={site}
            style={{ width: 160 }}
            onChange={(v) => { setSite(v); setPage(1); }}
            options={PLATFORM_SITES[platform] || []}
            suffixIcon={<GlobalOutlined />}
          />
          <Select
            placeholder={t("products.category")} allowClear style={{ width: 170 }}
            options={[
              { value: "3D printer filament", label: t("products.categories.filament") },
              { value: "sublimation ink", label: t("products.categories.ink") },
              { value: "photo paper", label: t("products.categories.paper") },
            ]}
            onChange={(v) => { setPage(1); setFilters({ ...filters, category: v }); }}
          />
          <Select
            placeholder={t("products.matchStatus")} allowClear style={{ width: 150 }}
            options={[
              { value: "pending", label: t("products.status.pending") },
              { value: "confirmed", label: t("products.status.confirmed") },
              { value: "rejected", label: t("products.status.rejected") },
            ]}
            onChange={(v) => { setPage(1); setFilters({ ...filters, match_status: v }); }}
          />
          <span>{t("products.minScore")}:</span>
          <InputNumber
            placeholder="0" min={0} max={100} style={{ width: 80 }}
            onChange={(v) => { setPage(1); setFilters({ ...filters, min_score: v ?? undefined }); }}
          />
          <Button type="primary" icon={<SyncOutlined spin={syncing} />} loading={syncing} onClick={handleSync}>
            {t("common.sync")} {platform === "tiktok" ? "TikTok" : "Amazon"} {site}
          </Button>
        </Space>
      </Card>

      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="middle"
        pagination={{
          current: page,
          pageSize: 20,
          onChange: setPage,
          showTotal: (total) => `${t("common.total")} ${total} ${t("common.items")}`,
        }}
        locale={{ emptyText: <Empty description={t("products.empty")} /> }}
      />
    </div>
  );
}
