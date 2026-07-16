"""Prompt 模板构建器。

把系统数据（产品统计、风险预警、推荐清单）组织成结构化 prompt，
供 AI 日报生成使用。对应 SRS FR-03：AI 市场分析日报。
"""

from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.risk_rule import RiskRule

SYSTEM_PROMPT = """你是一位资深的外贸跨境电商选品分析师，专注于耗材品类（3D打印耗材、墨水、相纸等）。
请根据提供的当日数据，生成一份专业的市场行情分析日报。

报告分为四个模块，用 Markdown 格式输出：
## 今日推荐
精选 3-5 个最值得关注的选品机会，说明推荐理由（销量、竞争度、利润空间）。

## 趋势解读
分析各品类的销量与竞争趋势，指出增长或衰退的品类。

## 风险提示
列出需要警惕的风险（高垄断、易燃品类、亚马逊自营挤压等）。

## 行动建议
给出 3-5 条可执行的选品/运营建议。

要求：语言简洁专业，数据驱动，避免空话。"""


def build_daily_report_prompt(db: Session, target_date: date) -> list[dict]:
    """构建 AI 日报的 messages（system + user）。

    从数据库聚合当日数据，拼成结构化的用户消息。
    """
    # 当日产品统计
    products = db.execute(
        select(Product).where(
            Product.data_date == target_date, Product.deleted_at.is_(None)
        ).order_by(Product.comprehensive_score.desc()).limit(20)
    ).scalars().all()

    if not products:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"今日（{target_date}）暂无选品数据，请生成一份简短的市场观察。"},
        ]

    # 按品类聚合
    category_stats: dict[str, list[Product]] = {}
    for p in products:
        cat = p.category or "未分类"
        category_stats.setdefault(cat, []).append(p)

    # 构建数据摘要
    lines = [f"以下是 {target_date} 的选品数据摘要（共 {len(products)} 个产品）：\n"]

    for cat, cat_products in category_stats.items():
        total_sales = sum((p.monthly_sales or 0) for p in cat_products)
        avg_score = sum((p.comprehensive_score or 0) for p in cat_products) / len(cat_products) if cat_products else 0
        lines.append(f"\n### 品类：{cat}（{len(cat_products)} 个产品，总月销 {total_sales}，平均评分 {avg_score:.1f}）")

        # TOP 3 产品明细
        for p in cat_products[:3]:
            risk = f"，风险标签：{p.risk_tags}" if p.risk_tags else ""
            lines.append(
                f"- {p.title[:60]}：月销 {p.monthly_sales or 'N/A'}，"
                f"价格 ${p.price or 'N/A'}，评分 {p.comprehensive_score or 'N/A'}，"
                f"评论 {p.review_count or 'N/A'}{risk}"
            )

    # 风险预警汇总
    risky = [p for p in products if p.risk_tags]
    if risky:
        lines.append(f"\n### 风险预警（{len(risky)} 个产品有风险标签）")
        all_tags: list[str] = []
        for p in risky:
            all_tags.extend(p.risk_tags or [])
        tag_counts = {t: all_tags.count(t) for t in set(all_tags)}
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- {tag}：{count} 个产品")

    user_content = "\n".join(lines)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]