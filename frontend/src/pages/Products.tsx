import { useEffect, useState } from "react";
import { Table, Card, Select, Space, Button, Tag, InputNumber, Input, Spin, Empty, message, Modal, Descriptions, Statistic, Row, Col, Progress, Drawer } from "antd";
import { SyncOutlined, GlobalOutlined, SearchOutlined, ReloadOutlined, EyeOutlined, DownloadOutlined } from "@ant-design/icons";
import { useRef } from "react";
import Sparkline from "../components/Sparkline";
import { formatPrice } from "../utils/price";
import { useTranslation } from "react-i18next";
import { getProducts, triggerSync, getSyncStatus, getProductDetail, exportProductsCsv, type ProductItem, type ProductListParams, type SyncStatus, type ProductDetail } from "../api/products";
import { compareProduct, type CompareResult } from "../api/price";

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
  const [detail, setDetail] = useState<ProductDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [syncProgress, setSyncProgress] = useState<SyncStatus | null>(null);
  const [keyword, setKeyword] = useState("");
  const syncPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [page, setPage] = useState(1);
  const [platform, setPlatform] = useState<string>("tiktok");
  const [site, setSite] = useState<string>("US");
  const [filters, setFilters] = useState<ProductListParams>({ sort_by: "score", sort_order: "desc" });

  const loadData = async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await getProducts({ ...filters, platform, site, keyword: keyword || undefined, page });
      setData(res.items);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [page, filters, platform, site, keyword]);
  useEffect(() => () => stopSyncPolling(), []);

  const [comparingId, setComparingId] = useState<number | null>(null);
  const [compareData, setCompareData] = useState<CompareResult | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareProductId, setCompareProductId] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const handleCompare = async (id: number) => {
    setComparingId(id);
    setCompareProductId(id);
    try {
      const data = await compareProduct(id);
      setCompareData(data);
      setCompareOpen(true);
    } catch {
      message.error(t("compare.failed"));
    } finally {
      setComparingId(null);
    }
  };

  const handleRefreshCompare = async () => {
    if (!compareProductId) return;
    setRefreshing(true);
    try {
      const data = await compareProduct(compareProductId, true);
      setCompareData(data);
      message.success(t("compare.refreshed"));
    } catch {
      message.error(t("compare.failed"));
    } finally {
      setRefreshing(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportProductsCsv({ ...filters, platform, site, keyword: keyword || undefined });
      message.success(t("products.exportDone", { defaultValue: "已导出" }));
    } catch {
      message.error(t("products.loadFailed"));
    } finally {
      setExporting(false);
    }
  };

  const handleViewDetail = async (id: number) => {
    setDetailLoading(true);
    setDetailOpen(true);
    try {
      const d = await getProductDetail(id);
      setDetail(d);
    } catch {
      message.error(t("products.loadFailed"));
    } finally {
      setDetailLoading(false);
    }
  };

  const stopSyncPolling = () => {
    if (syncPollRef.current) { clearInterval(syncPollRef.current); syncPollRef.current = null; }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncProgress({ state: "PENDING", message: "提交中..." });
    try {
      const res = await triggerSync({ platform, site });
      syncPollRef.current = setInterval(async () => {
        try {
          const st = await getSyncStatus(res.task_id);
          setSyncProgress(st);
          if (st.done || st.state === "SUCCESS" || st.state === "FAILURE") {
            stopSyncPolling();
            setSyncing(false);
            if (st.state === "SUCCESS") {
              const n = st.result?.synced ?? 0;
              const errs = st.result?.errors ?? 0;
              message.success(t("products.syncDone", { n, errs, defaultValue: `同步完成: ${n} 条，失败 ${errs}` }));
              loadData();
            } else {
              message.error(st.error || t("products.syncFailed"));
            }
          }
        } catch { /* ignore */ }
      }, 2000);
    } catch {
      message.error(t("products.syncFailed"));
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
    {
      title: t("products.site"), dataIndex: "site", key: "site", width: 70,
      render: (v: string) => v ? <Tag>{v}</Tag> : "-",
    },
    { title: t("products.category"), dataIndex: "category", key: "category", width: 120 },
    { title: t("products.monthlySales"), dataIndex: "monthly_sales", key: "monthly_sales", width: 110, sorter: true },
    {
      title: t("products.price"), dataIndex: "price", key: "price", width: 80,
      render: (v: number | null, record: ProductItem) => formatPrice(v, record.platform),
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
    {
      title: t("products.detail", { defaultValue: "详情" }), key: "detail", width: 60,
      render: (_: unknown, record: ProductItem) => (
        <Button size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record.id)} />
      ),
    },
    {
      title: t("compare.compare"), key: "compare", width: 60,
      render: (_: unknown, record: ProductItem) => (
        <Button size="small" icon={<SearchOutlined />} onClick={() => handleCompare(record.id)} loading={comparingId === record.id} />
      ),
    },
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
          <Input.Search
            placeholder={t("products.searchPlaceholder", { defaultValue: "搜索标题" })}
            allowClear style={{ width: 200 }}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={() => { setPage(1); loadData(); }}
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
          <Button icon={<DownloadOutlined />} loading={exporting} onClick={handleExport}>
            {t("products.export", { defaultValue: "导出" })}
          </Button>
        </Space>
      </Card>

      {syncing && syncProgress && (
        <Card style={{ marginBottom: 16 }}>
          <Progress
            percent={syncProgress.total ? Math.round(((syncProgress.index ?? 0) / syncProgress.total) * 100) : 30}
            status="active"
            format={() => syncProgress.stage === "upserting"
              ? `${t("products.syncUpserting", { defaultValue: "写入中" })} ${syncProgress.category} (${syncProgress.synced ?? 0})`
              : `${t("products.syncFetching", { defaultValue: "拉取" })} ${syncProgress.category} (${syncProgress.index}/${syncProgress.total})`}
          />
          <span style={{ color: "#8c8c8c", fontSize: 12 }}>{syncProgress.message || syncProgress.stage}</span>
        </Card>
      )}

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

      <Drawer
        title={detail?.title}
        open={detailOpen}
        onClose={() => { setDetailOpen(false); setDetail(null); }}
        width={560}
      >
        {detailLoading ? <Spin /> : detail ? (
          <div>
            <Space wrap style={{ marginBottom: 16 }}>
              <Tag color={detail.platform === "tiktok" ? "magenta" : "orange"}>{(detail.platform || "amazon").toUpperCase()}</Tag>
              {detail.site && <Tag>{detail.site}</Tag>}
              {detail.category && <Tag color="blue">{detail.category}</Tag>}
              <Tag color={detail.match_status === "confirmed" ? "green" : "default"}>{detail.match_status}</Tag>
            </Space>
            {detail.comprehensive_score && (
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={8}><Statistic title={t("products.score")} value={detail.comprehensive_score} precision={1} valueStyle={{ color: "#52c41a", fontWeight: 600 }} /></Col>
                <Col span={8}><Statistic title={t("products.price")} value={formatPrice(detail.price, detail.platform).replace("$","")} prefix="$" /></Col>
                <Col span={8}><Statistic title={t("products.monthlySales")} value={detail.monthly_sales ?? 0} /></Col>
              </Row>
            )}
            <Descriptions title={t("products.metrics", { defaultValue: "指标详情" })} bordered size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label={t("products.reviews")}>{detail.review_count ?? "-"}</Descriptions.Item>
              <Descriptions.Item label="Seller Count">{detail.seller_count ?? "-"}</Descriptions.Item>
              <Descriptions.Item label="Listing Monopoly">{detail.listing_monopoly != null ? `${detail.listing_monopoly}%` : "-"}</Descriptions.Item>
              <Descriptions.Item label="Brand Monopoly">{detail.brand_monopoly != null ? `${detail.brand_monopoly}%` : "-"}</Descriptions.Item>
              <Descriptions.Item label="Seller Monopoly">{detail.seller_monopoly != null ? `${detail.seller_monopoly}%` : "-"}</Descriptions.Item>
              <Descriptions.Item label="New Product Ratio">{detail.new_product_ratio != null ? `${detail.new_product_ratio}%` : "-"}</Descriptions.Item>
            </Descriptions>
            {detail.risk_tags && detail.risk_tags.length > 0 && (
              <Card size="small" title={t("products.risk")} style={{ marginBottom: 16 }}>
                <Space wrap>{detail.risk_tags.map((tag) => <Tag key={tag} color="orange">{tag}</Tag>)}</Space>
              </Card>
            )}
            <Card size="small" title={t("products.priceTrend", { defaultValue: "价格走势(近30天)" })} style={{ marginBottom: 16 }}>
              {detail.metrics_history.length >= 2 ? (
                <Sparkline data={detail.metrics_history.map((m) => m.price)} width={480} height={64} />
              ) : <span style={{ color: "#bfbfbf" }}>{t("monitor.empty")}</span>}
            </Card>
            <Card size="small" title={t("products.salesTrend", { defaultValue: "销量走势" })}>
              {detail.metrics_history.length >= 2 ? (
                <Sparkline data={detail.metrics_history.map((m) => m.monthly_sales)} width={480} height={64} color="#52c41a" />
              ) : <span style={{ color: "#bfbfbf" }}>{t("monitor.empty")}</span>}
            </Card>
          </div>
        ) : <Empty />}
      </Drawer>

      <Modal
        title={
          <Space>
            <span>{t("compare.title")}</span>
            {compareData?.cached && (
              <Tag color="default">
                {t("compare.cached")} {compareData.snapshot_date ? `· ${compareData.snapshot_date}` : ""}
              </Tag>
            )}
            <Button
              size="small"
              type="link"
              icon={<ReloadOutlined spin={refreshing} />}
              onClick={handleRefreshCompare}
              loading={refreshing}
            >
              {t("compare.refresh")}
            </Button>
          </Space>
        }
        open={compareOpen}
        onCancel={() => setCompareOpen(false)}
        footer={null}
        width={720}
      >
        {compareData ? (
          <div>
            {compareData.cost_breakdown && (
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={6}><Statistic title={t("compare.profitUsd")} value={compareData.gross_profit_usd ?? 0} prefix="$" valueStyle={{ color: (compareData.gross_profit_usd ?? 0) > 0 ? "#52c41a" : "#ff4d4f" }} /></Col>
                <Col span={6}><Statistic title={t("compare.margin")} value={compareData.profit_margin ?? 0} suffix="%" valueStyle={{ color: (compareData.profit_margin ?? 0) > 0 ? "#52c41a" : "#ff4d4f" }} /></Col>
                <Col span={6}><Statistic title={t("compare.sellCny")} value={compareData.platform_price_cny ?? 0} prefix="¥" /></Col>
                <Col span={6}><Statistic title={t("compare.fxRate")} value={compareData.exchange_rate} /></Col>
              </Row>
            )}
            {compareData.best_match ? (
              <Card size="small" title={`${t("compare.bestMatch")} (${compareData.best_match.similarity}%)`} style={{ marginBottom: 16 }}>
                <p><strong>{compareData.best_match.title}</strong></p>
                <Space>
                  <Tag color="orange">¥{compareData.best_match.price_cny} CNY</Tag>
                  <Tag color="blue">${compareData.best_match.price_usd} USD</Tag>
                  <Tag>{compareData.best_match.store_name}</Tag>
                </Space>
              </Card>
            ) : <Empty description={t("compare.noMatch")} />}
            {compareData.cost_breakdown && (
              <Descriptions title={t("compare.costBreakdown")} bordered size="small" column={2}>
                <Descriptions.Item label={t("compare.purchase")}>¥{compareData.cost_breakdown.purchase_price}</Descriptions.Item>
                <Descriptions.Item label={t("compare.shipping")}>¥{compareData.cost_breakdown.international_shipping}</Descriptions.Item>
                <Descriptions.Item label={t("compare.customs") + " (5%)"}>¥{compareData.cost_breakdown.customs_duty}</Descriptions.Item>
                <Descriptions.Item label={t("compare.commission") + " (8%)"}>¥{compareData.cost_breakdown.platform_commission}</Descriptions.Item>
                <Descriptions.Item label={t("compare.packaging")}>¥{compareData.cost_breakdown.packaging}</Descriptions.Item>
                <Descriptions.Item label={t("compare.returnLoss") + " (3%)"}>¥{compareData.cost_breakdown.return_loss}</Descriptions.Item>
                <Descriptions.Item label={t("compare.totalCost")} span={2}><strong>¥{compareData.cost_breakdown.total_cost} (${compareData.cost_breakdown.total_cost_usd})</strong></Descriptions.Item>
              </Descriptions>
            )}
          </div>
        ) : <Spin />}
      </Modal>
    </div>
  );
}
