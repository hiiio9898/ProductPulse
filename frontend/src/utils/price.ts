/**
 * 价格格式化工具。
 *
 * 不同平台入库单位不同：
 * - Amazon：美分（cents），需 /100 换算成美元
 * - TikTok：已是美元，直接用
 */
export function formatPrice(price: number | null, platform: string | null | undefined): string {
  if (price === null || price === undefined) return "-";
  const pf = (platform || "").toLowerCase();
  // Amazon 入库为美分，TikTok 入库为美元
  const usd = pf === "amazon" ? price / 100 : price;
  return `$${usd.toFixed(2)}`;
}

/** 取平台对应的美元价格数值（供排序/计算用） */
export function priceToUsd(price: number, platform: string | null | undefined): number {
  const pf = (platform || "").toLowerCase();
  return pf === "amazon" ? price / 100 : price;
}
