# Finance/ai/tool_executor.py

from . import mcp_tools

def execute_tool(tool_name, args, state):
    user = state["user"]
    building = getattr(user.flat, "building", None)

    if tool_name == "get_building_context":
        return mcp_tools.get_building_context(user)

    if tool_name == "get_financial_summary":
        return mcp_tools.get_financial_summary(
            user=user,
            year=args["year"]
        )

    if tool_name == "get_category_expense_history":
        return mcp_tools.get_category_expense_history(
            building=building,
            category_name=args["category_name"],
            year=args["year"]
        )

    if tool_name == "get_members_with_pending_payments":
        return mcp_tools.get_members_with_pending_payments(building)

    raise ValueError(f"Unknown tool: {tool_name}")
