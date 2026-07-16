import { useEffect, useState } from "react";
import { Table, Card, Select, Space, Button, Tag, InputNumber, Spin, Empty, message } from "antd";
import { SyncOutlined } from "@ant-design/icons";
import { getProducts, triggerSync, type ProductItem, type ProductListParams } from "../api/products";

const riskColors: Record<string, string> = { danger: "red", warning: "orange", info: "blue" };

export default function Products() {
  const [data, setData] = useState<ProductItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<ProductListParams>({ sort_by: "score", sort_order: "desc" });

  const loadData = async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await getProducts({ ...filters, page });
      setData(res.items);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [page, filters]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await triggerSync();
      message.success("同步任务已提交");
    } catch {
      message.error("同步触发失败");
    } finally {
      setSyncing(false);
    }
  };

  if (loading && data.length === 0) return <Spin size="large" />;
  if (error && data.length === 0) {
    return <Empty description="数据加载失败"><a onClick={loadData}>点击重试</a></Empty>;
  }

  const columns = [
    { title: "标题", dataIndex: "title", key: "title", ellipsis: true, width: 280 },
    { title: "品类", dataIndex: "category", key: "category", width: 100 },
    { title: "月销量", dataIndex: "monthly_sales", key: "monthly_sales", width: 90, sorter: true },
    { title: "价格", dataIndex: "price", key: "price", width: 80, render: (v: number | null) => v ? `$${v}` : "-" },
    {
      title: "综合评分", dataIndex: "comprehensive_score", key: "score", width: 100,
      sorter: true, defaultSortOrder: "descend" as const,
      render: (v: number | null) => v ? <span style={{ color: "#52c41a", fontWeight: 600 }}>{v.toFixed(1)}</span> : "-",
    },
    { title: "评论数", dataIndex: "review_count", key: "review_count", width: 80 },
    {
      title: "风险标签", dataIndex: "risk_tags", key: "risk_tags", width: 120,
      render: (tags: string[] | null) => tags?.length
        ? tags.map((t) => <Tag key={t} color={riskColors.warning}>{t}</Tag>)
        : <span style={{ color: "#8c8c8c" }}>无</span>,
    },
    { title: "匹配状态", dataIndex: "match_status", key: "match_status", width: 90 },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            placeholder="品类筛选" allowClear style={{ width: 160 }}
            options={[
              { value: "3D printer filament", label: "3D打印耗材" },
              { value: "sublimation ink", label: "热转印墨水" },
              { value: "photo paper", label: "相纸" },
            ]}
            onChange={(v) => { setPage(1); setFilters({ ...filters, category: v }); }}
          />
          <Select
            placeholder="匹配状态" allowClear style={{ width: 120 }}
            options={[
              { value: "pending", label: "待匹配" },
              { value: "confirmed", label: "已确认" },
              { value: "rejected", label: "已拒绝" },
            ]}
            onChange={(v) => { setPage(1); setFilters({ ...filters, match_status: v }); }}
          />
          <span>最低评分：</span>
          <InputNumber
            placeholder="0" min={0} max={100} style={{ width: 80 }}
            onChange={(v) => { setPage(1); setFilters({ ...filters, min_score: v ?? undefined }); }}
          />
          <Button type="primary" icon={<SyncOutlined spin={syncing} />} loading={syncing} onClick={handleSync}>
            同步数据
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
          showTotal: (total) => `共 ${total} 条`,
        }}
        locale={{ emptyText: <Empty description="暂无符合产品，试试调整筛选条件" /> }}
      />
    </div>
  );
}