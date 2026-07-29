from langgraph.graph import StateGraph
from .node import load_context_node,retrieve_memory_node,build_prompt_node,intent_node,tool_node,llm_node,AgentState,persist_memory_node,memory_node
# ----------------------------
# 🧠 BUILD GRAPH
# ----------------------------
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("load_context", load_context_node)
builder.add_node("retrieve_memory", retrieve_memory_node)
builder.add_node("build_prompt", build_prompt_node)
builder.add_node("intent", intent_node)
builder.add_node("tool", tool_node)
builder.add_node("llm", llm_node)
builder.add_node("persist_memory", persist_memory_node)

builder.add_node("save_memory", memory_node)

# ----------------------------
# 🔀 DEFINE FLOW
# ----------------------------
builder.set_entry_point("load_context")

builder.add_edge("load_context", "retrieve_memory")
builder.add_edge("retrieve_memory", "intent")
builder.add_edge( "intent","build_prompt")
builder.add_edge("build_prompt", "tool")
builder.add_edge("tool", "llm")
builder.add_edge("llm","persist_memory")
builder.add_edge("persist_memory", "save_memory")

# Compile graph
graph = builder.compile()

print(graph)
# ----------------------------
# ▶️ EXECUTION FUNCTION
# ----------------------------
def run_finance_agent(user_id, session_id, user_query, building):
    result = graph.invoke({
        "user_id": user_id,
        "session_id": session_id,
        "building_id": building.id,
        "user_query": user_query
    })

    return result["final_response"]