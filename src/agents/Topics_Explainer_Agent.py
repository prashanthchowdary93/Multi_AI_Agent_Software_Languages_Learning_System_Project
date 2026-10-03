"""

Given a topic from the roadmap, this agent:
  1. Lists available study files (MCP: list_study_files)
  2. Searches for relevant content (MCP: search_notes)
  3. Reads the most relevant file(s) in full (MCP: read_study_file)
  4. Stores context in the state variable
  5. Produces a clear, grounded explanation

  The key property: explanations are grounded in YOUR notes,
  not just the LLM's training data. If your notes say something,
  the explanation reflects that. If something isn't in your notes,
  the agent works from general knowledge and says so.

"""
import os
import json
from langchain_core.messages import HumanMessage,SystemMessage,AIMessage,ToolMessage
from graph.Flow_State import AgentState,RoadMap
from langchain_core.tools import tool
from mcp_servers.filesystem_server import (list_study_files,
                                           search_notes,
                                           read_study_file,
                                           get_notes_index)
from graph.Flow_State import get_current_topic
from langchain_core.messages.tool import ToolCall
from langchain_openai import ChatOpenAI

@tool
def tool_list_files() -> list[str]:
    """
    List all available study note files in the notes directory.
    Returns filenames like ['closures.md', 'decorators.md'].
    Call this FIRST to discover what materials exist before reading any file.
    """
    return list_study_files()


@tool
def tool_read_file(filename: str) -> str:
    """
    Read the complete content of a study note file.
    Args:
        filename: Exact filename as returned by tool_list_files().
                  Example: 'closures.md' or 'python_basics.md'
    Returns the full file text, or an error string if not found.
    """
    return read_study_file(filename)


@tool
def tool_search_notes(query: str) -> str:
    """
    Search across all study notes for a keyword or phrase.
    Use this to find which file covers a specific concept before reading it.
    Args:
        query: Search term (case-insensitive). Example: 'nonlocal', 'closure','decorators'
    Returns a JSON string with matching lines and their file locations.
    """
    results = search_notes(query)
    if not results:
        return "No matches found."
    return json.dumps(results, indent=2)

# All tools in a list, passed to llm.bind_tools()
EXPLAINER_TOOLS = [
    tool_list_files,
    tool_read_file,
    tool_search_notes    
]

# Map tool names to functions for dispatch
TOOL_MAP = {t.name: t for t in EXPLAINER_TOOLS}

# ─────────────────────────────────────────────────────────────────────────────
# Tool execution
# ─────────────────────────────────────────────────────────────────────────────

def execute_tool_call(tool_call: ToolCall) -> str:
    """
    Execute a single tool call from the LLM and return the result as a string.

    Args:
        tool_call: Dict with keys 'name', 'args', 'id' from the LLM response.

    Returns:
        String result to be put into a ToolMessage.
        Never raises, errors are returned as strings so the LLM
        can see what went wrong and potentially recover.
    """
    name = tool_call["name"]
    args = tool_call["args"]

    if name not in TOOL_MAP:
        return f"Error: unknown tool '{name}'. Available: {list(TOOL_MAP.keys())}"

    try:
        print(f"[Topic_Explainer_Agent] -> Invoking the tool : {TOOL_MAP[name]}, args passed: {args}")
        result = TOOL_MAP[name].invoke(args)
        # Ensure result is always a string for ToolMessage
        if isinstance(result, (list, dict)):
            return json.dumps(result)
        return str(result)
    except Exception as e:
        return f"Error executing {name}({args}): {type(e).__name__}: {e}"

