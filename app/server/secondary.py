from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from app.logs import search_log, find_log
import os


DEMO_SLOW_STREAM = os.getenv("DEMO_SLOW_STREAM", "false")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def healthcheck():
    return {"detail": "ok"}


@app.get("/logs")
async def logs_handler(
    filename: str,
    keyword: str | None = None,
    n: int | None = None,
):
    try:
        log_file = find_log(filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return StreamingResponse(
        search_log(log_path=log_file, keyword=keyword, n=n),
        media_type="text/plain",
    )
