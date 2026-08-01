"""
=============================================================================
💵 INCOME & OPENING BALANCE SERVICES
=============================================================================
"""

from collections import defaultdict
from datetime import date
from calendar import month_abbr
from django.db import models

from Finance.models import Income, Expense


def get_fy_months(start_year):
    """Returns formatted FY month labels (e.g. Apr-23 ... Mar-24)."""
    months = []
    for m in range(4, 13):
        months.append(f"{month_abbr[m]}-{str(start_year)[-2:]}")
    for m in range(1, 4):
        months.append(f"{month_abbr[m]}-{str(start_year + 1)[-2:]}")
    return months


def get_member_income_table(start_year, building):
    """Generates monthly income breakdown per member for a given FY and building."""
    months = get_fy_months(start_year)
    start_date = date(start_year, 4, 1)
    end_date = date(start_year + 1, 3, 31)

    incomes = Income.objects.filter(
        building=building,
        date__range=(start_date, end_date),
        status='verified',
    ).select_related("member__user", "member__user__flat", "special_charge")

    member_rows = {}
    total_row = {m: 0 for m in months}
    total_special = defaultdict(int)
    grand_total = 0

    for income in incomes:
        member = income.member
        name = member.user.get_full_name()
        flat = member.user.flat.number if member.user.flat else ""
        month_label = f"{income.date.strftime('%b')}-{str(income.date.year)[-2:]}"
        member_id = member.id

        if member_id not in member_rows:
            member_rows[member_id] = {
                "name": name,
                "flat": flat,
                "monthly": {m: 0 for m in months},
                "special_income": defaultdict(int),
                "total": 0
            }

        if income.special_charge:
            title = income.special_charge.title
            member_rows[member_id]["special_income"][title] += income.amount
            total_special[title] += income.amount
        else:
            member_rows[member_id]["monthly"][month_label] += income.amount
            total_row[month_label] += income.amount

        member_rows[member_id]["total"] += income.amount
        grand_total += income.amount

    for row in member_rows.values():
        row["special_income"] = dict(row["special_income"])

    return {
        "members": list(member_rows.values()),
        "total_row": {
            "monthly": total_row,
            "special_income": dict(total_special),
            "total": grand_total
        },
        "months": months
    }


def get_opening_balance(start_year, building):
    """Calculates cumulative net balance prior to the start of the given FY."""
    income_total = Income.objects.filter(
        building=building,
        date__lt=date(start_year, 4, 1),
        status='verified',
        special_charge__isnull=True
    ).aggregate(total=models.Sum("amount"))["total"] or 0

    expense_total = Expense.objects.filter(
        building=building,
        date__lt=date(start_year, 4, 1)
    ).aggregate(total=models.Sum("amount"))["total"] or 0

    return income_total - expense_total
