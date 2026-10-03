"""
    This file contains the definition of the workflow which is defined as GRAPH
    Here we add nodes, edges and conditional edges
"""
import os
from pathlib import Path
from langgraph.graph import StateGraph,START,END
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from graph.Flow_State import AgentState,is_all_topics_covered
from agents.Study_Planner_Agent import Study_Planner_Node
from agents.Human_Approval_Agent import human_approval_node
from agents.Topics_Explainer_Agent import Topic_Explainer_Agent_Node
from agents.Quiz_Generator_Agent import Quiz_Generator_Agent_Node
from agents.Progress_Coach_Agent import Progress_Coach_Agent_Node

def route_after_human_approval(state: AgentState) -> str:
    if state.get("roadmap_approved",False):
        print("returned HITL -> explainer")
        return "explainer"
    print("reverse")
    return "study_planner"

def route_after_coach(state: AgentState) -> str:
    print("inside route_after_coach")
    if is_all_topics_covered(state):
        return "end"
    else:
        return "explainer"

def build_graph(db_path: str = "persistence/agent_history.db", interrupt_before: list | None = None):
    # Create persistence directory
    persistence_dir = Path("persistence")
    persistence_dir.mkdir(parents=True, exist_ok=True)

    if db_path == "persistence/agent_history.db":
        db_path = os.getenv("CHECKPOINT_DB", "persistence/agent_history.db")

    # SQLite database path
    #db_path = persistence_dir / "agent_history.db"

    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    #Creating the graph object
    graph = StateGraph(AgentState)

    #Adding the nodes
    graph.add_node("study_planner",Study_Planner_Node)
    graph.add_node("human_approval",human_approval_node)
    graph.add_node("explainer",Topic_Explainer_Agent_Node)
    graph.add_node("quiz_generator",Quiz_Generator_Agent_Node)
    graph.add_node("progress_coach",Progress_Coach_Agent_Node)

    #Adding the static edges
    graph.add_edge(START,'study_planner')
    graph.add_edge('study_planner','human_approval')
    graph.add_edge('explainer','quiz_generator')
    graph.add_edge('quiz_generator','progress_coach')

    #Adding the conditional edges
    graph.add_conditional_edges('human_approval',route_after_human_approval,
                                {'study_planner':'study_planner','explainer':'explainer'})

    graph.add_conditional_edges('progress_coach',route_after_coach,
                                {'explainer':'explainer','end':END})


    #Compiling the graph
    #graph_workflow = graph.compile(checkpointer=checkpointer)
    return graph.compile(checkpointer=checkpointer,
                         interrupt_before=interrupt_before or [])
    
graph_workflow = build_graph()




