import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, theme, Button, Dropdown } from "antd";
import {
  DashboardOutlined,
  AppstoreOutlined,
  RadarChartOutlined,
  FileTextOutlined,
  SettingOutlined,
  LogoutOutlined,
  GlobalOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";

const { Header, Sider, Content, Footer } = Layout;

export default function MainLayout() {
  const { t, i18n } = useTranslation();
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { token: { colorBgContainer } } = theme.useToken();

  const handleLogout = () => {
    localStorage.removeItem("pp_token");
    navigate("/");
    window.location.reload();
  };

  const changeLang = (lang: string) => {
    i18n.changeLanguage(lang);
    localStorage.setItem("pp_lang", lang);
    window.location.reload();
  };

  const menuItems = [
    { key: "/dashboard", icon: <DashboardOutlined />, label: t("nav.dashboard") },
    { key: "/products", icon: <AppstoreOutlined />, label: t("nav.products") },
    { key: "/monitor", icon: <RadarChartOutlined />, label: t("nav.monitor") },
    { key: "/reports", icon: <FileTextOutlined />, label: t("nav.reports") },
    { key: "/config", icon: <SettingOutlined />, label: t("nav.config") },
  ];

  const langMenu = {
    items: [
      { key: "en", label: "English", onClick: () => changeLang("en") },
      { key: "zh", label: "\u4e2d\u6587", onClick: () => changeLang("zh") },
    ],
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
          <Dropdown menu={langMenu}>
            <Button type="text" icon={<GlobalOutlined />}>
              {i18n.language === "zh" ? "\u4e2d\u6587" : "English"}
            </Button>
          </Dropdown>
          <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout}>
            {t("common.logout")}
          </Button>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: colorBgContainer, minHeight: 280 }}>
          <Outlet />
        </Content>
        <Footer style={{ textAlign: "center", color: "#8c8c8c" }}>
          {t("footer.lastUpdated")}: -- | {t("footer.status")}: \u2705 {t("footer.normal")}
        </Footer>
      </Layout>
    </Layout>
  );
}
