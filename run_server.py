import os
import sys
import uvicorn
import logging
from dotenv import load_dotenv

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.core.config import get_settings

if __name__ == "__main__":
    load_dotenv()
    settings = get_settings()
    
    print("=" * 60)
    print(f"🚨 {settings.PROJECT_NAME} Backend")
    print(f"🌐 Server starting on http://{settings.HOST}:{settings.PORT}")
    print(f"📖 API Docs available at http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 60)
    
    uvicorn.run(
        "backend.main:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )
