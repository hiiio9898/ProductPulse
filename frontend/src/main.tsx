import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import enUS from "antd/locale/en_US";
import dayjs from "dayjs";
import "dayjs/locale/zh-cn";
import "dayjs/locale/en";
import App from "./App";
import "./i18n";
import "./index.css";

const antdLocale = localStorage.getItem("pp_lang") === "zh" ? zhCN : enUS;
dayjs.locale(localStorage.getItem("pp_lang") === "zh" ? "zh-cn" : "en");

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider locale={antdLocale}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>
);