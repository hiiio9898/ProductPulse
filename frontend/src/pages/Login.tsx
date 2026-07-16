import { useState } from "react";
import { Card, Input, Button, Typography, message } from "antd";
import { LockOutlined } from "@ant-design/icons";
import request from "../api/index";

const { Title, Text } = Typography;

interface Props {
  onLogin: (token: string) => void;
}

export default function Login({ onLogin }: Props) {
  const [tokenInput, setTokenInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!tokenInput.trim()) {
      message.warning("Enter access token");
      return;
    }
    setLoading(true);
    try {
      // 用输入的 token 临时调一个需要鉴权的接口验证
      const res = await request.get("/dashboard/overview", {
        headers: { Authorization: `Bearer ${tokenInput.trim()}` },
      });
      if (res.data.code === 0) {
        localStorage.setItem("pp_token", tokenInput.trim());
        onLogin(tokenInput.trim());
        message.success("Login success");
      }
    } catch {
      message.error("Invalid token, please check");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #1677ff 0%, #0958d9 100%)",
      }}
    >
      <Card style={{ width: 400, boxShadow: "0 8px 24px rgba(0,0,0,0.15)" }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <Title level={3} style={{ marginBottom: 4 }}>
            ProductPulse
          </Title>
        </div>
        <Input.Password
          size="large"
          placeholder="Enter access token"
          prefix={<LockOutlined />}
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
          onPressEnter={handleLogin}
          style={{ marginBottom: 16 }}
        />
        <Button
          type="primary"
          size="large"
          block
          loading={loading}
          onClick={handleLogin}
        >
          Login
        </Button>
        <Text
          type="secondary"
          style={{ display: "block", marginTop: 12, fontSize: 12, textAlign: "center" }}
        >
          Token configured by admin (APP_SECRET_KEY in backend .env)
        </Text>
      </Card>
    </div>
  );
}