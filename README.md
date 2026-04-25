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
- **Orchestration**: LangGraph, LangChain
- **Backend API**: FastAPI, Uvicorn, ngrok (Colab-ready)
- **LLM**: Groq API (Llama-3.1-8b-instant) / Claude API
- **UI**: Streamlit (Dashboard with Plotly mapping)
- **Routing**: NetworkX (City routing graph)
- **Language**: Python

## 📊 Inputs & Outputs

- **Input**: Mock Hinglish 112 call transcripts (panicked, vague, duplicate).
- **Output**: Dispatched resources, incident log, routing decisions, and reasoning explanations.
- **UI**: A Streamlit dashboard showing live incidents, a resource map, a dispatch log, and real-time agent reasoning.

## ⚖️ Constraints & Features

- **100% Free Tools**: Uses only free APIs and open-source tools (Groq, ngrok free tier, Google Colab).
- **Hinglish Support**: Natively processes mixed Hindi-English input common in Indian emergency calls.
- **Explainable AI**: Every dispatch decision made by the Strategy Agent includes a plain English explanation to ensure transparency and trust.
- **Live Demo Ready**: Decoupled architecture allows the heavy agentic pipeline to run on Google Colab, while the UI connects from any local machine.

## 🚀 How to Run

1. **Setup Environment**:
   ```bash
   pip install -r requirements.txt
   cp .env.example .env
   # Add your GROQ_API_KEY and NGROK_AUTH_TOKEN to .env
   ```

2. **Start the Backend (via Colab or locally)**:
   - To run locally, simply execute `colab_backend.py`.
   - To run on Colab, copy the contents of `colab_backend.py` into a notebook and run the cells. It will start a FastAPI server and expose it via ngrok. Note down the public URL.

3. **Start the UI**:
   ```bash
   streamlit run ui/dashboard.py
   ```
   - Paste the ngrok URL into the "Connection" sidebar in the Streamlit UI.

## 📂 Project Structure

```text
crisisgrid-ai/
├── agents/
│   ├── triage_agent.py      # Extracts JSON from transcripts
│   ├── fusion_agent.py      # Merges duplicate incidents
│   ├── dispatch_agent.py    # Routes resources via NetworkX
│   └── strategy_agent.py    # Makes LLM-based trade-off decisions
├── graph/
│   └── workflow.py          # LangGraph pipeline definition
├── data/
│   ├── mock_calls.py        # Hinglish transcripts
│   ├── city_graph.py        # NetworkX grid of Delhi NCR
│   └── resources.py         # Mock ambulances, fire trucks, etc.
├── ui/
│   └── dashboard.py         # Streamlit visual dashboard
├── utils/
│   └── state.py             # Shared LangGraph state TypedDict
├── colab_backend.py         # FastAPI + ngrok server entrypoint
├── requirements.txt
├── .env.example
└── README.md
```
