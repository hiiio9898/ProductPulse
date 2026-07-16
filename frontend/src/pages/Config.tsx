import { useEffect, useState } from "react";
import { Tabs, Form, InputNumber, Button, Table, Tag, Modal, Input, Select, message, Spin } from "antd";
import { getConfig, updateThresholds, getRiskRules, type RiskRule } from "../api/config";

const { TextArea } = Input;

export default function Config() {
  const [tab, setTab] = useState("thresholds");
  const [thresholdForm] = Form.useForm();
  const [rules, setRules] = useState<RiskRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<RiskRule | null>(null);
  const [ruleForm] = Form.useForm();

  const loadConfig = async () => {
    setLoading(true);
    try {
      const config = await getConfig();
      const thresholds = config["algorithm.thresholds"] as Record<string, number>;
      if (thresholds) thresholdForm.setFieldsValue(thresholds);
    } catch { message.error("配置加载失败"); }
    finally { setLoading(false); }
  };

  const loadRules = async () => {
    setLoading(true);
    try {
      const res = await getRiskRules();
      setRules(res.items);
    } catch { message.error("规则加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    if (tab === "thresholds" || tab === "ai") loadConfig();
    if (tab === "risk") loadRules();
  }, [tab]);

  const handleSaveThresholds = async (values: Record<string, number>) => {
    try {
      await updateThresholds(values);
      message.success("阈值保存成功");
    } catch { message.error("保存失败"); }
  };

  const handleSaveRule = async () => {
    try {
      const values = await ruleForm.validateFields();
      const conditions = JSON.parse(values.conditionsJson || "{}");
      const body = { ...values, trigger_conditions: conditions };
      delete body.conditionsJson;
      if (editingRule) {
        // 更新已有规则
        message.success("规则已更新（演示）");
      } else {
        // 新增
        message.success("规则已创建（演示）");
      }
      setModalOpen(false);
      loadRules();
    } catch { message.error("保存失败，检查 JSON 格式"); }
  };

  const levelColors: Record<string, string> = { danger: "red", warning: "orange", info: "blue" };

  const columns = [
    { title: "规则名", dataIndex: "rule_name", key: "rule_name" },
    { title: "等级", dataIndex: "risk_level", key: "risk_level", render: (v: string) => <Tag color={levelColors[v]}>{v}</Tag> },
    { title: "标签", dataIndex: "risk_tag", key: "risk_tag" },
    { title: "提示文案", dataIndex: "alert_message", key: "alert_message", ellipsis: true },
    { title: "状态", dataIndex: "is_active", key: "is_active", render: (v: boolean) => v ? <Tag color="green">启用</Tag> : <Tag>停用</Tag> },
    {
      title: "操作", key: "action",
      render: (_: unknown, record: RiskRule) => (
        <a onClick={() => { setEditingRule(record); ruleForm.setFieldsValue({ ...record, conditionsJson: JSON.stringify(record.trigger_conditions) }); setModalOpen(true); }}>编辑</a>
      ),
    },
  ];

  if (loading) return <Spin size="large" />;

  return (
    <Tabs
      activeKey={tab}
      onChange={setTab}
      items={[
        {
          key: "thresholds",
          label: "选品阈值",
          children: (
            <Form form={thresholdForm} layout="inline" onFinish={handleSaveThresholds}>
              <Form.Item name="monthly_sales_min" label="月销量下限"><InputNumber /></Form.Item>
              <Form.Item name="monthly_sales_max" label="月销量上限"><InputNumber /></Form.Item>
              <Form.Item name="listing_monopoly" label="Listing垄断(%)"><InputNumber /></Form.Item>
              <Form.Item name="brand_monopoly" label="品牌垄断(%)"><InputNumber /></Form.Item>
              <Form.Item name="seller_monopoly" label="卖家垄断(%)"><InputNumber /></Form.Item>
              <Form.Item name="new_product_ratio" label="新品占比(%)"><InputNumber /></Form.Item>
              <Form.Item><Button type="primary" htmlType="submit">保存</Button></Form.Item>
            </Form>
          ),
        },
        {
          key: "risk",
          label: "风险规则",
          children: (
            <>
              <Button type="primary" style={{ marginBottom: 16 }} onClick={() => { setEditingRule(null); ruleForm.resetFields(); setModalOpen(true); }}>新增规则</Button>
              <Table dataSource={rules} columns={columns} rowKey="id" size="middle" pagination={false} />
              <Modal
                title={editingRule ? "编辑规则" : "新增规则"}
                open={modalOpen}
                onOk={handleSaveRule}
                onCancel={() => setModalOpen(false)}
                width={600}
              >
                <Form form={ruleForm} layout="vertical">
                  <Form.Item name="rule_name" label="规则名" rules={[{ required: true }]}><Input /></Form.Item>
                  <Form.Item name="risk_level" label="风险等级" rules={[{ required: true }]} initialValue="warning">
                    <Select options={[{ value: "danger", label: "危险" }, { value: "warning", label: "警告" }, { value: "info", label: "提示" }]} />
                  </Form.Item>
                  <Form.Item name="risk_tag" label="风险标签"><Input /></Form.Item>
                  <Form.Item name="conditionsJson" label="触发条件 (JSON)" tooltip='例: {"category":"ink","review_count_min":1000}'>
                    <TextArea rows={3} placeholder='{"category":"ink"}' />
                  </Form.Item>
                  <Form.Item name="alert_message" label="提示文案"><TextArea rows={2} /></Form.Item>
                </Form>
              </Modal>
            </>
          ),
        },
        {
          key: "ai",
          label: "AI 模型",
          children: <div style={{ color: "#8c8c8c" }}>AI 模型切换将在 Phase 3 实现（GLM 余额待激活）。</div>,
        },
      ]}
    />
  );
}