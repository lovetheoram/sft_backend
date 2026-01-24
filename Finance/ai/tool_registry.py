# Finance/ai/tool_registry.py

TOOLS = [
    {
        "name": "get_building_context",
        "description": "Get basic building and role context for the logged-in user.",
        "args": {}
    },
    {
        "name": "get_financial_summary",
        "description": "Get yearly financial summary including income, expenses and balances.",
        "args": {
            "year": "int (required)"
        }
    },
    {
        "name": "get_category_expense_history",
        "description": (
            "Get category-wise monthly expense history for the user's building."
        ),
        "args": {
            "category_name": "string (required)",
            "year": "int (required)"
        }
    },
    {
        "name": "get_members_with_pending_payments",
        "description": "List members who have pending payments in the building.",
        "args": {}
    }
]
