from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from app.logs import search_log, find_log
from typing import Iterator

app = FastAPI()


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
