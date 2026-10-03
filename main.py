"""
This is a temporary main file to invoke the workflow
Later will be replaced by the front-end UI screens
"""
import sys
from pathlib import Path
import uuid

from langgraph.types import Command
# Add src/ to Python path before any project imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from graph.workflow import graph_workflow
from graph.Flow_State import initial_state,RoadMap
from langchain_core.runnables import RunnableConfig

def run_session(goal: str, session_id: str | None = None) -> None:

    is_resume = session_id is not None
    if not session_id:
        session_id = str(uuid.uuid4())[:8]

    print(f"\n{'='*60}")
    print("Learning Accelerator")
    print(f"Session ID: {session_id}")

    CONFIG: RunnableConfig = {
                    "configurable": {"thread_id": session_id}
                }

    if is_resume:
        print("Resuming existing learning session...")
    else:
        print(f"Goal: {goal}")

    print(f"{'='*60}")

    #init_state = initial_state("Learn Python decorators","user-0128")
    init_state = None if is_resume else initial_state(goal, session_id)
    try:
        final_state = graph_workflow.invoke(init_state,config=CONFIG)
    except Exception as e:
        if is_resume:
            print(f"\n[ERROR] Could not resume session '{session_id}': {e}")
            print("If the session ID is wrong or the checkpoint database has been deleted, start a new session instead.")
            return
        raise    

    # ── Handle human-in-the-loop interrupt ────────────────────────────
    # When the graph hits interrupt(), it pauses and returns with
    # "__interrupt__" in the result. We collect user input and resume.
    while "__interrupt__" in final_state:
        interrupt_payload = final_state["__interrupt__"][0].value

        # After SqliteSaver round-trip, the roadmap in the payload may be a dict.
        raw_roadmap = interrupt_payload.get("roadmap")
        roadmap = (
            RoadMap.from_dict(raw_roadmap)
            if isinstance(raw_roadmap, dict)
            else raw_roadmap
        )

        # Display the roadmap for approval
        if roadmap:
            print(f"\n{'='*60}")
            print("Proposed Study Plan")
            print(f"{'='*60}")
            print(f"Goal: {roadmap.goal}")
            print(f"Duration: {roadmap.total_estimated_weeks} weeks @ "
                    f"{roadmap.total_required_hours_per_week} hrs/week\n")
            for i, topic in enumerate(roadmap.topics, 1):
                prereqs = (f" (needs: {', '.join(topic.topic_pre_requisites)})"
                            if topic.topic_pre_requisites else "")
                print(f"  {i}. {topic.topic_title} "
                        f"({topic.estimated_minutes_tocomplete_topic} min){prereqs}")
                print(f"     {topic.topic_description}")

        print(f"\n{interrupt_payload.get('prompt', 'Continue further?')}")
        user_input = input("User Response is : ").strip()

        # Resume the graph with the user's decision
        print("[main.py] Invoking graph again after HITL")
        final_state = graph_workflow.invoke(Command(resume=user_input), config=CONFIG)
        print("[main.py] Invoked graph after HITL completed")

    print(f"Final state after graph execution  is \n : {final_state}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Learning Accelerator: a four-agent study system that plans a "
            "curriculum, explains topics from your notes, quizzes you, and "
            "adapts based on results. All inference runs locally via Ollama."
        ),
        epilog=(
            "Examples:\n"
            "  python main.py \"Learn Python closures from scratch\"\n"
            "  python main.py --resume a3f1b2c4\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "goal", nargs="?",
        default="Learn Python closures and decorators from scratch",
        help="What you want to learn (default: a Python closures starter goal)",
    )
    parser.add_argument(
        "--resume", metavar="SESSION_ID",
        help="Resume an existing session by its 8-char ID",
    )
    args = parser.parse_args()

    if args.resume:
        run_session(goal="", session_id=args.resume)
    else:
        run_session(goal=args.goal)