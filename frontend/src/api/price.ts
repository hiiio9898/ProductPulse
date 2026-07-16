import request from "./index";

export interface MatchCandidate {
  source_id: string;
  title: string;
  price_cny: number;
  price_usd: number;
  sales_30d: number | null;
  store_name: string;
  similarity: number;
}

export interface PriceAlert {
  product_id: number;
  title: string;
  price_change_percent: number;
  price_1688: number | null;
  alert: string;
  snapshot_date: string;
}

export const matchProduct = (productId: number) =>
  request
    .get<{ data: { product_id: number; candidates: MatchCandidate[] } }>(`/price/match/${productId}`)
    .then((r) => r.data.data);

// 注意：后端是 POST /price/match/{id}，这里用 post
export const triggerMatch = (productId: number) =>
  request
    .post<{ data: { product_id: number; candidates: MatchCandidate[] } }>(`/price/match/${productId}`)
    .then((r) => r.data.data);

export const confirmMatch = (productId: number, body: { source_id: string; source_title: string; match_status: string; price_cny?: number }) =>
  request.put<{ data: unknown }>(`/price/confirm/${productId}`, body).then((r) => r.data.data);

export const checkPrice = (productId: number) =>
  request.get<{ data: Record<string, unknown> | null }>(`/price/check/${productId}`).then((r) => r.data.data);

export const refreshAllPrices = () =>
  request.post<{ data: { task_id: string } }>("/price/refresh-all").then((r) => r.data.data);

export const getPriceAlerts = () =>
  request.get<{ data: { items: PriceAlert[]; total: number } }>("/price/alerts").then((r) => r.data.data);