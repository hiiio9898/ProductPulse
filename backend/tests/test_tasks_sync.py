"""Celery 任务层与 product_sync 测试（mock 外部依赖）。"""

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import date

from app.tasks.generate_report import _split_sections, _log_operation
from app.tasks.sync_1688 import sync_1688_prices
from app.tasks.sync_sorftime import DEFAULT_CATEGORIES


def test_default_categories():
    assert len(DEFAULT_CATEGORIES) >= 3
    assert all(isinstance(c, str) for c in DEFAULT_CATEGORIES)


def test_split_sections_basic():
    md = "## A\na\n## B\nb\n## C\nc\n## D\nd"
    s = _split_sections(md)
    assert set(s.keys()) == {"A", "B", "C", "D"}


def test_split_sections_empty():
    assert _split_sections("") == {}


def test_split_sections_no_headers():
    assert _split_sections("plain text") == {}


def test_split_sections_partial():
    md = "## A\ncontent\n## B\nbcontent"
    s = _split_sections(md)
    assert "A" in s and "B" in s


def test_log_operation_success():
    db = MagicMock()
    _log_operation(db, date(2026, 7, 16), "success", None, 5000, "glm-4-flash")
    db.add.assert_called_once()
    entry = db.add.call_args[0][0]
    assert entry.operation_type == "ai_generate"
    assert entry.status == "success"
    assert entry.duration_ms == 5000


def test_log_operation_failed():
    db = MagicMock()
    _log_operation(db, date(2026, 7, 16), "failed", "timeout", 3000)
    entry = db.add.call_args[0][0]
    assert entry.status == "failed"
    assert entry.error_message == "timeout"


def test_sync_1688_task_registered():
    assert sync_1688_prices.name == "sync_1688_prices"


def test_upsert_product_creates_new():
    from app.services.product_sync import upsert_product
    from app.adapters.sorftime import ProductListItem

    item = MagicMock(spec=ProductListItem)
    item.asin = "NEW_001"
    item.title = "new product"
    item.monthly_sales = 5000
    item.price = 19.99
    item.ratings_count = 100

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(upsert_product(mock_db, item, date(2026, 7, 16), "test"))
    loop.close()

    mock_db.add.assert_called_once()
    assert result.title == "new product"


def test_upsert_product_updates_existing():
    from app.services.product_sync import upsert_product
    from app.adapters.sorftime import ProductListItem
    from app.models.product import Product

    existing = Product(sorftime_id="EXIST_001", title="old", data_date=date(2026, 7, 1))
    item = MagicMock(spec=ProductListItem)
    item.asin = "EXIST_001"
    item.title = "updated title"
    item.monthly_sales = 9999
    item.price = 25.0
    item.ratings_count = 200

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_db.execute = AsyncMock(return_value=mock_result)

    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(upsert_product(mock_db, item, date(2026, 7, 16), "cat"))
    loop.close()

    assert result.title == "updated title"
    assert result.monthly_sales == 9999


def test_record_daily_metrics_creates():
    from app.services.product_sync import record_daily_metrics
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    loop = asyncio.new_event_loop()
    loop.run_until_complete(record_daily_metrics(mock_db, 1, date(2026, 7, 16), 5000, 19.99, 100))
    loop.close()
    mock_db.add.assert_called_once()