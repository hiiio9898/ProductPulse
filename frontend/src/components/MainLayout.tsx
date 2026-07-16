import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, theme, Button } from "antd";
import {
  DashboardOutlined,
  AppstoreOutlined,
  RadarChartOutlined,
  FileTextOutlined,
  SettingOutlined,
  LogoutOutlined,
} from "@ant-design/icons";

const { Header, Sider, Content, Footer } = Layout;

const menuItems = [
  { key: "/dashboard", icon: <DashboardOutlined />, label: "首页" },
  { key: "/products", icon: <AppstoreOutlined />, label: "选品" },
  { key: "/monitor", icon: <RadarChartOutlined />, label: "监控" },
  { key: "/reports", icon: <FileTextOutlined />, label: "日报" },
  { key: "/config", icon: <SettingOutlined />, label: "配置" },
];

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { token: { colorBgContainer } } = theme.useToken();

  const handleLogout = () => {
    localStorage.removeItem("pp_token");
    navigate("/");
    window.location.reload();
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} width={200} theme="light">
        <div style={{ height: 48, margin: 12, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, color: "#1890ff" }}>
          {collapsed ? "PP" : "ProductPulse"}
        </div>
        <Menu mode="inline" selectedKeys={[location.pathname]} items={menuItems} onClick={({ key }) => navigate(key)} />
      </Sider>
      <Layout>
        <Header style={{ background: colorBgContainer, padding: "0 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout}>登出</Button>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: colorBgContainer, minHeight: 280 }}>
          <Outlet />
        </Content>
        <Footer style={{ textAlign: "center", color: "#8c8c8c" }}>Last updated: -- | Status: OK</Footer>
      </Layout>
    </Layout>
  );
}
