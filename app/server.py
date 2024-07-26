from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from app.logs import search_log, find_log
from typing import AsyncGenerator, Callable
import os
import httpx
from httpx import ReadTimeout
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import asyncio
import time

DEMO_SLOW_STREAM = os.getenv("DEMO_SLOW_STREAM", "false")
SECONDARIES_ENV = os.getenv("SECONDARIES", "")
SECONDARIES: set[str] = {s for s in SECONDARIES_ENV.split(",") if s}

DEFAULT_CHUNK_SIZE = 10

thread_pool_exc = ThreadPoolExecutor(max_workers=4)


client = httpx.AsyncClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    print("Shutting down thread pool executor...")
    thread_pool_exc.shutdown(wait=True)


app = FastAPI(lifespan=lifespan)


if SECONDARIES:

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
                    f"http://{secondary}/logs",
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
else:

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
