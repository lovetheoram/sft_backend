# User Text (query)
#    ↓
# views.py
#    - Creates initial state: {"query": "...", "user": request.user}
#    ↓
# graph.py
#    - Entry point = "select_tool"
#    ↓
# nodes.py -> select_tool
#    - Uses llm.py + tool_registry.py
#    - LLM decides: which tool + arguments OR MISSING
#    ↓
# nodes.py -> run_tool
#    - Calls tool_executor.py
#    - tool_executor.py executes function from mcp_tools.py
#    - Returns raw result
#    ↓
# nodes.py -> synthesize_response
#    - Optionally calls LLM to explain raw result
#    ↓
# graph.py
#    - Returns final state
#    ↓
# views.py
#    - Reads state["response"]
#    - Sends JSON response to frontend
