EXPLANATION_PROMPT = """
You are an assistant for a housing society admin.

Explain the following expense in SIMPLE, NON-TECHNICAL terms.
Do NOT make decisions.
Do NOT suggest approvals.

Expense:
{expense}

Past Data:
{history}

Financial Context:
{finance}
"""

PLANNING_PROMPT = """
You are helping a building plan an expense.

Based on:
- Past expense history
- Current financial capacity
- Market pricing

Generate:
1. Estimated cost range
2. Whether it fits budget
3. Risks
4. Practical suggestions
"""

COMMUNICATION_PROMPT = """
Draft a short, polite message for society members.

Purpose: {purpose}
Amount: {amount}
Due Date: {due_date}

Tone: respectful, neutral, non-threatening
"""
