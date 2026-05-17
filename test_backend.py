import sys
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.state import get_state_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestRunner")

client = TestClient(app)

def run_tests():
    logger.info("Starting Backend Integration Tests...")
    
    # 1. Health Check
    get_state_manager().reset()
    res = client.get("/health")
    assert res.status_code == 200, "Health check failed"
    logger.info("✅ Health check passed")
    
    # 2. Process Call (Full LangGraph execution)
    payload = {
        "transcript": "Emergency! Major accident on the highway, multiple cars involved, people trapped. Send ambulances and rescue teams!"
    }
    logger.info("Testing LLM Pipeline (this may take a few seconds)...")
    res = client.post("/api/v1/incidents/process-call", json=payload)
    assert res.status_code == 200, f"Process call failed: {res.text}"
    data = res.json()
    assert "state" in data
    state = data["state"]
    assert len(state["incidents"]) > 0, "No incidents created"
    logger.info(f"✅ Process call passed. Incident created: {state['incidents'][0]['type']}")
    
    # 3. Traffic endpoint
    res = client.get("/api/v1/traffic")
    assert res.status_code == 200, "Traffic endpoint failed"
    assert "affected_edges" in res.json()
    logger.info("✅ Traffic system passed")
    
    # 4. Reset endpoint
    res = client.post("/api/v1/simulation/reset")
    assert res.status_code == 200
    assert len(get_state_manager().incidents) == 0
    logger.info("✅ Reset endpoint passed")
    
    logger.info("🎉 All backend integration tests passed successfully!")

if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        logger.error(f"❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ UNEXPECTED ERROR: {e}")
        sys.exit(1)
