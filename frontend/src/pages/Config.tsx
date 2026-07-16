import { useEffect, useState } from "react";
import { Tabs, Form, InputNumber, Button, Table, Tag, message, Spin } from "antd";
import { useTranslation } from "react-i18next";
import { getConfig, updateThresholds, getRiskRules, type RiskRule } from "../api/config";


export default function Config() {
  const { t } = useTranslation();
  const [tab, setTab] = useState("thresholds");
  const [thresholdForm] = Form.useForm();
  const [rules, setRules] = useState<RiskRule[]>([]);
  const [loading, setLoading] = useState(false);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const config = await getConfig();
      const thresholds = config["algorithm.thresholds"] as Record<string, number>;
      if (thresholds) thresholdForm.setFieldsValue(thresholds);
    } catch { message.error(t("products.loadFailed")); }
    finally { setLoading(false); }
  };

  const loadRules = async () => {
    setLoading(true);
    try {
      const res = await getRiskRules();
      setRules(res.items);
    } catch { message.error(t("products.loadFailed")); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    if (tab === "thresholds" || tab === "ai") loadConfig();
    if (tab === "risk") loadRules();
  }, [tab]);

  const handleSaveThresholds = async (values: Record<string, number>) => {
    try {
      await updateThresholds(values);
      message.success(t("config.saved"));
    } catch { message.error(t("products.loadFailed")); }
  };

  const levelColors: Record<string, string> = { danger: "red", warning: "orange", info: "blue" };

  const columns = [
    { title: t("config.riskRules"), dataIndex: "rule_name", key: "rule_name" },
    { title: t("products.risk"), dataIndex: "risk_level", key: "risk_level", render: (v: string) => <Tag color={levelColors[v]}>{v}</Tag> },
    { title: t("products.risk"), dataIndex: "risk_tag", key: "risk_tag" },
    { title: t("monitor.alert"), dataIndex: "alert_message", key: "alert_message", ellipsis: true },
  ];

  if (loading) return <Spin size="large" />;

  return (
    <Tabs
      activeKey={tab}
      onChange={setTab}
      items={[
        {
          key: "thresholds",
          label: t("config.thresholds"),
          children: (
            <Form form={thresholdForm} layout="inline" onFinish={handleSaveThresholds}>
              <Form.Item name="monthly_sales_min" label={`${t("products.monthlySales")} Min`}><InputNumber /></Form.Item>
              <Form.Item name="monthly_sales_max" label={`${t("products.monthlySales")} Max`}><InputNumber /></Form.Item>
              <Form.Item name="listing_monopoly" label="Listing %"><InputNumber /></Form.Item>
              <Form.Item name="brand_monopoly" label="Brand %"><InputNumber /></Form.Item>
              <Form.Item name="seller_monopoly" label="Seller %"><InputNumber /></Form.Item>
              <Form.Item name="new_product_ratio" label="New %"><InputNumber /></Form.Item>
              <Form.Item><Button type="primary" htmlType="submit">{t("config.save")}</Button></Form.Item>
            </Form>
          ),
        },
        {
          key: "risk",
          label: t("config.riskRules"),
          children: (
            <Table dataSource={rules} columns={columns} rowKey="id" size="middle" pagination={false} />
          ),
        },
        {
          key: "ai",
          label: t("config.aiModels"),
          children: <div style={{ color: "#8c8c8c" }}>GLM: glm-5.2 (primary) {"\u2192"} glm-4.7 {"\u2192"} glm-4-flash</div>,
        },
      ]}
    />
  );
}
