"""prompt_builder + response 异常处理测试。"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from app.services.prompt_builder import build_daily_report_prompt, SYSTEM_PROMPT
from app.core.response import ApiResponse, ErrorCode, BizError, now_iso
from app.core.database import SessionLocal
from app.models.product import Product
from sqlalchemy import delete
from datetime import date

TODAY = date.today()


def test_prompt_no_data():
    """无数据时 prompt 应返回简短消息。"""
    db = SessionLocal()
    # 用一个肯定没数据的日期
    messages = build_daily_report_prompt(db, date(2099, 1, 1))
    db.close()
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == SYSTEM_PROMPT
    assert "暂无选品数据" in messages[1]["content"]


def test_prompt_with_data():
    """有数据时 prompt 应包含产品摘要。"""
    db = SessionLocal()
    db.add(Product(
        sorftime_id="PROMPT_TEST_001", title="Prompt测试产品", category="test",
        monthly_sales=5000, price=19.99, comprehensive_score=70.0, risk_tags=["测试风险"],
        match_status="pending", data_date=TODAY,
    ))
    db.commit()

    messages = build_daily_report_prompt(db, TODAY)
    user_msg = messages[1]["content"]

    # 清理
    db.execute(delete(Product).where(Product.sorftime_id == "PROMPT_TEST_001"))
    db.commit()
    db.close()

    assert "Prompt测试产品" in user_msg
    assert "5000" in user_msg  # 销量


def test_prompt_includes_risk_summary():
    """有风险标签时 prompt 应包含风险预警汇总。"""
    db = SessionLocal()
    db.add(Product(
        sorftime_id="PROMPT_TEST_002", title="风险测试产品", category="ink",
        monthly_sales=3000, price=29.99, comprehensive_score=60.0, risk_tags=["易燃液体", "易损易潮"],
        match_status="pending", data_date=TODAY,
    ))
    db.commit()

    messages = build_daily_report_prompt(db, TODAY)
    db.execute(delete(Product).where(Product.sorftime_id == "PROMPT_TEST_002"))
    db.commit()
    db.close()

    assert "风险预警" in messages[1]["content"]


def test_api_response_ok():
    r = ApiResponse.ok(data={"x": 1})
    assert r.code == 0
    assert r.data == {"x": 1}
    assert r.timestamp


def test_api_response_fail():
    r = ApiResponse.fail(code=ErrorCode.NOT_FOUND, message="不存在")
    assert r.code == 1002
    assert r.message == "不存在"


def test_now_iso_format():
    ts = now_iso()
    assert "T" in ts and ts.endswith("Z")
    assert len(ts) == 20


def test_biz_error_attributes():
    e = BizError(code=ErrorCode.PARAM_INVALID, message="参数错", data={"k": "v"})
    assert e.code == 1001
    assert e.message == "参数错"
    assert e.data == {"k": "v"}


def test_error_codes_distinct():
    """关键错误码不应重复。"""
    codes = [ErrorCode.SUCCESS, ErrorCode.PARAM_INVALID, ErrorCode.NOT_FOUND,
             ErrorCode.API_TIMEOUT, ErrorCode.API_FAILED, ErrorCode.DB_ERROR,
             ErrorCode.NO_PERMISSION, ErrorCode.INTERNAL]
    assert len(codes) == len(set(codes))