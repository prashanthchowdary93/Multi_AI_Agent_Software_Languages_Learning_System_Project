"""
This is a Study_Planner Agent which takes user input (GOAL) and generates the Study Roadmap


It demonstrates the foundational pattern every agent follows:
  read from state → call LLM → parse output → return state update

###Input###
Reads the State["goal"] and invoke the LLM to generate Study Roadmap

###Output###
Updates the Study Roadmap received from LLM into state
writes state["Roadmap"]

#AI Functionalities/concepts used:
 1) Only LLM invoke

"""
import json

from graph.Flow_State import AgentState
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage,HumanMessage,AIMessage
from graph.Flow_State import RoadMap
from dotenv import load_dotenv

#Load the ENV file
load_dotenv()

def Study_Planner_Node(state: AgentState) -> dict:

    # First Read the goal from the state

    goal = state["goal"].strip()

    if not goal:
        print(f"[Study_Planner_Agent] -> User goal  must be defined first")
        return {"error": "No learning goal provided. Set state['goal'] before running."}

    print(f"[Study_Planner_Agent] -> User Goal is : {goal}")

    # Prepare the Study Planner Agent Prompt
    STUDY_PLANNER_PROMPT = """
    You are an expert curriculum designer. Your job is to create a structured study roadmap when given a learning goal.

    Return ONLY valid JSON with no prose, no markdown code fences, no explanation.
    The JSON must match this exact schema present in StudyRoadmap

    Rules:
    - Order topics from foundational to advanced
    - prerequisites must reference earlier topic titles exactly as written
    - estimated_minutes is time for one focused study session, not total time
    - Strictly Aim for 1 to 2 topics only, enough depth without being overwhelming
    - status must always be "pending"

    RETURN ONLY THE STRUCTURED OUTPUT.
    """

    #Now Create the LLM object with GPT-4 mini model
    llm_obj = ChatOpenAI(model='gpt-4o-mini')

    # Since we want LLM to return response in strucure of Roadmap, so we will use struc o/p
    llm_obj_with_stru_output = llm_obj.with_structured_output(RoadMap)

    # Add the conversation to the messages
    messages = [
        SystemMessage(content=STUDY_PLANNER_PROMPT),
        HumanMessage(content=f"Create a study roadmap for this learning goal: {goal}"),
    ]

    #Invoke the LLM now to generate response
    try:
      response = llm_obj_with_stru_output.invoke(messages)
    except Exception as e:
       print(f"[Study_Planner_Agent] -> Exception occured in LLM invoke is : {e}")
       return {"error": str(e),"messages": messages}

    print(f"[Study_Planner_Agent] -> Study Planner Response is : {response}")

    # Since messages is based on Lanchain BaseMessage, it expects evrything to be in
    # System/Human/AIMessage type, so converting it into AIMessage
    planner_message = AIMessage(
        content=json.dumps(response)
    )

    #Update the partial state and return it
    return {"roadmap":response,"messages":messages + [planner_message],"error":None}