TOPIC_EXPLAINER_SYSTEM_PROMPT = """You are an expert tutor explaining topics to a student.

    Your explanations must be grounded in the student's actual study materials.
    Use the available tools to find and read relevant notes before explaining.

    APPROACH, follow this sequence:
    1. Call tool_list_files() to see what materials are available
    2. Call tool_search_notes(topic) to find which files cover this topic
    3. Call tool_read_file(filename) to read the most relevant file(s)
    4. Write your explanation based on what you found in the notes

    EXPLANATION FORMAT:
    - Start with a real-world analogy (1-2 sentences)
    - State the core concept clearly (1-2 sentences)
    - Show a concrete code example from the student's notes
    - End with one "common mistake" or "gotcha" to watch out for
    - Target length: 50-100 words

    If the notes don't cover the topic, explain from general knowledge
    and say "Your notes don't cover this specifically, but here's the concept from my parametric knowledge base:"
"""

def Topic_Explainer_Agent_Node(state: AgentState) -> dict:
    print("Inside Topic Explainer coach Agent")
    current_topic = get_current_topic(state)

    if current_topic is None:
        return {
            "error": "No current topic found. Study Planner Agent must run first.",
        }

    session_id = state.get("session_id", "unknown")

    #Create the LLM object and then bind it with tools
    llm_obj = ChatOpenAI(model='gpt-4o-mini')
    llm_obj_with_tools = llm_obj.bind_tools(EXPLAINER_TOOLS)

    #Write the messages to invoke LLM
    messages = [
        SystemMessage(content=TOPIC_EXPLAINER_SYSTEM_PROMPT),
        HumanMessage(content=(f"Please explain this topic to me: '{current_topic.topic_title}'\n"
            f"Context: {current_topic.topic_description}\n"
            f"Session ID for memory calls: {session_id}"
        )),
    ]

    # ── Tool-calling loop ─────────────────────────────────────────────
    # Safety limit: prevents infinite loops if the LLM keeps
    # requesting tools without producing a final answer.
    max_iterations = 8
    final_response = None
    for iteration in range(max_iterations):
        print(f"[Topic_Explainer_Agent] LLM call {iteration + 1}/{max_iterations}...")
        try:
            explainer_llm_response = llm_obj_with_tools.invoke(messages)
        except Exception as e:
            print(f"[Topic_Explainer_Agent] LLM call failed: {e}")
            return {
                "messages": messages,
                "error": f"Topic_Explainer_Agent LLM call failed: {e}",
            }
        messages.append(explainer_llm_response)

        # No tool calls = LLM is done, this is the final answer
        if not explainer_llm_response.tool_calls:
            final_response = explainer_llm_response
            print(f"[Topic_Explainer_Agent] Complete after {iteration + 1} LLM call(s)")
            break

        # Process each tool call in this response
        print(f"[Topic_Explainer_Agent] {len(explainer_llm_response.tool_calls)} tool call(s) requested:")

        for tool_call in explainer_llm_response.tool_calls:

            tool_name = tool_call["name"]  #tool name
            tool_args = tool_call["args"]  # args of the tool 
            print(f"Tool Invoked  → {tool_name}({tool_args})")

            tool_response = execute_tool_call(tool_call)

            # Truncate very long results in the log (not in the message)
            log_result = tool_response[:100] + "..." if len(tool_response) > 100 else tool_response
            print(f"Response Returned    ← {log_result}")

            messages.append(ToolMessage(content=tool_response,tool_call_id=tool_call["id"],))
    
    # Handle max iterations reached without a final answer
    if final_response is None:
        error_msg = (
            f"Explainer reached max iterations ({max_iterations}) "
            "without producing a final explanation. "
            "This may indicate the model is stuck in a tool-calling loop."
        )
        print(f"[Topic_Explainer_Agent] WARNING: {error_msg}")
        return {
            "messages": messages,
            "error": error_msg,
        }

    explanation_length = len(final_response.content)
    print(f"[Topic_Explainer_Agent] Explanation Length is: {explanation_length} characters")
    #print(f"[Topic_Explainer_Agent] Explanation is       : {final_response.content} characters")

    return {
        "messages": messages,
        "error": None,
        # Pass core state through explicitly, LangGraph 1.1.0 state propagation workaround
        "roadmap": state.get("roadmap"),
        "current_topic_index": state.get("current_topic_index", 0),
        "session_id": state.get("session_id", ""),
    }
