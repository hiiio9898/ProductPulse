# 附录 A：Sorftime 亚马逊数据 API 接口规格

> 数据来源：Sorftime 选品情报平台，提供亚马逊（Amazon）多站点电商数据。
> 本文档为系统接入 Sorftime 时使用的真实接口清单，供 `adapters/sorftime.py` 与选品算法引擎参考。
> 最后更新：2026-07-15

## A.1 通用约定

| 项 | 说明 |
|----|------|
| 支持站点 | US, GB, DE, FR, IN, CA, JP, ES, IT, MX, AE, AU, BR, SA |
| 分页 | page 参数，每页返回 20 条 |
| 返回格式 | 面向 AI 大模型的字符串（非严格 JSON，解析时需做容错） |
| 计费 | 按调用次数扣减（各接口标注「调用消耗」） |
| 缓存策略 | 适配层统一 Redis 缓存，TTL 24h，避免重复计费 |

## A.2 接口清单（13 个）

### 1. 相似产品特征 `similar_product_feature`（消耗 5）
查询类目热销产品的共有特征，用于卖点提炼与差异化定位。
- `amzSite` String 必填
- `productName` String 必填（类目名称）
- 返回：产品特点 / 产品数量占比 / 月销量占比 / 特点说明

### 2. 产品详情 `product_detail`（消耗 1）
查询单个产品完整详情（销量、评价、属性、毛利、FBA 等）。
- `amzSite` String 必填
- `asin` String 必填
- 返回：标题/价格/星级/评论数/品牌/月销量/月销额/毛利/毛利率/FBA费用/包装尺寸/重量/APlus 等

### 3. 产品变体查询 `product_variations`（消耗 2）
查询产品子体明细（不同规格的销售表现）。
- `amzSite` String 必填
- `asin` String 必填（单 ASIN）
- 返回：各子体 ASIN + 属性 + 子体月销量区间

### 4. 产品历史趋势 `product_trend`（消耗 1）
查询月销量 / 月销额 / 价格 / 大类排名的历史趋势。
- `amzSite` String 必填
- `asin` String 必填（单 ASIN）
- `productTrendType` String 可选：SalesVolume / SalesAmount / Price / Rank
- 返回：时间序列字符串（如 `2024年05月=98211,...`）

### 5. 产品评论 `product_reviews`（消耗 5）
查询近一年用户评论，最多 100 条。
- `amzSite` String 必填
- `asin` String 必填（单 ASIN）
- `reviewType` String 可选：Both / Positive / Negative
- 返回：评论属性/日期/评星/标题/正文

### 6. 潜力产品搜索 `potential_product`（消耗 1）
搜索潜力产品（新上架高增长）。
- `amzSite` String 必填（支持 US / GB / DE）
- `searchName` String 可选
- `price_min/max` Number 可选
- `month_sales_volume_min/max` Integer 可选
- `delivery_type` String 可选：Both / FBM / FBA
- `page` Integer 可选
- 返回：含「产品潜力指数」的产品列表

### 7. 选产品（实时） `product_search`（消耗 1）
实时产品搜索，支持多维度筛选，默认按月销量倒序。
- `amzSite` String 必填
- `searchName/brand/seller_name/property_name` String 必填（至少其一）
- 价格/月销/星级/评论数/子体排名/发货方式/季节性 可选筛选
- `sortby_potential_index` Boolean 可选
- `page` Integer 可选
- 返回：产品列表（含潜力指数、卖家国籍、APlus）

### 8. 产品流量词反查 `product_traffic_terms`（消耗 1）
反查产品在哪些关键词前 3 页曝光，按最后曝光时间倒序。
- `amzSite` String 必填
- `asin` String 必填
- `page` Integer 可选
- 返回：关键词/月搜索量/推荐竞价/自然位&广告位/曝光时间

### 9. 竞品关键词分析 `competitor_product_keywords`（消耗 1）
竞品在核心关键词下的自然曝光位置（排除广告）。
- `keywordSupportSite` String 必填
- `asin` String 必填
- `page` Integer 可选
- 返回：关键词/曝光位置/月搜索量

### 10. 产品关键词排名趋势 `product_ranking_trend_by_keyword`（消耗 1）
产品在指定关键词下的排名趋势。
- `amzSite` String 必填
- `asin` String 必填
- `keyword` String 必填
- `page` Integer 可选
- 返回：page/position/time 时间序列

### 11. 产品分析报告 `product_report`（消耗 1）
工作流引导工具，传入 ASIN 后引导依次调用 detail/category_report/reviews/traffic_terms/keyword_extends。本工具不返回数据。

### 12. 选产品（历史） `product_search_from_history`（消耗 1）
搜索历史热卖产品，默认按月销量倒序。
- `amzSite` String 必填
- `searchTime` String 必填（yyyy-MM）
- `searchName` String 可选
- 价格/月销/星级/评论数/发货方式 可选筛选
- `page` Integer 可选
- 返回：历史产品列表

### 13. 亚马逊总结产品评论 `product_customers_say`（消耗 1）
查询亚马逊「Customers Say」AI 评论总结与关键词情感分析。
- `site` String 必填（注意字段名为 site，非 amzSite）
- `asin` String 必填（单 ASIN）
- 返回：AI评论总结 + 关键词（提及次数/积极/消极/更新时间）

## A.3 与项目模块的映射

| 项目模块 | 主要使用接口 |
|---------|-------------|
| 选品算法引擎（FR-01） | `product_search` / `potential_product` / `similar_product_feature` |
| 产品详情与评分 | `product_detail` / `product_variations` |
| 趋势与历史 | `product_trend` / `product_search_from_history` |
| 评论与痛点（AI 日报输入） | `product_reviews` / `product_customers_say` |
| 流量与关键词（Listing 优化） | `product_traffic_terms` / `competitor_product_keywords` / `product_ranking_trend_by_keyword` |
| 每日数据拉取（Celery 08:00） | `product_search`（按品类）为主，其余按需懒加载 |

## A.4 实现注意事项

- 返回为「面向 AI 的非严格 JSON 字符串」，适配层解析时需用容错解析器（先尝试 `json.loads`，失败则正则提取键值对）。
- 高消耗接口（`similar_product_feature`、`product_reviews` 各消耗 5）必须强缓存，优先复用。
- `product_customers_say` 的站点字段名为 `site`，与其余接口的 `amzSite` 不同，适配层需统一映射。
- 所有调用走 `adapters/sorftime.py`，统一重试（tenacity 指数退避）/超时/降级（失败用昨日快照）。