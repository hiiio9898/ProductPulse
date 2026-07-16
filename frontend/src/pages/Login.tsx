import { useState } from "react";
import { Card, Input, Button, Typography, message } from "antd";
import { LockOutlined, GlobalOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import request from "../api/index";

const { Title, Text } = Typography;

interface Props {
  onLogin: (token: string) => void;
}

export default function Login({ onLogin }: Props) {
  const { t, i18n } = useTranslation();
  const [tokenInput, setTokenInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!tokenInput.trim()) {
      message.warning(t("login.enterToken"));
      return;
    }
    setLoading(true);
    try {
      const res = await request.get("/dashboard/overview", {
        headers: { Authorization: `Bearer ${tokenInput.trim()}` },
      });
      if (res.data.code === 0) {
        localStorage.setItem("pp_token", tokenInput.trim());
        onLogin(tokenInput.trim());
        message.success(t("login.loginSuccess"));
      }
    } catch {
      message.error(t("login.invalidToken"));
    } finally {
      setLoading(false);
    }
  };

  const changeLang = (lang: string) => {
    i18n.changeLanguage(lang);
    localStorage.setItem("pp_lang", lang);
    window.location.reload();
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "linear-gradient(135deg, #1677ff 0%, #0958d9 100%)" }}>
      <Card style={{ width: 400, boxShadow: "0 8px 24px rgba(0,0,0,0.15)" }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <Title level={3} style={{ marginBottom: 4 }}>ProductPulse</Title>
        </div>
        <Input.Password
          size="large"
          placeholder={t("login.enterToken")}
          prefix={<LockOutlined />}
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
          onPressEnter={handleLogin}
          style={{ marginBottom: 16 }}
        />
        <Button type="primary" size="large" block loading={loading} onClick={handleLogin}>
          {t("login.login")}
        </Button>
        <Text type="secondary" style={{ display: "block", marginTop: 12, fontSize: 12, textAlign: "center" }}>
          {t("login.tokenHint")}
        </Text>
        <div style={{ textAlign: "center", marginTop: 12 }}>
          <Button type="text" size="small" icon={<GlobalOutlined />} onClick={() => changeLang(i18n.language === "zh" ? "en" : "zh")}>
            {i18n.language === "zh" ? "English" : "\u4e2d\u6587"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
