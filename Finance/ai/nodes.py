# Finance/ai/nodes.py

import json
from langchain_core.messages import HumanMessage
from .tool_registry import TOOLS
from .llm import llm


# def select_tool(state):
#     query = state.get("query", "")
#     tools_text = "\n".join(
#         f"- {t['name']}: {t['description']} | args: {t['args']}"
#         for t in TOOLS
#     )

#     prompt = f"""
# You are a finance assistant.

# User query:
# '{query}"

# Available tools:
# {tools_text}

# Rules:
# 1. Choose the best tool.
# 2. Extract arguments from the query.
# 3. If required arguments are missing, ask for them.
# 4. Respond ONLY in JSON.

# Formats:

# Tool call:
# {{
#   "tool": "<tool_name>",
#   "args": {{ ... }}
# }}

# Missing info:
# {{
#   "tool": "MISSING",
#   "missing": ["field1", "field2"]
# }}

# No tool needed:
# {{
#   "tool": "NONE",
#   "answer": "<text>"
# }}
# """

#     response = llm.invoke([HumanMessage(content=prompt)])
#     state["decision"] = json.loads(response.content)
#     return state


# Finance/ai/nodes.py

import json
from langchain_core.messages import HumanMessage
from .tool_registry import TOOLS
from .llm import llm


def select_tool(state):
    query = state.get("query", "").strip()

    # ✅ HARD GUARD
    if not query:
        state["decision"] = {
            "tool": "NONE",
            "answer": "Please ask a question."
        }
        return state

    tools_text = "\n".join(
        f"- {t['name']}: {t['description']} | args: {t['args']}"
        for t in TOOLS
    )

    prompt = f"""
You are a finance assistant.

User query:
"{query}"

Available tools:
{tools_text}

Rules:
- Respond ONLY in valid JSON
- No markdown
- No explanation
- No backticks

Formats:

Tool call:
{{
  "tool": "<tool_name>",
  "args": {{ ... }}
}}

Missing info:
{{
  "tool": "MISSING",
  "missing": ["field"]
}}

No tool needed:
{{
  "tool": "NONE",
  "answer": "<text>"
}}
"""

    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()

    # 🔐 Strip markdown if model adds it
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        decision = json.loads(raw)
    except json.JSONDecodeError:
        # 🧯 FAILSAFE (VERY IMPORTANT)
        decision = {
            "tool": "NONE",
            "answer": raw or "I didn’t understand that."
        }

    state["decision"] = decision
    return state


# Finance/ai/nodes.py (continued)

# from .tool_executor import execute_tool

# def run_tool(state):
#     decision = state["decision"]

#     if decision["tool"] == "MISSING":
#         state["response"] = (
#             f"Please provide: {', '.join(decision['missing'])}"
#         )
#         return state

#     if decision["tool"] == "NONE":
#         state["response"] = decision["answer"]
#         return state

#     result = execute_tool(
#         tool_name=decision["tool"],
#         args=decision.get("args", {}),
#         state=state
#     )

#     state["tool_result"] = result
#     return state


# Finance/ai/nodes.py

from .tool_executor import execute_tool


def run_tool(state):
    decision = state.get("decision")

    # 🛑 SAFETY GUARD
    if not decision:
        state["response"] = "I couldn’t understand your request."
        return state

    tool = decision.get("tool")

    if tool == "MISSING":
        state["response"] = (
            f"Please provide: {', '.join(decision.get('missing', []))}"
        )
        return state

    if tool == "NONE":
        state["response"] = decision.get("answer", "")
        return state

    result = execute_tool(
        tool_name=tool,
        args=decision.get("args", {}),
        state=state
    )

    state["tool_result"] = result
    return state


# Finance/ai/nodes.py (continued)

def synthesize_response(state):
    data = state.get("tool_result")

    prompt = f"""
Explain the following data clearly to the user.

DATA:
{data}
"""

    response = llm.invoke([HumanMessage(content=prompt)])
    state["response"] = response.content
    return state
