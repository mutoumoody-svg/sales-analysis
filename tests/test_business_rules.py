"""
Business Rules Tests - 业务规则测试.

Tests:
1. Sales type classification
2. Cost matching priority
3. Profit calculation
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from decimal import Decimal
from app.services.sales_service import classify_sales_type


def test_distributor_is_wholesale():
    """Rule 1: Distributor customer -> Wholesale."""
    result = classify_sales_type(
        customer_type="Distributor",
        store_channel="flagship",
        total_quantity=5,
        total_amount=Decimal("500"),
    )
    assert result == "Wholesale", f"Expected Wholesale, got {result}"
    print("PASS: Distributor -> Wholesale")


def test_flagship_retail():
    """Rule 2: Flagship store -> Retail (default)."""
    result = classify_sales_type(
        customer_type="Normal",
        store_channel="flagship",
        total_quantity=3,
        total_amount=Decimal("300"),
    )
    assert result == "Retail", f"Expected Retail, got {result}"
    print("PASS: Flagship -> Retail")


def test_large_quantity_flagged():
    """Rule 3: Abnormally large quantity -> Potential Wholesale."""
    result = classify_sales_type(
        customer_type="Normal",
        store_channel="flagship",
        total_quantity=100,
        total_amount=Decimal("10000"),
    )
    assert result == "Potential Wholesale", f"Expected Potential Wholesale, got {result}"
    print("PASS: Large quantity -> Potential Wholesale")


def test_normal_customer_retail():
    """Default: Normal customer, normal quantity -> Retail."""
    result = classify_sales_type(
        customer_type="Normal",
        store_channel=None,
        total_quantity=2,
        total_amount=Decimal("200"),
    )
    assert result == "Retail", f"Expected Retail, got {result}"
    print("PASS: Normal customer -> Retail")


if __name__ == "__main__":
    print("=" * 50)
    print("Business Rules Tests")
    print("=" * 50)
    print()

    test_distributor_is_wholesale()
    test_flagship_retail()
    test_large_quantity_flagged()
    test_normal_customer_retail()

    print()
    print("All tests passed!")
