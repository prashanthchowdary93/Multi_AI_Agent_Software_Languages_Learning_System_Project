
from graph.Flow_State import AgentState
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage,SystemMessage,AIMessage
from graph.Flow_State import QuizResult,QuizQuestion,get_current_topic
from typing import Annotated,Literal
from pydantic import Field,BaseModel
import json
from datetime import datetime, timezone

QUESTION_GENERATION_PROMPT = """You are a quiz designer for a student learning programming.

Given a topic and explanation, generate {n} quiz questions that test
genuine understanding, not just the ability to repeat memorized phrases.

Good questions require the student to:
  - Apply a concept to a new situation
  - Explain WHY something works, not just WHAT it does
  - Identify edge cases or common mistakes
  - Compare related concepts

Return ONLY valid JSON with no prose or markdown:
{{
  "questions": [
    {{
      "question": "Clear, specific question text ending with ?",
      "expected_answer": "Model answer in 1-3 sentences",
      "difficulty": "easy|medium|hard"
    }}
  ]
}}

Rules:
  - Include at least one question about a common mistake or gotcha
  - expected_answer should be concise but complete
  - Avoid yes/no questions, ask for explanation or demonstration
"""

GRADING_PROMPT = """You are a fair teacher grading a student's answer.

Question: {question}
Model answer: {expected_answer}
Student's answer: {student_answer}

Grade the student's answer honestly. Be generous with partial credit:
  - Fundamentally correct with minor gaps: 0.7-0.9
  - Correct concept but imprecise: 0.5-0.7
  - Partially correct: 0.3-0.5
  - Fundamentally wrong: 0.0-0.2

Return ONLY valid JSON with no prose or markdown:
{{
  "correct": true,
  "score": 0.85,
  "feedback": "One specific sentence of feedback",
  "missing_concept": "Key concept missed, or empty string if answer is correct"
}}
"""

class QuizFormat(BaseModel):
    question:str = Field(description='Question about the provided topic')
    expected_answer: str = Field(description='Expected answer of the question')
    difficulity: Literal['easy','medium','difficulity']

class QuizList(BaseModel):
    quizlist:list[QuizFormat]

def generate_questions(topic,explanation,n=1) -> list[dict]:

    llm_obj = ChatOpenAI(model='gpt-4o-mini')
    llm_obj_with_structure_output = llm_obj.with_structured_output(QuizList)

    format_prompt = QUESTION_GENERATION_PROMPT.format(n=1)

    try:
        question_gen_response = llm_obj_with_structure_output.invoke(
            [SystemMessage(content=format_prompt),
             HumanMessage(content=f"Topic: {topic}\n\nExplanation:\n{explanation}"),]
        )
    except Exception as e:
        print(f"[Quiz Generator] LLM call failed during question generation: {e}")
        # Return minimal fallback so the quiz can still run
        return [{
            "question": f"What is the main concept covered in {topic}?",
            "expected_answer": "See your study notes for this topic.",
            "difficulty": "medium",
        }]

    try:
        #Returning the response in python dict format , instead of pydantic object
        return [q.model_dump() for q in question_gen_response.quizlist]
        
    except (json.JSONDecodeError, KeyError):
        pass

    # Fallback: one generic question if parsing fails
    print("[Quiz Generator] Warning: could not parse questions, using fallback")
    return [{
        "question": f"In your own words, explain the key concept of {topic} and why it matters.",
        "expected_answer": "A clear explanation demonstrating conceptual understanding.",
        "difficulty": "medium",
    }]    

class user_answer(BaseModel):
    correct: bool = Field(description="User answer is correct or wrong")
    score:float = Field(description='score of the user answer') 
    feedback: str = Field(description='Feedback for the user answer')
    missing_concept:str = Field(description="Missing concept in user answer if answer is wrong")
    
def grade_answer(question: str, expected: str, student_answer: str) -> dict:
    """
    Use the LLM to grade a student's answer against the expected answer.

    Args:
        question:       The question that was asked.
        expected:       The model answer.
        student_answer: What the student wrote.

    Returns:
        Dict with keys: correct (bool), score (float), feedback (str),
        missing_concept (str).
        Returns a safe default if LLM output can't be parsed.
    """
    # Very low temperature, grading should be consistent and analytical
    llm = ChatOpenAI(model='gpt-4o-mini')
    llm_with_str_out_grade = llm.with_structured_output(user_answer)

    prompt = GRADING_PROMPT.format(
        question=question,
        expected_answer=expected,
        student_answer=student_answer,
    )

    try:
        response = llm_with_str_out_grade.invoke([HumanMessage(content=prompt)])
    except Exception as e:
        print(f"[Quiz Generator] LLM call failed during grading: {e}")
        # Return partial credit so the session can continue
        return {
            "correct": False,
            "score": 0.5,
            "feedback": "Could not grade answer due to a connection error.",
            "missing_concept": "",
        }
    
    try:
        return response.model_dump()
    except json.JSONDecodeError:
        # Safe default if grading fails
        return {
            "correct": False,
            "score": 0.0,
            "feedback": "Could not grade automatically, please review manually.",
            "missing_concept": "",
        }

