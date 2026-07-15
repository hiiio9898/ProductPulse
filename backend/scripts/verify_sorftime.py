import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os
from dotenv import load_dotenv
load_dotenv(".env")
from app.adapters.sorftime import sorftime_adapter

print("=== 1. Amazon ProductRequest ===")
d = sorftime_adapter.product_detail("US", "B0CVM8TXHP", trend=2)
print("ASIN:", d.asin)
print("Title:", d.title)
print("Price:", d.price, "| Rating:", d.rating, "| Sales:", d.monthly_sales, "| Brand:", d.brand)
print("Profit:", d.gross_profit, "| Margin:", d.gross_margin)
print()

print("=== 2. 1688 ProductSearchFromName ===")
items = sorftime_adapter.ali1688_search("3D printer filament PLA")
print("Total:", len(items))
for it in items[:3]:
    title = (it.get("Title") or "?")[:40]
    price = it.get("Price")
    sales = it.get("SalesOf30d")
    print("  -", title, "| Price:", price, "| 30d:", sales)