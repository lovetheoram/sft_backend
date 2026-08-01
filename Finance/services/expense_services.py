"""
=============================================================================
💸 EXPENSE SUMMARY SERVICES
=============================================================================
"""

from collections import defaultdict
from datetime import date
from Finance.models import Expense
from .income_services import get_fy_months


def get_expense_summary(start_year, building):
    """Generates monthly expense summary by category for a given FY and building."""
    months = get_fy_months(start_year)
    start_date = date(start_year, 4, 1)
    end_date = date(start_year + 1, 3, 31)

    expenses = Expense.objects.filter(
        building=building,
        date__range=(start_date, end_date)
    ).select_related("category")

    category_map = defaultdict(lambda: {
        "category": "",
        "monthly_expenses": {m: 0 for m in months},
        "total_spent": 0
    })

    total_monthly = {m: 0 for m in months}
    total_expense = 0

    for exp in expenses:
        category = exp.category.name if exp.category else "Uncategorized"
        month_label = f"{exp.date.strftime('%b')}-{str(exp.date.year)[-2:]}"
        category_map[category]["category"] = category
        category_map[category]["monthly_expenses"][month_label] += exp.amount
        category_map[category]["total_spent"] += exp.amount

        total_monthly[month_label] += exp.amount
        total_expense += exp.amount

    return {
        "categories": list(category_map.values()),
        "total_monthly_expense": total_monthly,
        "total_expense": total_expense
    }