def generate_quiz(topic:str,explanation:str) -> QuizResult:

    print(f"\n{'='*60}")
    print(f"Quiz: {topic}")
    print(f"{'='*60}")
    print("Answer each question in your own words.\n")

    #First we need to generate the questions and expected answers from LLM
    # LLM output should be like this question,expected_answer,difficulity_level
    
    questions_list = generate_questions(topic, explanation, n=1)

    graded_questions = []
    total_score = 0.0
    weak_areas = []
    
    #Second we need to grade the user answers using LLM As Judge protocol  
    for i, q_data in enumerate(questions_list, 1):
        question_text = q_data["question"]
        expected = q_data["expected_answer"]
        difficulty = q_data.get("difficulty", "medium")

        print(f"Question {i} [{difficulty}]: {question_text}")
        user_answer = input("Your answer: ").strip()

        # Handle empty answers
        if not user_answer:
            user_answer = "(no answer provided)"

        print("Grading the user provided answer...")
        grade = grade_answer(question_text, expected, user_answer)
        print(f"[QUiz Generator] -> Grade is : {grade}")
        score = float(grade.get("score", 0.0))
        correct = bool(grade.get("correct", False))
        feedback = grade.get("feedback", "")
        missing = grade.get("missing_concept", "")

        total_score += score

        # Show result
        status = "✓" if correct else "✗"
        print(f"{status} Score: {score:.0%}, {feedback}\n")

        if missing:
            weak_areas.append(missing)

        graded_questions.append(QuizQuestion(
            question=question_text,
            expected_answer=expected,
            user_answer=user_answer,
            correct=correct,
            feedback=feedback,
            score=score,
        ))

    # Calculate overall score
    avg_score = total_score / len(questions_list) if questions_list else 0.0
    correct_count = sum(1 for q in graded_questions if q.correct)

    print(f"{'='*60}")
    print(f"Quiz complete! Score: {avg_score:.0%} "
          f"({correct_count}/{len(graded_questions)} correct)")
    if weak_areas:
        print(f"Areas to review: {', '.join(set(weak_areas))}")
    print(f"{'='*60}\n")

    return QuizResult(
        topic=topic,
        questions=graded_questions,
        average_score=avg_score,
        weak_areas=list(set(weak_areas)),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

# ─────────────────────────────────────────────────────────────────────────────
# The LangGraph node
# ─────────────────────────────────────────────────────────────────────────────
def Quiz_Generator_Agent_Node(state: AgentState) -> dict:
    print("Inside Quiz generator coach Agent")

    #get the current topic
    current_topic = get_current_topic(state)

    if not current_topic:
        return {
                    "error": "No current topic found. Study Planner Agent/Explainer Agent must run first.",
                }
        
    session_id = state.get("session_id", "unknown")

    raw_messages = state.get("messages",[])
    explanation = ""
    if not raw_messages:
        return {
                    "error": "No current topic found. Study Planner Agent/Explainer Agent must run first.",
                }

    for msg in reversed(raw_messages):
        if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
            explanation = str(msg.content)
            break

    if not explanation:
        print("[Quiz Generator] Warning: no explanation found, generating generic quiz")
        explanation = f"Topic: {current_topic.topic_title}. {current_topic.topic_description}" 

    print(f"\n[Quiz Generator] Generating quiz Questions for topic: '{current_topic.topic_title}'")
    quiz_result = generate_quiz(current_topic.topic_title, explanation)

    # Accumulate results
    existing_results = state.get("quiz_results", [])
    all_weak_areas = list(set(
        state.get("weak_areas", []) + quiz_result.weak_areas
    ))

    return {
        "quiz_results": existing_results + [quiz_result],
        "weak_areas": all_weak_areas,
        "error": None,
        # Pass core state through explicitly, LangGraph 1.1.0 state propagation workaround
        "roadmap": state.get("roadmap"),
        "current_topic_index": state.get("current_topic_index", 0),
        "session_id": state.get("session_id", ""),
    }    


    
