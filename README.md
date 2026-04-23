# CrisisGrid AI

**Autonomous Multi-Agent Emergency Dispatch System for Indian Cities**

## 🚨 The Problem

During large-scale disasters (floods, fires, earthquakes), emergency helplines like 112 receive massive volumes of panicked calls. These calls are often unstructured (Hinglish), duplicated (multiple people reporting the same incident), and sometimes conflicting. Human operators can quickly get overwhelmed, leading to delays in critical resource dispatch.

## 💡 What We Are Building

CrisisGrid AI is a multi-agent AI system designed to handle the influx of emergency calls autonomously. It processes unstructured data, resolves conflicts, and makes optimal dispatch decisions. 

The system consists of 4 specialized AI agents working together using **LangGraph**:

1. **Triage Agent** — Reads raw 112 call transcripts, extracts the location, incident type, severity (low/medium/critical), and resources needed. Outputs structured JSON.
2. **Fusion Agent** — Merges duplicate calls about the same incident and resolves conflicting information. Outputs one clean master incident object per unique event.
3. **Dispatch Agent** — Manages a mock resource database (ambulances, fire trucks, police vans). Uses a `networkx` city graph to find the nearest available unit, routes it, and marks units as dispatched.
4. **Strategy Agent** — Handles hard trade-off decisions (e.g., the last ambulance is left, but there are two critical incidents, or re-routing mid-dispatch). Outputs the final decision along with a plain English explanation for transparency.

All agents share a common LangGraph state object to maintain context and coordination.

## 🛠 Tech Stack

Built for an Agentic AI hackathon with a focus on accessibility and open tools:
- **Orchestration**: LangGraph
- **LLM**: Claude API (Free tier) / Groq (Free)
- **UI**: Streamlit (Dashboard)
- **Routing**: NetworkX (City routing graph)
- **Language**: Python

## 📊 Inputs & Outputs

- **Input**: Mock Hinglish 112 call transcripts (panicked, vague, duplicate).
- **Output**: Dispatched resources, incident log, routing decisions, and reasoning explanations.
- **UI**: A Streamlit dashboard showing live incidents, a resource map, a dispatch log, and real-time agent reasoning.

## ⚖️ Constraints & Features

- **100% Free Tools**: Uses only free APIs and open-source tools.
- **Hinglish Support**: Natively processes mixed Hindi-English input common in Indian emergency calls.
- **Explainable AI**: Every dispatch decision made by the Strategy Agent includes a plain English explanation to ensure transparency and trust.
- **Live Demo Ready**: Fully functional for a live hackathon demonstration.

## 📂 Project Structure

```text
crisigrid-ai/
├── agents/
│   ├── triage_agent.py
│   ├── fusion_agent.py
│   ├── dispatch_agent.py
│   └── strategy_agent.py
├── graph/
│   └── workflow.py
├── data/
│   ├── mock_calls.py        # Hinglish transcripts
│   ├── city_graph.py        # networkx graph
│   └── resources.py         # mock ambulances, trucks, etc.
├── ui/
│   └── dashboard.py         # Streamlit app
├── utils/
│   └── state.py             # shared LangGraph state schema
├── requirements.txt
├── README.md
└── .gitignore
```
