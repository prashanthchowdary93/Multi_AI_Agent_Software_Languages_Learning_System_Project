"""
This Agent will
  1) Will read the current topic and quizResults
  2) Using these details it will invoke LLM to provide any message based on user quiz score
     and weak areas if any
  3) Then increment the current topic index number to shift to next topic, which will follow 
     flow again explainer -> Quiz generator -> progress coach
  4) Updates the partial state and return it
"""


from graph.Flow_State import AgentState,get_current_topic,get_latest_quiz_result,QuizResult
from langchain_openai import ChatOpenAI
import json,os
from langchain_core.messages import AIMessage,SystemMessage,HumanMessage

COACHING_PROMPT = """You are an encouraging learning coach reviewing a student's quiz results.

Provide a brief starting with sentence "Coaching feedback is" in the summary key, warm coaching message (2-3 sentences max) based on:
  - The topic studied
  - Their score (0.0 = 0%, 1.0 = 100%)
  - Any weak areas identified

Return ONLY valid JSON:
{{
  "summary": "2-3 sentence encouraging summary",
  "encouragement": "One short motivational sentence for next steps"
}}

Be specific, reference the topic and any weak areas by name.
Never be discouraging. A low score means "more practice needed", not "you failed."
"""


def get_coaching_message(topic: str, score: float, weak_areas: list[str]) -> dict:
    """Ask the LLM for a personalised coaching message."""
    llm  = ChatOpenAI(model='gpt-5-mini')
    context = {
        "topic":         topic,
        "score_percent": f"{score:.0%}",
        "weak_areas":    weak_areas if weak_areas else ["none identified"],
    }

    try:
        response = llm.invoke([
            SystemMessage(content=COACHING_PROMPT),
            HumanMessage(content=json.dumps(context)),
        ])
    except Exception as e:
        print(f"[Progress Coach] LLM call failed: {e}")
        return {
            "summary": f"You scored {score:.0%} on {topic}. Keep going!",
            "encouragement": "Every topic builds on the last.",
        }

    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {
            "summary":      f"You scored {score:.0%} on {topic}.",
            "encouragement": "Keep going, every topic builds on the last!",
        }

def Progress_Coach_Agent_Node(state: AgentState) -> dict:
    print("Inside Progress coach Agent")

    topic = get_current_topic(state)
    
    current_topic = topic.topic_title

    if not current_topic:
        return {
                    "error": "No current topic found. Study Planner Agent/Explainer Agent/Quiz Generator must run first.",
                }
    
    latest_topic_quiz_results = get_latest_quiz_result(state)

    if not latest_topic_quiz_results:
        return {
                    "error": "No current topic quiz results found. Study Planner Agent/Explainer Agent/Quiz Generator must run first.",
                }

    roadmap = state.get("roadmap")  # may be StudyRoadmap, dict, or None after resume
    if roadmap is None:
        return {"error": "No roadmap found"}
    
    current_score = 0
      
    current_score = latest_topic_quiz_results.average_score

    weak_areas = state.get("weak_areas",[])
    print(f"[Progress_coach_agent] -> weak_areas are : {weak_areas}")
    #if weak_areas:
    #    print(f"[Progress Coach] Weak areas: {', '.join(weak_areas)}")

    # ── Get coaching message ──────────────────────────────────────────
    coaching = get_coaching_message(current_topic, current_score, weak_areas)

    print(f"[Progress_coach_agent] -> Final coaching message is : {coaching}")

    #Update the topic status
    print(f"[Progress_coach_agent] -> current_score for topic {current_topic} is : {current_score}")
    if current_score >= 0.4:
        topic.topic_status = "Completed"
    else:
        topic.topic_status = "Need Review"
    #increment the topic counter and append the coaching message to messages
    current_index = 0  
    current_index = state.get("current_topic_index",0)
    current_index += 1
    topics = roadmap.get("topics",[]) if isinstance(roadmap,dict) else roadmap.topics
    all_done = False
    print(f"current_index is-1 : {current_index} ,  len(topics) is : { len(topics)}")
    if int(current_index) == len(topics):
        print("All done")
        all_done = True
    #else:
         

    if all_done:
        completed = sum(1 for t in topics if (t.get("status") if isinstance(t, dict) else t.topic_status) == "completed")
        total = len(topics)
        results = state.get("quiz_results", [])
        avg = sum(r.average_score for r in results) / max(len(results), 1)
        print(f"\n [Progress_coach_agent] ->  Session complete! {completed}/{total} topics passed.")
        print(f" [Progress_coach_agent] -> Overall average: {avg:.0%}")
    else:
        next_topic = topics[current_index]
        next_title = next_topic.get("topic_title") if isinstance(next_topic, dict) else next_topic.topic_title
        print(f"\n [Progress_coach_agent] -> Next topic is : '{next_title}'")
    print(f"{'─'*60}\n")
         
    return {"current_topic_index":current_index,"error":None,
            "messages":[AIMessage(content=coaching["summary"])],
             "roadmap":roadmap }
