import request from "./index";

export interface ProductItem {
  id: number;
  sorftime_id: string;
  title: string;
  platform: string;
  category: string | null;
  monthly_sales: number | null;
  price: number | null;
  review_count: number | null;
  comprehensive_score: number | null;
  risk_tags: string[] | null;
  match_status: string;
  data_date: string | null;
}

export interface ProductListParams {
  platform?: string;
  category?: string;
  match_status?: string;
  min_score?: number;
  sort_by?: "score" | "price" | "sales";
  sort_order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export const getProducts = (params: ProductListParams = {}) =>
  request
    .get<{ data: { items: ProductItem[]; page: number; page_size: number } }>("/products/", { params })
    .then((r) => r.data.data);

export const getProductDetail = (id: number) =>
  request.get<{ data: Record<string, unknown> }>(`/products/${id}`).then((r) => r.data.data);

export const triggerSync = (params?: { platform?: string; site?: string; category?: string }) =>
  request.post<{ data: { task_id: string; platform: string; site: string } }>("/products/sync", null, { params }).then((r) => r.data.data);

export const getWeeklyRecommendations = () =>
  request
    .get<{ data: { items: unknown[]; week_start: string } }>("/products/recommendations/weekly")
    .then((r) => r.data.data);