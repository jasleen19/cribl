from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from app.logs import search_log, find_log
from typing import Iterator
import os
import httpx
from httpx import ReadTimeout

secondaries = os.getenv("secondaries", "")
SECONDARIES: set[str] = {s for s in secondaries.split(",") if s}
app = FastAPI()

if SECONDARIES:

    def get_logs_from_secondary(
        secondary: str,
        filename: str,
        keyword: str | None = None,
        n: int | None = None,
    ):
        params = {"filename": filename}
        if n:
            params["n"] = n
        if keyword:
            params["keyword"] = keyword
        try:
            with httpx.stream(
                "GET",
                f"http://{secondary}:8000/logs",
                params=params,
            ) as r:
                for text in r.iter_text():
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

    def get_logs(
        log_file: str,
        keyword: str | None,
        n: str | None,
    ) -> Iterator[str]:
        try:
            for log in search_log(log_file, keyword, n):
                yield log + "\n"
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
