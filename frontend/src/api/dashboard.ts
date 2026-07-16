import request from "./index";

export interface OverviewData {
  recommendations_today: number;
  alerts_count: number;
  pending_sku_count: number;
  top_score: number;
  top_product_title: string | null;
}

export interface TrendItem {
  date: string;
  product_count: number;
  avg_sales: number;
}

export const getOverview = () =>
  request.get<{ data: OverviewData }>("/dashboard/overview").then((r) => r.data.data);

export const getTrends = () =>
  request.get<{ data: TrendItem[] }>("/dashboard/trends").then((r) => r.data.data);