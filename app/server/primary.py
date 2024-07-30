from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import httpx
from httpx import ReadTimeout
from concurrent.futures import ThreadPoolExecutor
import os


DEMO_SLOW_STREAM = os.getenv("DEMO_SLOW_STREAM", "false")
DEFAULT_CHUNK_SIZE = 1024**3  # 1 MB
SECONDARIES_ENV = os.getenv("SECONDARIES", "")
SECONDARIES: set[str] = {s for s in SECONDARIES_ENV.split(",") if s}

thread_pool_exc = ThreadPoolExecutor(max_workers=4)


client = httpx.AsyncClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    print("Shutting down thread pool executor...")
    thread_pool_exc.shutdown(wait=True)


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def healthcheck():
    return {"detail": "ok"}


async def get_logs_from_secondary(
    secondary: str,
    filename: str,
    keyword: str | None = None,
    n: int | None = None,
) -> AsyncGenerator[str, None]:
    params = {"filename": filename}
    if n:
        params["n"] = n
    if keyword:
        params["keyword"] = keyword
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"https://{secondary}/logs",
                params=params,
            ) as r:
                async for line in r.aiter_lines():
                    if DEMO_SLOW_STREAM == "true":
                        print("Primary")
                    yield line + "\n"
    except ReadTimeout as e:
        yield f"Error during streaming: {str(e)}"
        # https://github.com/encode/starlette/discussions/1739#discussioncomment-3094935
        # Starlette (used by FastAPI) does not support HTTP response trailers.
        return


@app.get("/logs")
async def logs_handler(
    hostname: str,
    filename: str,
    keyword: str | None = None,
    n: int | None = None,
):
    if not hostname or hostname not in SECONDARIES:
        raise HTTPException(status_code=400, detail="Invaid hostname")
    if not filename:
        raise HTTPException(status_code=400, detail="Invaid filename")

    return StreamingResponse(
        get_logs_from_secondary(
            hostname,
            filename=filename,
            keyword=keyword,
            n=n,
        ),
        media_type="text/plain",
    )
