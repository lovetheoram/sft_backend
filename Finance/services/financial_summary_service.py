"""
=============================================================================
📊 FINANCIAL SUMMARY AGGREGATOR SERVICE
=============================================================================
"""

from django.core.cache import cache
from .income_services import get_opening_balance, get_member_income_table
from .expense_services import get_expense_summary


def get_financial_summary(start_year, building):
    """
    Aggregates opening balance, member income, expense categories,
    and closing balance into a complete financial summary report.
    Caches result for 15 minutes.
    """
    building_id = getattr(building, 'id', building)
    cache_key = f"fin_summary_{building_id}_{start_year}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    opening_balance = get_opening_balance(start_year, building)
    income_table = get_member_income_table(start_year, building)
    expense_summary = get_expense_summary(start_year, building)

    total_income = income_table["total_row"]["total"]
    total_expense = expense_summary["total_expense"]
    closing_balance = opening_balance + total_income - total_expense

    result = {
        "opening_balance": opening_balance,
        "months": income_table["months"],
        "members": income_table["members"],
        "total_row": income_table["total_row"],
        "expenses": expense_summary,
        "closing_balance": closing_balance,
        "total_receipt": total_income
    }
    cache.set(cache_key, result, 900)
    return result

