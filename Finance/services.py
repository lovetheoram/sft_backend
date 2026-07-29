from collections import defaultdict
from datetime import date
from calendar import month_abbr
from django.db import models
from .models import Income, Expense


def get_fy_months(start_year):
    months = []
    for m in range(4, 13):
        months.append(f"{month_abbr[m]}-{str(start_year)[-2:]}")
    for m in range(1, 4):
        months.append(f"{month_abbr[m]}-{str(start_year + 1)[-2:]}")
    return months


def get_member_income_table(start_year, building):
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


def get_expense_summary(start_year, building):
    months = get_fy_months(start_year)
    start_date = date(start_year, 4, 1)
    end_date = date(start_year + 1, 3, 31)

    expenses = Expense.objects.filter(
        building=building,
        date__range=(start_date, end_date)
    )

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


def get_financial_summary(start_year, building):
    opening_balance = get_opening_balance(start_year, building)
    income_table = get_member_income_table(start_year, building)
    expense_summary = get_expense_summary(start_year, building)

    total_income = income_table["total_row"]["total"]
    total_expense = expense_summary["total_expense"]
    closing_balance = opening_balance + total_income - total_expense

    return {
        "opening_balance": opening_balance,
        "months": income_table["months"],
        "members": income_table["members"],
        "total_row": income_table["total_row"],
        "expenses": expense_summary,
        "closing_balance": closing_balance,
        "total_receipt": total_income
    }