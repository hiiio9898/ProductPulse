"""Sorftime 接口的 Pydantic 入参/出参类型定义。

与「附录A-Sorftime接口规格.md」一一对应。返回类型对应 Sorftime 面向 AI 的字符串，
适配层解析后填充这些结构；无法解析的字段留 None。
"""

from typing import Any, Optional

from pydantic import BaseModel


class AmzSite(str):
    """亚马逊站点枚举值。"""

    US = "US"
    GB = "GB"
    DE = "DE"
    FR = "FR"
    IN = "IN"
    CA = "CA"
    JP = "JP"
    ES = "ES"
    IT = "IT"
    MX = "MX"
    AE = "AE"
    AU = "AU"
    BR = "BR"
    SA = "SA"


class TrendType(str):
    SALES_VOLUME = "SalesVolume"
    SALES_AMOUNT = "SalesAmount"
    PRICE = "Price"
    RANK = "Rank"


class ReviewType(str):
    BOTH = "Both"
    POSITIVE = "Positive"
    NEGATIVE = "Negative"


class DeliveryType(str):
    BOTH = "Both"
    FBM = "FBM"
    FBA = "FBA"


# ---------- 出参结构 ----------

class SimilarFeature(BaseModel):
    feature: str
    product_share: Optional[str] = None
    sales_share: Optional[str] = None
    description: Optional[str] = None


class ProductDetail(BaseModel):
    asin: str
    parent_asin: Optional[str] = None
    title: Optional[str] = None
    image: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[float] = None
    ratings_count: Optional[int] = None
    brand: Optional[str] = None
    monthly_sales: Optional[int] = None
    monthly_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    gross_margin: Optional[float] = None
    fba_fee: Optional[float] = None
    package_size: Optional[str] = None
    weight_g: Optional[int] = None
    aplus: Optional[bool] = None
    seller_country: Optional[str] = None
    raw: Any = None


class ProductListItem(BaseModel):
    asin: str
    parent_asin: Optional[str] = None
    title: Optional[str] = None
    image: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[float] = None
    ratings_count: Optional[int] = None
    brand: Optional[str] = None
    monthly_sales: Optional[int] = None
    monthly_revenue: Optional[float] = None
    potential_index: Optional[float] = None
    delivery_type: Optional[str] = None
    seller_country: Optional[str] = None
    aplus: Optional[bool] = None
    raw: Any = None


class Variation(BaseModel):
    asin: str
    attribute: Optional[str] = None
    monthly_sales_range: Optional[str] = None


class TrafficTerm(BaseModel):
    keyword: str
    monthly_search_volume: Optional[int] = None
    suggested_bid: Optional[str] = None
    position: Optional[str] = None


class Review(BaseModel):
    attribute: Optional[str] = None
    date: Optional[str] = None
    rating: Optional[float] = None
    title: Optional[str] = None
    content: Optional[str] = None


class CustomersSayKeyword(BaseModel):
    keyword: str
    description: Optional[str] = None
    total_mentions: Optional[int] = None
    positive_count: Optional[int] = None
    negative_count: Optional[int] = None


class CustomersSay(BaseModel):
    asin: str
    ai_summary: Optional[str] = None
    keywords: list[CustomersSayKeyword] = []