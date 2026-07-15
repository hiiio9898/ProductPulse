import { Typography } from "antd";

const { Title, Paragraph } = Typography;

export default function Products() {
  return (
    <div>
      <Title level={3}>选品中心</Title>
      <Paragraph type="secondary">
        页面开发中（Phase 1 实现）。此占位遵循页面状态规范：加载中 / 空数据 / 错误 / 延迟 / 成功。
      </Paragraph>
    </div>
  );
}