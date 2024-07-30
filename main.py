from app.server.primary import app as primary_app
from app.server.secondary import app as secondary_app
import uvicorn
import os


SECONDARIES_ENV = os.getenv("SECONDARIES", "")
SECONDARIES: set[str] = {s for s in SECONDARIES_ENV.split(",") if s}

if __name__ == "__main__":
    app = primary_app if SECONDARIES else secondary_app
    uvicorn.run(app, host="0.0.0.0", port=8000)
