
"""
This Agent reads the Study Roadmap from the state and show it to user
And ask for the approval
If rejected, again flow will go to Study_Planner_Agent for plan generaton and comes for approval

Input:
 state["roadmap"]

Output:
    Updates roadmap_approved in state and return the state

This node comes between the Roadmap planner and Explainer
Once the planner prepares the roadmap, it requests for the Human Approval (HITL)
Once user approves it, then graph will proceed further to Explainer node
So the state resumes from the sqlite db once user approves it    
"""
from graph.Flow_State import AgentState,RoadMap
from langgraph.types import interrupt

def human_approval_node(state: AgentState) -> dict:
    """
    1) First reads the RoadMap object from the state, to show it to user while asking for approval
    2) Then based on user response it updates the "approved" variable in graph state
    3) Returns the entire state as in resume we need to send entire state object
    """
    roadmap:  RoadMap | None = state.get("roadmap")

    if roadmap is None:
        # No roadmap to approve, auto-approve and continue
        print("[Human Approval Agent] -> No roadmap found, skipping approval")
        return {"roadmap_approved": True}

    print("\n[Human Approval] Pausing for roadmap review...")

    # interrupt() pauses the graph here.
    # The dict passed to interrupt() is the "payload".
    # main.py reads this to know what to show the user.
    # Execution resumes when Command(resume=...) is called.
    decision = interrupt({
        "type": "roadmap_approval",
        "roadmap": roadmap,
        "prompt": (
            "Does this study plan look good?\n"
            "  Type 'yes' to start studying\n"
            "  Type 'no' to generate a different new plan"
        ),
    })

    # decision is whatever the user typed (via Command(resume=...)
    approved = str(decision).lower().strip() in ("yes", "y", "ok", "approve","proceed")

    if approved:
        print("[Human Approval] Roadmap approved, starting study session")
    else:
        print("[Human Approval] Roadmap rejected, regenerating...")

    return {"roadmap_approved": approved,
            "goal":state.get("goal", ""),
            "session_id": state.get("session_id", ""),
            "roadmap": roadmap,
            "error": None,}