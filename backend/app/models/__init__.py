"""SQLAlchemy 模型聚合导入。

8 张表对应数据库设计 4.1。导入此包即可让 Alembic / metadata 识别全部模型。
"""

from app.models.product import Product
from app.models.price_snapshot import PriceSnapshot
from app.models.product_metrics_daily import ProductMetricsDaily
from app.models.daily_report import DailyReport
from app.models.recommendation import Recommendation
from app.models.risk_rule import RiskRule
from app.models.system_config import SystemConfig
from app.models.operation_log import OperationLog

__all__ = [
    "Product",
    "PriceSnapshot",
    "ProductMetricsDaily",
    "DailyReport",
    "Recommendation",
    "RiskRule",
    "SystemConfig",
    "OperationLog",
]