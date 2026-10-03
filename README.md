# Production-Grade Multi-Agent AI System -> For hands-on experience in working with LLMs


## What this project builds

A **Software Languages Learning platform**: a four-agent system that plans a study curriculum,
explains topics from your own notes or LLM parametric knowledge, quizzes you, and adapts based on results.

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

## Requirements

- Python 3.11+
- Langchain & Langgraph
---
## Project structure

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
```

---

## Adding your own study materials

Replace or add Markdown files in `study_materials/sample_notes/`.
The Explainer agent reads every `.md` file in that directory automatically
via the MCP filesystem server. No configuration changes needed.

---

## Configuration reference

See `.env.example` for all available settings.

---

## Author

**Prashanth Chowdary Rimmalapudi**

