import request from "./index";

export interface ProductItem {
  id: number;
  sorftime_id: string;
  title: string;
  platform: string;
  site: string;
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
  site?: string;
  category?: string;
  keyword?: string;
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

export const triggerSync = (params?: { platform?: string; site?: string; category?: string }) =>
  request.post<{ data: { task_id: string; platform: string; site: string } }>("/products/sync", null, { params }).then((r) => r.data.data);

export interface SyncStatus {
  state: string;
  stage?: string;
  category?: string;
  index?: number;
  total?: number;
  fetched?: number;
  synced?: number;
  done?: boolean;
  result?: { synced?: number; errors?: number; auto_matched?: number };
  error?: string;
  message?: string;
}

export const getSyncStatus = (taskId: string) =>
  request.get<{ data: SyncStatus }>(`/products/sync/status/${taskId}`).then((r) => r.data.data);

export const getWeeklyRecommendations = () =>
  request
    .get<{ data: { items: unknown[]; week_start: string } }>("/products/recommendations/weekly")
    .then((r) => r.data.data);


export interface MetricHistoryPoint {
  date: string;
  monthly_sales: number | null;
  price: number | null;
  review_count: number | null;
}

export interface ProductDetail {
  id: number;
  sorftime_id: string;
  title: string;
  category: string | null;
  platform: string;
  site: string;
  monthly_sales: number | null;
  price: number | null;
  listing_monopoly: number | null;
  brand_monopoly: number | null;
  seller_monopoly: number | null;
  review_count: number | null;
  new_product_ratio: number | null;
  seller_count: number | null;
  amazon_self_ratio: number | null;
  comprehensive_score: number | null;
  risk_tags: string[] | null;
  match_status: string;
  data_date: string | null;
  metrics_history: MetricHistoryPoint[];
}

export const getProductDetail = (id: number) =>
  request.get<{ data: ProductDetail }>(`/products/${id}`).then((r) => r.data.data);


export const exportProductsCsv = (params: ProductListParams = {}) =>
  request
    .get("/products/export/csv", { params, responseType: "blob" })
    .then((res) => {
      const url = window.URL.createObjectURL(new Blob([res.data as BlobPart]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "products.csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    });
