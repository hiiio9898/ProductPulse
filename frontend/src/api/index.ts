import axios, { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from "axios";
import { message } from "antd";

// 统一响应体接口
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
  timestamp: string;
}

const request = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
});

// 请求拦截：注入鉴权 token
request.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem("pp_token") || "";
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截：校验业务码，处理 HTTP 错误（不改变返回类型，调用方取 response.data）
request.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const body = response.data;
    if (body.code !== 0) {
      message.error(body.message || "请求失败");
      return Promise.reject(body);
    }
    return response;
  },
  (error: AxiosError<ApiResponse>) => {
    const status = error.response?.status;
    const body = error.response?.data;
    if (status === 401) {
      message.error("登录已过期，请重新登录");
      // 单用户系统：可跳转登录页（后续补充）
    } else if (status === 429) {
      message.error("请求过于频繁，请稍后再试");
    } else {
      message.error(body?.message || "网络异常，请稍后重试");
    }
    return Promise.reject(error);
  }
);

export default request;