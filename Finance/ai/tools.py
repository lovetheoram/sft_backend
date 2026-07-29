from langchain.tools import tool
from ..services import get_financial_summary

from django.db.models import Sum
from ..models import Expense
from ..models import Building
# @tool
# def get_financial_summary_tool(year: int, building_id: int):
#     """
#     Get financial summary for a building for a financial year.
#     """
#     from ..models import Building
#     building = Building.objects.get(id=building_id)
#     data = get_financial_summary(year, building)
#     return data


# @tool
# def get_total_expense_tool(year: int, building_id: int) -> int:
#     """
#     Get total expense for a financial year for a specific building.

#     Args:
#         year (int): Financial year start (e.g., 2024 means Apr 2024–Mar 2025)
#         building_id (int): ID of the building

#     Returns:
#         int: Total expense amount
#     """
#     from ..models import Building
#     from datetime import date

#     building = Building.objects.get(id=building_id)
#     start_date = date(year, 4, 1)
#     end_date = date(year + 1, 3, 31)

#     total = Expense.objects.filter(
#         building=building,
#         date__range=(start_date, end_date)
#     ).aggregate(total=Sum("amount"))["total"] or 0

#     return total

from langchain.tools import tool
from django.shortcuts import get_object_or_404

from Finance.models import (
    Building,
    Income,
    Expense,
    Member,
    SpecialCharge
)

from Finance.services import (
    get_financial_summary,
    get_member_income_table,
    get_expense_summary,
    get_opening_balance,
)

from django.db.models import Sum
from collections import defaultdict
from datetime import date

@tool
def get_financial_summary_tool(year: int, building_id: int):
    """
    Complete financial summary for a financial year.
    """

    building = get_object_or_404(
        Building,
        id=building_id
    )

    data = get_financial_summary(
        year,
        building
    )

    return data


@tool
def get_total_expense_tool(year: int, building_id: int):
    """
    Get total expense for a year.
    """

    building = get_object_or_404(
        Building,
        id=building_id
    )

    data = get_expense_summary(
        year,
        building
    )

    return {
        "year": year,
        "total_expense": data["total_expense"]
    }


@tool
def get_total_income_tool(year: int, building_id: int):
    """
    Get total income collected.
    """

    building = get_object_or_404(
        Building,
        id=building_id
    )

    data = get_member_income_table(
        year,
        building
    )

    return {
        "year": year,
        "total_income": data["total_row"]["total"]
    }


@tool
def get_opening_balance_tool(year: int, building_id: int):
    """
    Get opening balance.
    """

    building = get_object_or_404(
        Building,
        id=building_id
    )

    return {
        "year": year,
        "opening_balance": get_opening_balance(
            year,
            building
        )
    }


@tool
def get_closing_balance_tool(year: int, building_id: int):
    """
    Get closing balance.
    """

    building = get_object_or_404(
        Building,
        id=building_id
    )

    summary = get_financial_summary(
        year,
        building
    )

    return {
        "year": year,
        "closing_balance": summary["closing_balance"]
    }


@tool
def get_expense_category_tool(year: int, building_id: int):
    """
    Expense breakdown by category.
    """

    building = get_object_or_404(
        Building,
        id=building_id
    )

    data = get_expense_summary(
        year,
        building
    )

    return data["categories"]


@tool
def get_monthly_expense_tool(year: int, building_id: int):
    """
    Monthly expense trend.
    """

    building = get_object_or_404(
        Building,
        id=building_id
    )

    data = get_expense_summary(
        year,
        building
    )

    return data["total_monthly_expense"]



@tool
def get_top_contributors_tool(year: int, building_id: int):
    """
    Members ranked by contribution.
    """

    building = get_object_or_404(
        Building,
        id=building_id
    )

    data = get_member_income_table(
        year,
        building
    )

    members = sorted(
        data["members"],
        key=lambda x: x["total"],
        reverse=True
    )

    return members[:10]


@tool
def get_special_charge_tool(
    year: int,
    building_id: int
):
    """
    Summary of special charges.
    """

    building = get_object_or_404(
        Building,
        id=building_id
    )

    data = get_member_income_table(
        year,
        building
    )

    return data["total_row"]["special_income"]


TOOLS = {
    "summary": get_financial_summary_tool,
    "expense": get_total_expense_tool,
    "income": get_total_income_tool,
    "opening_balance": get_opening_balance_tool,
    "closing_balance": get_closing_balance_tool,
    "expense_category": get_expense_category_tool,
    "monthly_expense": get_monthly_expense_tool,
    "top_contributors": get_top_contributors_tool,
    "special_charge": get_special_charge_tool,
}