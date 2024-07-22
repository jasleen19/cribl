import pytest
from app.logs import read_log, search_log
import tempfile
# from contextlib import contextmanager
# import time


def test_read_log_simple_lines():
    content = """First line
Second line
Third line"""

    with tempfile.NamedTemporaryFile(mode="w+") as temp:
        temp.write(content)
        temp.flush()

        content_lines = content.split("\n")

        for i, log in enumerate(read_log(temp.name)):
            assert log == content_lines[~i]

        assert i + 1 == len(content_lines)


def test_read_log_file_ending_with_new_line():
    content = """First line
Second line
Third line
"""

    with tempfile.NamedTemporaryFile(mode="w+") as temp:
        temp.write(content)
        temp.flush()

        content_lines = content.split("\n")

        for i, log in enumerate(read_log(temp.name)):
            if i == 0:
                assert log == ""
            assert log == content_lines[~i]

        assert i + 1 == len(content_lines)


def test_read_log_lines_in_different_chunks():
    content = """First
987654321"""

    with tempfile.NamedTemporaryFile(mode="w+") as temp:
        temp.write(content)
        temp.flush()

        content_lines = content.split("\n")

        for i, log in enumerate(read_log(temp.name, chunk_size=7)):
            assert log == content_lines[~i]

        assert i + 1 == len(content_lines)


def test_read_log_no_lines_early_exit():
    content = """abc this is a text file without any split lines. bla bla bla
"""
    with tempfile.NamedTemporaryFile(mode="w+") as temp:
        temp.write(content)
        temp.flush()

        with pytest.raises(TypeError) as exc_info:
            for _ in read_log(temp.name, chunk_size=4, max_chunks_without_lines=2):
                pass
        assert "without split lines" in str(exc_info.value)


def test_search_log_n_lines():
    content = """First line
Second line
Third line
line 4
line 5
line 6
line 7
line 8
line 9
"""

    with tempfile.NamedTemporaryFile(mode="w+") as temp:
        temp.write(content)
        temp.flush()

        content_lines = content.split("\n")

        n = 3
        for i, log in enumerate(search_log(temp.name, n=n)):
            assert log == content_lines[~i]

        assert i + 1 == n


def test_search_log_search_keyword():
    content = """First Line
Second line
Third Line
line 4
line 5
line 6
line 7
line 8
line 9
"""

    with tempfile.NamedTemporaryFile(mode="w+") as temp:
        temp.write(content)
        temp.flush()

        for i, log in enumerate(search_log(temp.name, keyword="Line")):
            assert "Line" in log

        assert i + 1 == 2  # [First Line, Third Line]


def test_search_log_n_and_search_keyword():
    content = """First Line
Second line
Third Line
line 4
line 5
line 6
line 7
line 8
line 9
"""

    with tempfile.NamedTemporaryFile(mode="w+") as temp:
        temp.write(content)
        temp.flush()

        for i, log in enumerate(search_log(temp.name, keyword="line", n=4)):
            assert "line" in log

        assert i + 1 == 4


def test_search_log_missing_file_fails():
    with pytest.raises(FileNotFoundError) as exc_info:
        next(search_log(""))

    assert "No such file or directory" in str(exc_info.value)


# # NOTE: Only run for performance testing as this will create a giant file.
# def test_read_log_large_file():
#     @contextmanager
#     def timer():
#         start_time = time.time()
#         yield
#         end_time = time.time()
#         elapsed_time = end_time - start_time
#         print(f"Elapsed time: {elapsed_time} seconds")

#     two_gb_file = 2 * 1024 * 1024 * 1024
#     max_line_length = 100
#     dummy_line = "a" * (max_line_length - 1) + "\n"  # 99 'a' characters followed by a newline
#     num_lines = two_gb_file // len(dummy_line)  # Total number of lines needed

#     with tempfile.NamedTemporaryFile(mode="w+") as temp:
#         for _ in range(num_lines):
#             temp.write(dummy_line)
#         temp.flush()

#         four_mb_chunk = 4 * 1024 * 1024
#         with timer():  # takes 5 secs :)
#             assert (
#                 len([_ for _ in read_log(temp.name, chunk_size=four_mb_chunk)]) == num_lines + 1
#             )  # due to last newline
