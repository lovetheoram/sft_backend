# Finance/ai/nodes.py

from typing import List, TypedDict

from langchain_core.messages import SystemMessage, HumanMessage

from .llm import get_llm
from .tools import (
    get_financial_summary_tool,
    get_total_expense_tool
)
from .prompts import FINANCE_AGENT_SYSTEM_PROMPT

from .memory import (
    load_messages,
    save_messages,
    build_system_prompt,
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
    messages: List

    retrieved_memory: List[str]
    intent: str
    tool_result: str
    final_response: str


# ----------------------------
# 🔹 1. LOAD MEMORY
# ----------------------------
def load_memory_node(state: AgentState):
    base_messages = load_messages(
        state["user_id"],
        state["session_id"],
        FINANCE_AGENT_SYSTEM_PROMPT
    )

    state["messages"] = base_messages[-2:]
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
        print("Vector retrieval error:", e)
        memories = []

    state["retrieved_memory"] = memories
    return state


# ----------------------------
# 🔹 3. BUILD PROMPT
# ----------------------------
def build_prompt_node(state: AgentState):
    system_prompt = build_system_prompt(
        state["user_id"],
        state["session_id"],
        FINANCE_AGENT_SYSTEM_PROMPT
    )

    messages = [SystemMessage(content=system_prompt)]

    if state["retrieved_memory"]:
        messages.append(
            SystemMessage(
                content="Relevant past context:\n" +
                "\n".join(state["retrieved_memory"])
            )
        )

    messages += state["messages"]
    messages.append(HumanMessage(content=state["user_query"]))

    state["messages"] = messages
    return state


# ----------------------------
# 🔹 4. INTENT DETECTION
# ----------------------------
def intent_node(state):
    llm = get_llm()

    if llm is None:
        state["intent"] = "general"
        return state

    try:
        response = llm.invoke(
            f"Classify intent: {state['user_query']}"
        )
        state["intent"] = str(response.content).lower()
    except Exception as e:
        print("Intent error:", e)
        state["intent"] = "general"

    return state
# ----------------------------
# 🔹 5. TOOL NODE
# ----------------------------
def tool_node(state: AgentState):
    intent = state["intent"]

    result = None

    try:
        if "expense" in intent:
            result = get_total_expense_tool.invoke({
                "year": 2024,
                "building_id": state["building_id"]
            })

        elif "summary" in intent:
            result = get_financial_summary_tool.invoke({
                "year": 2024,
                "building_id": state["building_id"]
            })

    except Exception as e:
        print("Tool error:", e)

    state["tool_result"] = result
    return state


# ----------------------------
# 🔹 6. LLM RESPONSE
# ----------------------------
def llm_node(state):
    llm = get_llm()

    if llm is None:
        state["final_response"] = "LLM not available"
        return state

    try:
        response = llm.invoke(state["messages"]).content
        state["final_response"] = str(response)
    except Exception as e:
        print("LLM error:", e)
        state["final_response"] = "Something went wrong."

    return state
# ----------------------------
# 🔹 7. SAVE MEMORY
# ----------------------------
def should_store(text: str):
    text = text.lower()

    if len(text.split()) > 6:
        return True

    keywords = [
        "expense", "summary", "payment",
        "plan", "idea", "strategy",
        "problem", "solution", "decision"
    ]

    return any(k in text for k in keywords)


def save_memory_node(state: AgentState):
    user_id = state["user_id"]
    session_id = state["session_id"]

    user_query = state["user_query"]
    response = state["final_response"]

    try:
        # short-term memory
        save_messages(
            user_id,
            session_id,
            [
                HumanMessage(content=user_query),
                SystemMessage(content=response)
            ]
        )

        # vector memory
        add_memory(user_id, f"User: {user_query}")

        if should_store(response):
            add_memory(user_id, f"Assistant: {response}")

    except Exception as e:
        print("Memory error:", e)

    return state