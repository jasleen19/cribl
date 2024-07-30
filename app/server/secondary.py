from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from app.logs import search_log, find_log
from typing import Callable
import httpx
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import asyncio
import time
import os


DEMO_SLOW_STREAM = os.getenv("DEMO_SLOW_STREAM", "false")
DEFAULT_CHUNK_SIZE = 1024**3  # 1 MB
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


def data_producer(
    q: Queue,
    fn: Callable,
    *args,
    **kwargs,
) -> None:
    try:
        for data in fn(*args, **kwargs):
            if DEMO_SLOW_STREAM == "true":
                time.sleep(1)
                print("File pointer")
            q.put(data)
    except TypeError as e:
        q.put(f"Error during streaming: {str(e)}")
    finally:
        q.put(None)


def data_consumer(
    q: Queue,
):
    while True:
        data = q.get()
        if DEMO_SLOW_STREAM == "true":
            print("Secondary")
        if data is None:
            break

        yield data + "\n"


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

    q = Queue()

    asyncio.get_running_loop().run_in_executor(
        thread_pool_exc,
        data_producer,
        q,
        search_log,
        log_file,
        keyword,
        n,
    )

    return StreamingResponse(
        data_consumer(
            q,
        ),
        media_type="text/plain",
    )
