"""
    This file contains the state of the entire workflow which will be updated by every agent
    
    This graph will be checkpointed to SQLite after execution of each node by Langgraph automatically.
    This is how it handles the system crashes or resume of the workflow.
"""

from __future__ import annotations
from dataclasses import dataclass,asdict,field
from typing import Annotated,TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
import json

# ─────────────────────────────────────────────────────────────────────────────
# Study Roadmap data class object
# These are the complex objects that live inside AgentState.
# We use @dataclass instead of plain dicts for two reasons:
#   1. Type safety, you can't accidentally misspell a field name
#   2. Clarity, the structure documents itself
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Topic:
    topic_title: str    #Title of the topic
    topic_description:str #Description about what we will learn in this topic
    estimated_minutes_tocomplete_topic: int #Minutes required to complete topic
    topic_status: str = "pending" #status of the topic
    topic_pre_requisites: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dataclass object to JSON for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Topic":
        """Reconstruct from a python dict to dataclass object (e.g., after JSON round-trip) to ."""
        return cls(
            topic_title=data["topic_title"],
            topic_description=data["topic_description"],
            estimated_minutes_tocomplete_topic=data["estimated_minutes_tocomplete_topic"],
            topic_pre_requisites=data.get("topic_pre_requisites", []),
            topic_status=data.get("topic_status", "pending"),
        )
 

@dataclass
class RoadMap:
    goal: str                              #User goal
    total_estimated_weeks: int             #No of weeks required to achieve goal
    topics: list[Topic]                    #List of topics
    total_required_hours_per_week: int = 5 #No of hours required per week to achieve goal

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls,data : dict) -> "RoadMap":
        return cls(
            goal=data["goal"],
            total_estimated_weeks=data["total_estimated_weeks"],
            total_required_hours_per_week=data["total_required_hours_per_week"],
            topics=[Topic.from_dict(t) for t in data.get("topics", [])]
        )


@dataclass
class QuizQuestion:
    """
    One question within a quiz, with the user's answer and grading.

    The Quiz Generator creates these.
    The Progress Coach reads them to identify weak areas.
    """
    question: str
    expected_answer: str

    # Filled in after the user answers
    user_answer: str = ""
    correct: bool = False
    feedback: str = ""          # One sentence of specific feedback from grader
    score: float = 0.0          # 0.0 – 1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QuizResult:
    """
    The complete result of one quiz session on a single topic.

    Stored in AgentState.quiz_results, one entry per topic per session.
    The Progress Coach reads this to decide what to do next.
    """
    topic: str
    questions: list[QuizQuestion]
    average_score: float    # Average score across all questions (0.0 – 1.0)
    weak_areas: list[str]   # Concepts the student got wrong or missed
    timestamp: str = ""     # ISO format UTC timestamp

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "average_score": self.average_score,
            "weak_areas": self.weak_areas,
            "timestamp": self.timestamp,
            "questions": [q.to_dict() for q in self.questions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QuizResult":
        """
        Reconstruct from a plain dict.

        Called when LangGraph deserializes quiz_results from a SQLite
        checkpoint as raw dicts (msgpack round-trip). This happens when
        resuming a crashed or interrupted session.
        """
        return cls(
            topic=data.get("topic", ""),
            questions=[],           # Questions not needed for coaching logic
            average_score=float(data.get("average_score", 0.0)),
            weak_areas=data.get("weak_areas", []),
            timestamp=data.get("timestamp", ""),
        )  
    
# ─────────────────────────────────────────────────────────────────────────────
# The main state class
#
# AgentState is the TypedDict that LangGraph manages.
# Every node in the graph receives the full state and returns
# a partial update (only the keys it changed).
#
# Why TypedDict and not a regular class?
#   LangGraph requires dict-compatible objects. TypedDict gives us
#   type safety while staying dict-compatible.
#
# Why inherit from TypedDict directly instead of using a subclass trick?
#   LangGraph 1.x works cleanly with TypedDict. No need for workarounds.
# ─────────────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    goal: str                                           #User goal
    messages: Annotated[list[BaseMessage],add_messages] #To store the conversation history btw user and LLM
    session_id: str                                     #ID of the current session
    roadmap: RoadMap | None                             # Roadmap object
    roadmap_approved: bool                              # Whether Human approved or not
    current_topic_index: int                            # To see which topic are we on?
    quiz_results: list[QuizResult]                      # Quiz results type as list because of multiple topics
    weak_areas: list[str]                               # to set the weak areas based on score           
    error: str | None                                   #Error message incase if any Node goes into error

# ─────────────────────────────────────────────────────────────────────────────
# Create a initial state definition to have the correct initial values for state
# Never create the initial state manually as this can lead to missing of some
# values or can set wrong values
# For this function initial_state we pass below things:
    # 1) goal -> state["goal"]
    # 2) session_id -> state["session_id"]

    #Output will be entire state with default values
# ─────────────────────────────────────────────────────────────────────────────

def initial_state(goal: str , session_id:str) -> AgentState:
    return {
        "goal": goal,
        "messages": [],
        "session_id": session_id,
        "roadmap": None,
        "roadmap_approved": False,
        "current_topic_index":0,
        "quiz_results":[],
        "weak_areas":[],
        "error": None,
    }

def get_current_topic(state: AgentState) -> "Topic | None":
    """
    Get the topic currently being studied, or None if session is complete.

    Usage in an agent node:
        topic = get_current_topic(state)
        if topic is None:
            return {"error": "No current topic"}
    
    Handles dict or dataclass roadmap (msgpack deserialization returns dicts).
    """
    roadmap = state.get("roadmap")
    if roadmap is None:
        return None

    # After checkpoint deserialization, roadmap may come back as a dict
    if isinstance(roadmap, dict):
        topics_raw = roadmap.get("topics", [])
    else:
        topics_raw = roadmap.topics

    idx = state.get("current_topic_index", 0)
    print(f"[Flow_state] -> idx is : {idx},type of topics_raw is : {type(topics_raw)}")

    if idx >= len(topics_raw):
        return None

    t = topics_raw[idx]
    # Individual topics may also come back as dicts
    if isinstance(t, dict):
        print(f"[Flow_state] -> Current fetched topic(dict) is : {t}")
        return Topic.from_dict(t)
    print(f"[Flow_state] -> Current fetched topic is : {t}")
    return t

def get_latest_quiz_result(state: dict) -> QuizResult | None:
    """
    Get the most recent quiz result, or None if no quizzes have run.

    Handles dict or dataclass quiz results, after a checkpoint resume,
    LangGraph may deserialize quiz_results as a list of plain dicts.

    Usage in the progress_coach node to analyze the just-completed quiz.
    """
    results = state.get("quiz_results", [])
    if not results:
        return None

    latest = results[-1]

    # After msgpack checkpoint deserialization, quiz results may come
    # back as plain dicts. Reconstruct them using from_dict().
    if isinstance(latest, dict):
        return QuizResult.from_dict(latest)

    return latest

def is_all_topics_covered(state: AgentState) -> bool:         

        roadmap_temp = state.get("roadmap",[])

        topics = roadmap_temp.get("topics",[]) if isinstance(roadmap_temp,dict) else roadmap_temp.topics
        idx = state.get("current_topic_index", 0)
        if idx >= len(topics):
            return True
        else:
            return False