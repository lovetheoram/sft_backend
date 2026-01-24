# from Finance.models import (
#     Expense, Income, Member, Building
# )
# from Finance.views import (
#     get_expense_summary,
#     get_member_income_table,
#     get_opening_balance_for_table
# )
# from Finance.views import FinancialSummaryReport
# from rest_framework.test import APIRequestFactory
# from django.contrib.auth.models import AnonymousUser
# from datetime import date


# # ----------------------------
# # TOOL 1: Building Context
# # ----------------------------
# def get_building_context(user):
#     building = getattr(user.flat, "building", None)
#     return {
#         "user_role": user.role,
#         "building_id": building.id if building else None,
#         "building_name": building.name if building else None
#     }


# # ----------------------------
# # TOOL 2: Financial Summary
# # ----------------------------
# def get_financial_summary(user, year):
#     factory = APIRequestFactory()
#     request = factory.get(f"/financialSummary/?year={year}")
#     request.user = user

#     response = FinancialSummaryReport.as_view()(request)
#     return response.data


# # ----------------------------
# # TOOL 3: Expense History
# # ----------------------------
# def get_category_expense_history(building, category_name, year):
#     summary = get_expense_summary(year, building)

#     for cat in summary["categories"]:
#         if cat["category"] == category_name:
#             return cat

#     return {
#         "category": category_name,
#         "monthly_expenses": {},
#         "total_spent": 0
#     }


# # ----------------------------
# # TOOL 4: Members by Condition
# # ----------------------------
# def get_members_with_pending_payments(building):
#     members = Member.objects.filter(
#         user__flat__building=building
#     )

#     pending = []
#     for m in members:
#         if Income.objects.filter(
#             member=m, status="pending"
#         ).exists():
#             pending.append({
#                 "member_id": m.id,
#                 "name": m.user.get_full_name(),
#                 "flat": m.user.flat.number
#             })
#     return pending





# Finance/ai/mcp_tools.py

from Finance.models import Expense, Income, Member, Building
from Finance.views import (
    get_expense_summary,
    get_member_income_table,
    get_opening_balance_for_table,
    FinancialSummaryReport
)
from rest_framework.test import APIRequestFactory
from datetime import date


def get_building_context(user):
    building = getattr(user.flat, "building", None)
    return {
        "user_role": user.role,
        "building_id": building.id if building else None,
        "building_name": building.name if building else None
    }


def get_financial_summary(user, year):
    factory = APIRequestFactory()
    request = factory.get(f"/financialSummary/?year={year}")
    request.user = user
    response = FinancialSummaryReport.as_view()(request)
    return response.data


def get_category_expense_history(building, category_name, year):
    summary = get_expense_summary(year, building)

    for cat in summary["categories"]:
        if cat["category"].lower() == category_name.lower():
            return cat

    return {
        "category": category_name,
        "monthly_expenses": {},
        "total_spent": 0
    }


def get_members_with_pending_payments(building):
    members = Member.objects.filter(
        user__flat__building=building
    )

    pending = []
    for m in members:
        if Income.objects.filter(member=m, status="pending").exists():
            pending.append({
                "member_id": m.id,
                "name": m.user.get_full_name(),
                "flat": m.user.flat.number
            })
    return pending
