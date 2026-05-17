# CrisisGrid AI

An intelligent, multi-agent emergency dispatch system powered by **LangGraph**, **FastAPI**, and **NetworkX**. 

CrisisGrid AI simulates a real-time smart city command center that autonomously triages 112 calls, merges duplicate reports, calculates dynamic severity scores (0-100), allocates resources, and reroutes units based on active traffic conditions.

---

## Architecture Overview

The system operates on a dual-layer architecture:

### 1. The Intelligence Layer (LangGraph Multi-Agent System)
- **Triage Agent**: Parses raw transcripts, extracts hazmat/trapped data, and maps incident types.
- **Fusion Agent**: Correlates multiple calls into single incidents, merging intelligence and calculating dynamic severity (0-100) based on 10 risk factors.
- **Dispatch Agent**: Allocates multi-resource packages (e.g., 3 fire trucks + 2 ambulances) and executes dynamic rerouting (pulling units from LOW to CRITICAL incidents).
- **Strategy Agent**: Evaluates cascading disaster risks based on infrastructure profiles and justifies resource shortages.
- **City Graph Engine**: A NetworkX directed graph that inflates ETAs based on active incidents, roadblocks, and flood zones.

### 2. The Infrastructure Layer (FastAPI Production Backend)
- **State Manager**: Thread-safe persistent memory across all calls.
- **WebSocket Manager**: Streams live dispatch events, incident updates, and agent reasoning to connected clients.
- **REST API**: Production-grade Pydantic-validated endpoints for call processing, scenario simulation, and system health.

---

## Getting Started

### 1. Prerequisites
- Python 3.10+
- A Groq API key for the LLM agents (`llama-3.3-70b-versatile`)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/crisisgrid-ai.git
cd crisisgrid-ai

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_api_key_here

# Optional Backend Settings
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

### 4. Running the Server

Start the production FastAPI backend using Uvicorn:

```bash
python run_server.py
```

The API will be available at `http://localhost:8000`.
Interactive Swagger documentation is at `http://localhost:8000/docs`.

---

## API & Simulation

### WebSocket Feed
Connect to `ws://localhost:8000/ws` to receive live system updates:
- `state_snapshot`: Sent on initial connection.
- `incident`: Broadcast when severity or resources change.
- `dispatch`: Broadcast when units are routed.
- `feed`: Human-readable live event stream.

### Running Test Scenarios
CrisisGrid comes with a built-in scenario runner to demonstrate its intelligence (merging, escalation, and strategic rerouting).

Trigger a scenario via cURL or the Swagger UI:
```bash
curl -X POST "http://localhost:8000/api/v1/simulation/scenario" \
     -H "Content-Type: application/json" \
     -d '{"delay": 1.5}'
```

### Process Custom Calls
```bash
curl -X POST "http://localhost:8000/api/v1/incidents/process-call" \
     -H "Content-Type: application/json" \
     -d '{"transcript": "There is a massive fire at the industrial plant, chemical smell everywhere!"}'
```