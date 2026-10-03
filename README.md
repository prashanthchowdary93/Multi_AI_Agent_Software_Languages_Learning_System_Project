


## Production-Grade Multi-Agent AI System -> For hands-on experience in working with LLMs

     ```
    ** What this project builds **
    
    A **Software Languages Learning platform**: a four-agent system that plans a study curriculum,
    explains topics from your own notes or LLM parametric knowledge, quizzes you, and adapts based on results.
    
    ** Multi-AI Agent Software Languages Learning System **
    
    ```

## Problem Statement

    ```
    Learning any software programming requires multiple types of assistance or stages like explaining topic and then evaluating based on the topic content.
    
    One general-purpose AI agent may handle everything, but responsibilities become difficult to separate and maintain.
    Different learning tasks require different capabilities.
    
    The project addresses this using specialized 4 different agents.
    ```

## Solution

    ```
    This multi-agent system takes input (goal) from the user and then generates curriculum plan for the provided goal.
    
    Then based on the curriculum planned, using MCP tool calls it reads the available notes and bring back the content if provided notes has the content related to provided     goal, otherwise it brings content from its parametric knowledge.
    
    Once explainer agent provides the content, then quiz generator agent generates the quiz questions to evaluate the user understanding and then grades the user answers        and then progress coach agent takes this explanation, quiz scores and then provides topics which needs to reviewed again by the user.
    
    This loops runs until it completes all the topics provided in curriculum plan.
    ```

## Why multi agents?

    ```
    This solution was designed in multi agent system because of different types of LLM calls and only 1 agent required MCP Tool calls.
    Like Planner agent may need simple straight forward prompt with temperature as 0 because we don't want every time LLM to generate different types of curriculum for same     topic where as explainer topic needs Tool calling using MCP and LLM calls in loop until it finds the explanation and quiz generator may need temperature as > 0 while        generating question while in the same agent for grading it needs temperature as 0 because every time we want LLM to grade the answer in consistent way .
    
    ```

## Key Features

    ```
    - Multi-agent orchestration
    - Specialized learning agents
    - Programming language explanations
    - quiz question generation
    - Tool integration through MCP
    - Stateful agent workflows
    - Error handling
    - Modular and extensible architecture
    
    ```

## System Architecture

    ```
    ***Example flow:***
    
    ```
    Goal: "Learn basics of Langgraph"
      │
      ▼
    Study Planner  →  structured study roadmap
      │
      ▼ (you approve the plan)
    Explainer           →  reads your notes via MCP, explains each topic
      │
      ▼
    Quiz Generator      →  tests understanding, grades answers with LLM-as-judge
      │
      ▼
    Progress Coach      →  adapts roadmap, calls CrewAI Study Buddy via A2A
      │
      └── loops back to Explainer for next topic
    ---
    
    ## Architecture
    
    | Layer | Technology | What it does |
    |---|---|---|
    | Orchestration | LangGraph 1.1.0 | Stateful agent graph with checkpointing |
    | Tool integration | MCP (mcp 1.26.0) | Standardised agent-to-tool protocol |
    | LLM Inference | OpenAI |
    | Observability | Langsmith | Full trace of every agent and LLM call |
    | Evaluation | DeepEval 3.9.1 | LLM-as-judge quality metrics |
    ---
    ```

## Multi-Agent Workflow

    ```
    1) User submits the the goal (Ex. Basics of Langgraph fundamentals)
    2) Then curriculum planner agent generates the curriculum plan and sent the request for Human Approval (HITL) to check and approve the plan generated
    3) If Human approves, then explainer agent explains all the topics listed in the plan and for each topic it explains using grounded notes by using MCP tools or from its       parametric knowledge and then quiz generator agent generates the questions and then does the grading and then progress coach agent provides the valuable feedback            based on the quiz score and this loop runs until last topic
    4) If Human rejects the study plan, then again it will generate plan and ask for human approval again and then again process mentioned in step 3 executes
    
    ```


## Agents and Responsibilities

    https://github.com/user-attachments/files/33004348/test.xlsx


## Technology Stack

    ```
    | Technology | Purpose |
    |---|---|
    | Python | Application development |
    | LangGraph | Agent orchestration |
    | MCP | Tool/context integration |
    | LLM | Reasoning and response generation |
    | Git/GitHub | Version control |
    
    ```

## Project Structure

    ```
    Multi_Agent_Learning_Project_Handson/
    ├── src/
    │   ├── agents/                 # LangGraph agent nodes
    │   │   ├── Study_Planner_Agent.py
    │   │   ├── Topics_Explainer_Agent.py
    │   │   ├── Quiz_Generator_Agent.py
    │   │   ├── Progress_Coach_Agent.py
    │   │   └── Human_Approval_Agent.py
    │   ├── graph/
    │   │   ├── FLow_State.py            # Shared AgentState TypedDict
    │   │   └── workflow.py         # LangGraph graph definition
    │   ├── mcp_servers/            # MCP tool servers
    │   │   ├── filesystem_server.py
    ├── tests/
    │   ├── conftest.py             # Shared fixtures and markers
    │   ├── test_deepeval.py        # 2 tests
    ├── study_materials/
    │   └── sample_notes/           # Markdown files the agents read
    ├── data/                       # SQLite checkpoint DB (created at runtime)
    ├── main.py                     # Entry point
    ├── Streamlit_UI_Screen.py      # For building UI screen for the project
    ├── docker-compose.yml          # Langfuse self-hosted stack
    ├── Makefile                    # One-command startup
    ├── requirements.txt
    └── .env.example
    
    ```
## Session resume

    Every session is checkpointed to `data/agent_history.db` after each agent node.
    To resume a stopped session:
    
    ```bash
    python main.py --resume <session-id>
    ```
    
    The session ID is printed at the start of every run.
    
    ---

## Observability

    Used the Langsmith API keys and URL for the observability
    ```
    ---

## Testing

    ```
    # Quality evaluation tests, run before releases (~90 seconds, requires apenai api keys)
    # 2 LLM-as-judge tests
    pytest tests/test_eval.py -v -s -m eval

## Running the Application

    ```
    We can run the application using main.py for terminal interface, using below command
      python main.py "Basics of Langgraph fundamentals"
    
    We can also run the application using Streamlit_UI_Screen.py for UI screen interface,using below command:
      streamlit run Streamlit_UI_Screen.py
    ```

## Author
**Prashanth Chowdary Rimmalapudi**
