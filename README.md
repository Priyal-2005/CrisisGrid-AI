# CrisisGrid AI

An intelligent, multi-agent emergency dispatch system powered by **LangGraph**, **FastAPI**, **Next.js 15**, and **NetworkX**. 

CrisisGrid AI simulates a real-time smart city command center that autonomously triages 112 calls, merges duplicate reports, calculates dynamic severity scores (0-100), allocates resources, and reroutes units based on active traffic conditions. It features a modern, high-performance EOC (Emergency Operations Center) dashboard.

---

## Architecture Overview

The system operates on a highly scalable, decoupled full-stack architecture:

### 1. The Intelligence & Infrastructure Layer (FastAPI + LangGraph)
- **Triage Agent**: Parses raw transcripts, extracts hazmat/trapped data, and maps incident types.
- **Fusion Agent**: Correlates multiple calls into single incidents, merging intelligence and calculating dynamic severity (0-100) based on 10 risk factors.
- **Dispatch Agent**: Allocates multi-resource packages (e.g., 3 fire trucks + 2 ambulances) and executes dynamic rerouting (pulling units from LOW to CRITICAL incidents).
- **Strategy Agent**: Evaluates cascading disaster risks based on infrastructure profiles and justifies resource shortages.
- **City Graph Engine**: A NetworkX directed graph that inflates ETAs based on active incidents, roadblocks, and flood zones.
- **State & WebSocket Managers**: Thread-safe persistent memory that streams live dispatch events, incident updates, and agent reasoning to connected clients.

### 2. The Presentation Layer (Next.js 15 App Router)
- **Realtime Dashboard**: A high-density, dark-mode SOC (Security Operations Center) dashboard built with TailwindCSS and shadcn/ui.
- **State Synchronization**: Client-side state managed entirely by **Zustand**, perfectly mirroring the backend's data models via auto-reconnecting WebSockets.
- **Dynamic Map Visualization**: Realtime Leaflet maps plotting pulsing incidents and active, animating dispatch routes.
- **Live Reasoning Stream**: A terminal-style console displaying the continuous LLM thoughts of the LangGraph agents.

---

## Getting Started

### 1. Prerequisites
- **Backend**: Python 3.10+
- **Frontend**: Node.js 18+ & npm
- A **Groq API key** for the LLM agents (`llama-3.3-70b-versatile`)

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/crisisgrid-ai.git
cd crisisgrid-ai

# Install Python dependencies
pip3 install -r requirements.txt
```

Create a `.env` file in the root directory:
```env
# ── API Keys ──
GROQ_API_KEY=your_groq_api_key_here

# ── Backend Settings ──
HOST=0.0.0.0
PORT=8000
DEBUG=false
ENV=production
CORS_ORIGINS=*
```

Start the production FastAPI backend:
```bash
python3 run_server.py
```
The API runs at `http://localhost:8000`. Swagger documentation is at `http://localhost:8000/docs`.

### 3. Frontend Setup
Open a new terminal window:
```bash
cd frontend

# Install Node dependencies
npm install

# Start the Next.js development server
npm run dev
```
The EOC Dashboard runs at `http://localhost:3000`.

---

## Testing the AI Simulation

CrisisGrid comes with a built-in scenario runner to demonstrate its intelligence (merging, escalation, and strategic rerouting).

You can trigger the scenario directly from the **Simulation Controls** panel on the Next.js frontend dashboard, or via cURL:

```bash
curl -X POST "http://localhost:8000/api/v1/simulation/scenario" \
     -H "Content-Type: application/json" \
     -d '{"delay": 1.5}'
```

Watch the dashboard as the Triage Agent parses 6 rapid, complex emergency calls, the Fusion Agent escalates severity when duplicate calls hit the same sector, and the Dispatch Agent dynamically pulls an ambulance off a minor incident to route it to a critical chemical explosion.

---

## 🔗 Deployment
- **Backend**: Ready for Render / Railway via `run_server.py`. Ensure `CORS_ORIGINS` points to your frontend.
- **Frontend**: Ready for Vercel. Ensure `NEXT_PUBLIC_WS_URL` and `NEXT_PUBLIC_API_URL` point to your deployed backend domain (using `wss://` for secure WebSockets).
