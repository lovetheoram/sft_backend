from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from .llm import get_llm
from .tools import (
    get_financial_summary_tool,
    get_total_expense_tool
)
from .prompts import FINANCE_AGENT_SYSTEM_PROMPT


tools = [
    get_financial_summary_tool,
    get_total_expense_tool
]

from langchain.tools import tool


def get_tools_with_context(building_id):
    
    @tool
    def get_total_expense_tool_ctx(year: int) -> int:
        """
    Get financial summary for a building for a financial year.
    """
        return get_total_expense_tool.invoke({
            "year": year,
            "building_id": building_id
        })

    @tool
    def get_financial_summary_tool_ctx(year: int):
        """
    Get total expense for a financial year for a specific building.

    Args:
        year (int): Financial year start (e.g., 2024 means Apr 2024–Mar 2025)
        

    Returns:
        int: Total expense amount
    """
        return get_financial_summary_tool.invoke({
            "year": year,
            "building_id": building_id
        })

    return [
        get_total_expense_tool_ctx,
        get_financial_summary_tool_ctx
    ]

def extract_text_from_response(content):
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
        return "\n".join(texts)
    
    return str(content)




from .memory import (
    load_messages,
    save_messages,
    build_system_prompt,
    update_summary,
    update_long_term_memory,
    detect_important_info,
    save_meta,
    load_meta
)

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage


def run_finance_agent(user_id, session_id, user_query, building):
    llm = get_llm()

    # Inject building context into tools
    tools = get_tools_with_context(building.id)
    llm_with_tools = llm.bind_tools(tools)

    # Load chat history (NO system inside)
    base_messages = load_messages(user_id, session_id, FINANCE_AGENT_SYSTEM_PROMPT)

    # Build dynamic system prompt (summary + long-term memory)
    system_prompt = build_system_prompt(
        user_id,
        session_id,
        FINANCE_AGENT_SYSTEM_PROMPT
    )

    messages = [SystemMessage(content=system_prompt)] + base_messages
    print("MESSAGE:  ",)
    # Add new user message
    messages.append(HumanMessage(content=user_query))

    print(messages)

    while True:
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        # 🔧 Tool handling
        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                tool_dict = {t.name: t for t in tools}
                tool_func = tool_dict[tool_name]

                result = tool_func.invoke(tool_args)

                messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call["id"]
                    )
                )

        else:
            # ✅ CLEAN MESSAGES BEFORE SAVING

            cleaned_messages = base_messages + [
                HumanMessage(content=user_query),
                response
            ][-10:]
            # 💾 Save chat history
            # 💾 Save chat history
            save_messages(user_id, session_id, cleaned_messages)

            message_count = len(cleaned_messages)
            meta = load_meta(user_id, session_id)

            # 🔹 Summary trigger (delta-based)
            if message_count - meta.get("last_summary_update", 0) >= 5:
                try:
                    update_summary(llm, user_id, session_id, cleaned_messages[-6:])
                    meta["last_summary_update"] = message_count
                except Exception as e:
                    print("Summary update failed:", e)

            # 🔹 Long-term memory trigger (delta-based)
            if message_count - meta.get("last_memory_update", 0) >= 7:
                try:
                    update_long_term_memory(llm, user_id, cleaned_messages[-10:])
                    meta["last_memory_update"] = message_count
                except Exception as e:
                    print("Long-term memory update failed:", e)

            # 🔹 Event-based trigger (IMPORTANT)
            if detect_important_info(user_query):
                try:
                    update_long_term_memory(llm, user_id, cleaned_messages[-10:])
                    meta["last_memory_update"] = message_count  # keep in sync
                except Exception as e:
                    print("Event memory update failed:", e)

            save_meta(user_id, session_id, meta)

            # ✅ Return final response
            return extract_text_from_response(response.content)