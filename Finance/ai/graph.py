# from langgraph.graph import StateGraph, END
# from langchain_core.messages import HumanMessage
# from langchain_google_genai import ChatGoogleGenerativeAI
# from django.conf import settings

# from . import mcp_tools
# from .prompts import EXPLANATION_PROMPT, COMMUNICATION_PROMPT
# from Finance.ai.rag import retrieve_context


# # -------- LLM --------
# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash",
#     temperature=0.3,
#     api_key=settings.GEMINI_API_KEY
# )


# # -------- STATE --------
# class ChatState(dict):
#     """
#     Expected keys:
#     - query
#     - user
#     - expense (optional)
#     - year
#     - purpose
#     - amount
#     - due_date
#     - response
#     """
#     pass


# # -------- ROUTER --------
# def route_intent(state: ChatState):
#     text = state.get("query", "").lower()

#     if "explain" in text:
#         return "explain_expense"
#     if "plan" in text or "budget" in text:
#         return "plan_expense"
#     if "message" in text or "reminder" in text:
#         return "draft_message"

#     return "fallback"  # any unknown queries go here


# # -------- NODES --------
# def explain_expense(state: ChatState):
#     if "expense" not in state:
#         state["response"] = "❌ No expense provided. Please provide an expense to explain."
#         return state

#     user = state["user"]
#     expense = state["expense"]
#     year = state.get("year", 2024)

#     history = mcp_tools.get_category_expense_history(
#         expense.building,
#         expense.category.name,
#         year,
#     )

#     finance = mcp_tools.get_financial_summary(user, year)

#     prompt = EXPLANATION_PROMPT.format(
#         expense=str(expense),
#         history=str(history),
#         finance=str(finance),
#     )

#     result = llm.invoke([HumanMessage(content=prompt)])
#     state["response"] = result.content
#     return state


# def plan_expense(state: ChatState):
#     query = state.get("query", "")

#     rag_context = retrieve_context(query)

#     prompt = f"""
# You are planning a finance expense.

# VERIFIED CONTEXT:
# {rag_context}

# QUESTION:
# {query}

# Give:
# - Estimated cost range
# - Feasibility
# - Risks
# """

#     result = llm.invoke([HumanMessage(content=prompt)])
#     state["response"] = result.content
#     return state


# def draft_message(state: ChatState):
#     purpose = state.get("purpose")
#     amount = state.get("amount")
#     due_date = state.get("due_date")

#     if not purpose:
#         state["response"] = "❌ No purpose provided for drafting message."
#         return state

#     prompt = COMMUNICATION_PROMPT.format(
#         purpose=purpose,
#         amount=amount,
#         due_date=due_date,
#     )

#     result = llm.invoke([HumanMessage(content=prompt)])
#     state["response"] = result.content
#     return state


# def fallback(state: ChatState):
#     state["response"] = "🤖 I didn't understand that. Can you rephrase?"
#     return state


# # -------- GRAPH --------
# def build_graph():
#     graph = StateGraph(ChatState)

#     # nodes
#     graph.add_node("route", route_intent)
#     graph.add_node("explain_expense", explain_expense)
#     graph.add_node("plan_expense", plan_expense)
#     graph.add_node("draft_message", draft_message)
#     graph.add_node("fallback", fallback)

#     # entry
#     graph.set_entry_point("route")

#     # routing
#     graph.add_conditional_edges(
#         "route",
#         route_intent,
#         {
#             "explain_expense": "explain_expense",
#             "plan_expense": "plan_expense",
#             "draft_message": "draft_message",
#             "fallback": "fallback",
#             "end": END,
#         },
#     )

#     # terminal edges
#     graph.add_edge("explain_expense", END)
#     graph.add_edge("plan_expense", END)
#     graph.add_edge("draft_message", END)
#     graph.add_edge("fallback", END)

#     return graph.compile()



# Finance/ai/graph.py

from langgraph.graph import StateGraph, END
from .nodes import select_tool, run_tool, synthesize_response


class ChatState(dict):
    pass


def build_graph():
    g = StateGraph(ChatState)

    g.add_node("select_tool", select_tool)
    g.add_node("run_tool", run_tool)
    g.add_node("respond", synthesize_response)

    g.set_entry_point("select_tool")

    g.add_edge("select_tool", "run_tool")
    g.add_edge("run_tool", "respond")
    g.add_edge("respond", END)

    return g.compile()
