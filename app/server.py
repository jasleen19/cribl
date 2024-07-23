from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from app.logs import search_log, find_log
from typing import AsyncGenerator
import os
import httpx
from httpx import ReadTimeout
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Thread pool with same number of workers as CPU cores
thread_pool_exc = ThreadPoolExecutor()

secondaries = os.getenv("secondaries", "")
SECONDARIES: set[str] = {s for s in secondaries.split(",") if s}
app = FastAPI()

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
                    async for text in r.aiter_text():
                        yield text
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

    async def get_logs(
        log_file: str,
        keyword: str | None,
        n: str | None,
    ) -> AsyncGenerator[str, None]:
        try:
            # Reading file is a IO blocking operation and doesn't work well with asyncio
            # so we use a thread pool executor to run it in a separate thread to
            # avoid blocking the main thread which is running the event loop
            lines = await asyncio.get_event_loop().run_in_executor(thread_pool_exc, search_log, log_file, keyword, n)
            for line in lines:
                yield line + "\n"
        except TypeError as e:
            yield f"Error during streaming: {str(e)}"
            # https://github.com/encode/starlette/discussions/1739#discussioncomment-3094935
            # Starlette (used by FastAPI) does not support HTTP response trailers.
            return

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
            get_logs(
                log_file,
                keyword,
                n,
            ),
            media_type="text/plain",
        )
