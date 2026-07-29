

from typing import List, TypedDict, Dict, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from .llm import get_llm
# from .tools import get_financial_summary_tool, get_total_expense_tool


from .tools import TOOLS
from .memory import (
    load_messages,
    append_message,
    load_summary,
    update_summary,
    load_user_profile,
    update_user_profile,
    is_profile_query,
)
from .memory_vector import (
    add_memory,
    get_relevant_memory
)

# ----------------------------
# 🧠 STATE
# ----------------------------
class AgentState(TypedDict):
    user_id: int
    session_id: str
    building_id: int

    user_query: str
    retrieved_memory: List[str]

    messages: List
    summary: str
    profile: Dict

    intent: Dict
    tool_result: Optional[str]

    final_response: str


# ----------------------------
# 🔹 LOAD CONTEXT
# ----------------------------
def load_context_node(state: AgentState):
    state["messages"] = load_messages(
        state["user_id"],
        state["session_id"]
    )

    state["summary"] = load_summary(
        state["user_id"],
        state["session_id"]
    )

    state["profile"] = load_user_profile(
        state["user_id"]
    )

    return state


# ----------------------------
# 🔹 2. VECTOR RETRIEVAL
# ----------------------------
def retrieve_memory_node(state: AgentState):
    try:
        memories = get_relevant_memory(
            state["user_id"],
            state["user_query"],
            k=3
        )
    except Exception as e:
        print("Vector error:", e)
        memories = []

    state["retrieved_memory"] = memories
    return state


# ----------------------------
# 🔹 BUILD PROMPT
# ----------------------------
def build_prompt_node(state: AgentState):
    messages = []

    messages.append(SystemMessage(
    content="""
You are a society financial assistant.

When tool results are available:

- Use ONLY the tool result.
- Never invent categories.
- Never invent amounts.
- Never invent members.
- If data is missing, explicitly say:
  "No data available."

If a tool returns an empty result,
say that the information was not found.
"""
))

    intent = state["intent"]["intent"]

    # PROFILE → only for personal queries
    if intent == "general" and state["profile"]:
        messages.append(SystemMessage(
            content=f"User Profile:\n{state['profile']}"
        ))

    # SUMMARY → only for long context queries
    if intent == "general" and state["summary"]:
        messages.append(SystemMessage(
            content=f"Summary:\n{state['summary']}"
        ))
    financial_intents = [
    "summary",
    "expense",
    "income",
    "opening_balance",
    "closing_balance",
    "expense_category",
    "monthly_expense",
    "top_contributors",
    "special_charge",
]

    if intent in financial_intents and state["retrieved_memory"]:
        messages.append(
            SystemMessage(
                content="Relevant Memory:\n" +
                "\n".join(state["retrieved_memory"][:2])
            )
        )

    

    messages.extend(state["messages"])
    messages.append(HumanMessage(content=state["user_query"]))

    state["messages"] = messages
    return state


# ----------------------------
# 🔹 INTENT
# ----------------------------
def intent_node(state: AgentState):
    llm = get_llm()

    prompt = f"""
You are a financial assistant.

Return ONLY JSON.

{{
 "intent":
    "summary" |
    "expense" |
    "income" |
    "opening_balance" |
    "closing_balance" |
    "expense_category" |
    "monthly_expense" |
    "top_contributors" |
    "special_charge" |
    "general",

 "year": number or null
}}



Query:
{state["user_query"]}
"""
    try:
        response = llm.invoke(prompt).content
        import json
        state["intent"] = json.loads(response)
    except:
        state["intent"] = {"intent": "general"}
    print("INTENT RESPONSE:", state["intent"])
    return state


# ----------------------------
# 🔹 TOOL
# ----------------------------
# def tool_node(state: AgentState):
#     intent = state["intent"]

#     try:
#         if intent["intent"] == "summary":
#             state["tool_result"] = get_financial_summary_tool.invoke({
#                 "year": intent.get("year"),
#                 "building_id": state["building_id"]
#             })

#         elif intent["intent"] == "expense":
#             state["tool_result"] = get_total_expense_tool.invoke({
#                 "year": intent.get("year"),
#                 "building_id": state["building_id"]
#             })

#         else:
#             state["tool_result"] = None

#     except Exception as e:
#         print("Tool error:", e)
#         state["tool_result"] = None

#     return state

from .tools import TOOLS

def tool_node(state: AgentState):

    intent = state["intent"]

    tool_name = intent.get("intent")

    if tool_name == "general":
        state["tool_result"] = None
        return state

    tool = TOOLS.get(tool_name)

    if not tool:
        state["tool_result"] = None
        return state

    try:
        state["tool_result"] = tool.invoke({
            "year": intent.get("year"),
            "building_id": state["building_id"]
        })

    except Exception as e:
        print("Tool error:", e)
        state["tool_result"] = None
    print("TOOL NAME:", intent["intent"])
    print("YEAR:", intent.get("year"))
    print("TOOL RESULT:", state["tool_result"])
    return state
# ----------------------------
# 🔹 LLM RESPONSE
# ----------------------------
def llm_node(state: AgentState):
    llm = get_llm()
    messages = state["messages"]

    if state["tool_result"]:
        messages.append(SystemMessage(
            content=f"Tool Result:\n{state['tool_result']}"
        ))
    print("=" * 50)

    for msg in messages:
        print(type(msg).__name__)
        print(msg.content)

    print("=" * 50)

    try:
        state["final_response"] = llm.invoke(messages).content
    except:
        state["final_response"] = "Error occurred."

    return state


# ----------------------------
# 🔹 7. SAVE MEMORY
# ----------------------------
def persist_memory_node(state: AgentState):
    try:
        

        if len(state["user_query"].split()) > 5:
            add_memory(state["user_id"], f"User: {state['user_query']}")

        # if len(state["final_response"].split()) > 8:
        if state["intent"] == "general" and state["retrieved_memory"]:
            add_memory(state["user_id"], f"Assistant: {state['final_response']}")

    except Exception as e:
        print("Memory error:", e)

    return state

# ----------------------------
# 🔹 MEMORY UPDATE
# ----------------------------
def memory_node(state: AgentState):
    user_id = state["user_id"]
    session_id = state["session_id"]

    query = state["user_query"]
    response = state["final_response"]

    llm = get_llm()

    # save chat
    append_message(user_id, session_id, "user", query)
    append_message(user_id, session_id, "assistant", response)

    # update summary (controlled)
    update_summary(llm, user_id, session_id, state["messages"])

    # update profile (only when needed)
    if is_profile_query(query):
        update_user_profile(llm, user_id, state["messages"])

    return state