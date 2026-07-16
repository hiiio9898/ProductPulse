"""API 集成测试。

用 TestClient 测试全部核心 API 路由：鉴权、CRUD、业务逻辑。
复用主数据库（已 migrate），测试数据用唯一前缀避免冲突。
"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.main import app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.product import Product
from app.models.daily_report import DailyReport
from app.models.price_snapshot import PriceSnapshot

client = TestClient(app)
TODAY = date.today()
TEST_PREFIX = "API_TEST_"

# 正确鉴权头
AUTH = {"Authorization": f"Bearer {settings.app_secret_key}"}
NO_AUTH = {}


def setup_module(module):
    """插入测试数据。"""
    db = SessionLocal()
    db.execute(delete(Product).where(Product.sorftime_id.like(f"{TEST_PREFIX}%")))
    db.execute(delete(DailyReport).where(DailyReport.report_date == TODAY))
    db.commit()

    db.add(Product(
        sorftime_id=f"{TEST_PREFIX}001", title="API测试产品A", category="3D printer filament",
        monthly_sales=60000, price=24.99, listing_monopoly=20.0, brand_monopoly=30.0,
        seller_monopoly=25.0, review_count=150, new_product_ratio=12.0,
        amazon_self_ratio=15.0, comprehensive_score=75.0, risk_tags=["易损易潮"],
        match_status="pending", data_date=TODAY,
    ))
    db.add(Product(
        sorftime_id=f"{TEST_PREFIX}002", title="API测试产品B", category="photo paper",
        monthly_sales=10000, price=12.99, comprehensive_score=50.0,
        match_status="confirmed", data_date=TODAY,
    ))
    db.commit()
    db.close()


def teardown_module(module):
    """清理测试数据。"""
    db = SessionLocal()
    db.execute(delete(Product).where(Product.sorftime_id.like(f"{TEST_PREFIX}%")))
    db.execute(delete(PriceSnapshot).where(PriceSnapshot.snapshot_date == TODAY))
    db.execute(delete(DailyReport).where(DailyReport.report_date == TODAY))
    db.commit()
    db.close()


# ---------- 鉴权 ----------

def test_health_no_auth_ok():
    """健康检查不需要鉴权。"""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["code"] == 0


def test_products_without_token_rejected():
    """无 token 访问受保护接口应被拒。"""
    r = client.get("/api/v1/products/", headers=NO_AUTH)
    body = r.json()
    assert body["code"] == 4001
    assert "鉴权" in body["message"]


def test_products_with_wrong_token_rejected():
    """错误 token 应被拒。"""
    r = client.get("/api/v1/products/", headers={"Authorization": "Bearer wrong_token"})
    assert r.json()["code"] == 4001


def test_products_with_correct_token_ok():
    """正确 token 应通过。"""
    r = client.get("/api/v1/products/", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["code"] == 0


# ---------- 选品 API ----------

def test_list_products_pagination():
    r = client.get("/api/v1/products/?page=1&page_size=1", headers=AUTH)
    data = r.json()["data"]
    assert len(data["items"]) <= 1
    assert data["page"] == 1


def test_list_products_filter_category():
    r = client.get("/api/v1/products/?category=3D printer filament", headers=AUTH)
    items = r.json()["data"]["items"]
    assert all(i["category"] == "3D printer filament" for i in items)


def test_list_products_filter_min_score():
    r = client.get("/api/v1/products/?min_score=60", headers=AUTH)
    items = r.json()["data"]["items"]
    assert all(i["comprehensive_score"] >= 60 for i in items)


def test_get_product_detail():
    db = SessionLocal()
    p = db.execute(
        __import__("sqlalchemy").select(Product).where(Product.sorftime_id == f"{TEST_PREFIX}001")
    ).scalar_one()
    db.close()

    r = client.get(f"/api/v1/products/{p.id}", headers=AUTH)
    assert r.json()["code"] == 0
    assert r.json()["data"]["title"] == "API测试产品A"


def test_get_product_not_found():
    r = client.get("/api/v1/products/999999", headers=AUTH)
    assert r.json()["code"] == 1002


def test_get_product_detail_invalid_id():
    """非数字 ID 应触发参数校验或 404。"""
    r = client.get("/api/v1/products/abc", headers=AUTH)
    assert r.status_code in (200, 422)


# ---------- Dashboard ----------

def test_dashboard_overview():
    r = client.get("/api/v1/dashboard/overview", headers=AUTH)
    data = r.json()["data"]
    assert "alerts_count" in data
    assert "pending_sku_count" in data
    assert "top_score" in data
    assert isinstance(data["alerts_count"], int)


def test_dashboard_trends():
    r = client.get("/api/v1/dashboard/trends", headers=AUTH)
    data = r.json()["data"]
    assert isinstance(data, list)


# ---------- Config ----------

def test_get_config():
    r = client.get("/api/v1/config", headers=AUTH)
    data = r.json()["data"]
    assert "algorithm.thresholds" in data


def test_get_risk_rules():
    r = client.get("/api/v1/config/risk-rules", headers=AUTH)
    items = r.json()["data"]["items"]
    assert len(items) >= 2  # 预置 2 条


def test_update_thresholds():
    r = client.put("/api/v1/config/thresholds", json={"monthly_sales_min": 6000}, headers=AUTH)
    assert r.json()["code"] == 0
    assert r.json()["data"]["monthly_sales_min"] == 6000
    # 恢复
    client.put("/api/v1/config/thresholds", json={"monthly_sales_min": 5000}, headers=AUTH)


def test_risk_rule_crud():
    """新增 -> 查询 -> 更新 -> 删除 风险规则。"""
    # 新增
    r = client.post("/api/v1/config/risk-rules", json={
        "rule_name": "API测试规则", "trigger_conditions": {"category": "test"},
        "risk_level": "info", "risk_tag": "测试标签", "alert_message": "测试",
    }, headers=AUTH)
    assert r.json()["code"] == 0
    rule_id = r.json()["data"]["id"]

    # 更新
    r = client.put(f"/api/v1/config/risk-rules/{rule_id}", json={"risk_level": "warning"}, headers=AUTH)
    assert r.json()["data"]["risk_level"] == "warning"

    # 删除
    r = client.delete(f"/api/v1/config/risk-rules/{rule_id}", headers=AUTH)
    assert r.json()["code"] == 0

    # 确认已删
    r = client.delete(f"/api/v1/config/risk-rules/{rule_id}", headers=AUTH)
    assert r.json()["code"] == 1002


def test_delete_risk_rule_not_found():
    r = client.delete("/api/v1/config/risk-rules/999999", headers=AUTH)
    assert r.json()["code"] == 1002


# ---------- Reports ----------

def test_get_today_report():
    r = client.get("/api/v1/reports/daily", headers=AUTH)
    assert r.json()["code"] == 0  # 可能无日报，data 为 null


def test_get_report_invalid_date():
    r = client.get("/api/v1/reports/daily/invalid-date", headers=AUTH)
    assert r.json()["code"] == 1001


def test_get_report_not_found_date():
    r = client.get("/api/v1/reports/daily/2020-01-01", headers=AUTH)
    assert r.json()["code"] == 1002


# ---------- Price ----------

def test_price_alerts():
    r = client.get("/api/v1/price/alerts", headers=AUTH)
    data = r.json()["data"]
    assert "items" in data
    assert isinstance(data["total"], int)


def test_price_check_not_found():
    r = client.get("/api/v1/price/check/999999", headers=AUTH)
    assert r.json()["code"] == 1002


def test_confirm_match():
    """测试确认关联（不调真实 1688）。"""
    db = SessionLocal()
    p = db.execute(
        __import__("sqlalchemy").select(Product).where(Product.sorftime_id == f"{TEST_PREFIX}002")
    ).scalar_one()
    db.close()

    r = client.put(f"/api/v1/price/confirm/{p.id}", json={
        "source_id": "TEST1688", "source_title": "测试货源", "match_status": "confirmed", "price_cny": 10.0,
    }, headers=AUTH)
    assert r.json()["code"] == 0
    assert r.json()["data"]["match_status"] == "confirmed"

    # 拒绝
    r = client.put(f"/api/v1/price/confirm/{p.id}", json={
        "source_id": "TEST1688", "source_title": "测试货源", "match_status": "rejected",
    }, headers=AUTH)
    assert r.json()["data"]["match_status"] == "rejected"