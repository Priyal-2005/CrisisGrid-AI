# CrisisGrid AI

**Autonomous Multi-Agent Emergency Dispatch System for Indian Cities**

## 🚨 The Problem

During large-scale disasters (floods, fires, earthquakes), emergency helplines like 112 receive massive volumes of panicked calls. These calls are often unstructured (Hinglish), duplicated (multiple people reporting the same incident), and sometimes conflicting. Human operators can quickly get overwhelmed, leading to delays in critical resource dispatch.

## 💡 What We Are Building

CrisisGrid AI is a **stateful, real-time** multi-agent AI system designed to handle the influx of emergency calls autonomously. Unlike simple pipelines, it maintains a persistent global state that accumulates incidents over time, resolves conflicts, and makes optimal dispatch decisions under resource strain.

The system consists of 4 specialized AI agents working together using **LangGraph**:

1. **Triage Agent** — Reads raw 112 call transcripts (Hinglish/English), extracts location, incident type, severity (Low/Medium/Critical), and resources needed.
2. **Fusion Agent** — Merges duplicate calls and resolves conflicting information (e.g., two people reporting different victims at the same fire). Outputs one clean "Master Incident" per unique event.
3. **Dispatch Agent** — Manages a live resource database. Uses a `networkx` city graph to find the nearest available unit and marks them as EN ROUTE.
4. **Strategy Agent** — Handles complex trade-offs (e.g., rerouting a unit from a Medium incident to a Critical one) and provides human-readable reasoning for every action.

## ✨ Hackathon Features (Live Demo Ready)

- **Persistent Global State**: Incidents and resource movements are tracked across multiple pipeline executions. The system never "forgets" an active fire while processing a new accident.
- **Real-time Simulation**: A dedicated "Auto Mode" simulates a live dispatch center, automatically feeding mock 112 calls every few seconds to stress-test the agents.
- **Dynamic Rerouting**: The AI autonomously pulls units from lower-priority calls if a new CRITICAL incident is detected and no units are available.
- **Priority Queue UI**: Automatically sorts incidents by severity (Critical → Medium → Low) and time.
- **Interactive Control Panel**: Clicking on any incident in the dashboard focuses the map, filters the dispatch log, and shows the specific "AI Decision Reasoning" for that event.

## 🛠 Tech Stack

- **Orchestration**: LangGraph, LangChain
- **Backend API**: FastAPI, Uvicorn, ngrok (Colab-ready)
- **LLM**: Groq API (Llama-3.1-8b-instant) / Claude API
- **UI**: Streamlit (with interactive `st.map` and real-time polling)
- **Routing**: NetworkX (Weighted city graph of Delhi NCR)
- **Language**: Python 3.10+

## 📊 Inputs & Outputs

- **Input**: Unstructured Hinglish/English transcripts (e.g., *"Bhai CP mein building collapse ho gayi hai, ambulance bhejo jaldi!"*).
- **Output**: Structured incident objects, real-time resource routing, and plain-English strategic reasoning.
- **UI**: A professional "Control Room" dashboard with a live system feed, priority queue, and resource utilization tracking.

## ⚖️ Constraints & Features

- **100% Free Tools**: Uses Groq (LLM), ngrok (Tunneling), and Streamlit (UI).
- **Hinglish Support**: Natively processes mixed Hindi-English input common in Indian cities.
- **Explainable AI**: Every dispatch decision includes a "Decision / Reasoning / Action Taken" block for full transparency.
- **Scalable State**: Uses LangGraph's state management to handle multi-incident scenarios simultaneously.

## 🚀 How to Run

1. **Setup Environment**:
   ```bash
   pip3 install -r requirements.txt
   cp .env.example .env
   # Add your GROQ_API_KEY and NGROK_AUTH_TOKEN to .env
   ```

2. **Start the Backend**:
   ```bash
   python3 colab_backend.py
   ```
   - This starts the FastAPI server and creates an ngrok tunnel. 
   - Note the **Public URL** generated (e.g., `https://xyz.ngrok.io`).

3. **Start the Dashboard**:
   ```bash
   python3 -m streamlit run ui/dashboard.py
   ```
   - Paste the ngrok URL into the **Connection** sidebar.
   - Click **▶ Start Live Simulation** to see the system autonomously process incoming calls.

## 📂 Project Structure

```text
crisisgrid-ai/
├── agents/
│   ├── triage_agent.py      # Extracting structured JSON from panic calls
│   ├── fusion_agent.py      # De-duplication and conflict resolution
│   ├── dispatch_agent.py    # Pathfinding and unit assignment
│   └── strategy_agent.py    # High-level trade-off logic & rerouting
├── graph/
│   └── workflow.py          # Stateful LangGraph pipeline
├── data/
│   ├── mock_calls.py        # Dataset of 112 emergency transcripts
│   ├── city_graph.py        # NetworkX definition of Delhi NCR zones
│   └── resources.py         # Mock database of ambulances/fire trucks
├── ui/
│   ├── dashboard.py         # Streamlit Control Room UI
│   └── mock_data.py         # UI-specific mock state & icons
├── utils/
│   └── state.py             # LangGraph State Schema
├── colab_backend.py         # FastAPI Entrypoint (Persistence & Simulation)
├── requirements.txt
└── README.md
```

## 🔗 Deployed Link

https://crisisgrid-ai.streamlit.app/
