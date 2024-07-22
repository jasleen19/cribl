from typing import Iterator
import os

DEFAULT_CHUNK_SIZE = 1024**3  # 1 MB
DEFAULT_LOGS_DIR = "/var/log"
MAX_NUM_CHUNKS_WIHOUT_LINES = 10


def find_log(filename: str, log_dir: str = DEFAULT_LOGS_DIR) -> str:
    if not filename:
        raise ValueError("Filename is missing")

    log_path = os.path.join(log_dir, filename)
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Log file does not exist: {log_path}")

    return log_path


def search_log(
    log_path: str,
    keyword: str | None = None,
    n: int | None = None,
) -> Iterator[str]:
    for log in read_log(log_path):
        if keyword is not None and keyword not in log:
            continue

        if n is not None:
            if n == 0:
                return
            n -= 1

        yield log


def read_log(
    filepath: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    max_chunks_without_lines: int = MAX_NUM_CHUNKS_WIHOUT_LINES,
) -> Iterator[str]:
    with open(filepath, "rb") as f:
        f.seek(0, 2)  # Move the cursor to the end of the file
        file_size = f.tell()
        remainder = b""
        counter = 0
        while file_size > 0:
            chunk_size = min(chunk_size, file_size)  # Ensure we don't read beyond the file's start
            file_size -= chunk_size
            f.seek(file_size)
            chunk = f.read(chunk_size)

            # If there was a remainder from the previous chunk, add it to the current chunk
            chunk += remainder

            # Split the chunk into lines
            lines = chunk.split(b"\n")

            # The first element could be the remainder that did not complete a line
            remainder = lines.pop(0)

            if not lines:
                counter += 1
            else:
                counter = 0

            # Chunks were read with no lines found, it could be a binary file that could overflow our memory
            if counter >= max_chunks_without_lines:
                raise TypeError("Encountered a file without split lines")

            # Process the lines in reverse order, except for the remainder part
            for line in reversed(lines):
                yield line.decode("utf-8")

        # After exiting the loop, yield the remainder if there is any
        if remainder:
            yield remainder.decode("utf-8")
