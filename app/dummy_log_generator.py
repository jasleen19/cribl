def generate_data(size):
    """Generate a chunk of repetitive data of a given size in bytes with newlines."""
    line = "This is a log entry\n"
    repeated_data = (line * (size // len(line) + 1))[:size]
    return repeated_data.encode("utf-8")


def create_large_log_file(filepath, target_size_gb, chunk_size_mb=10):
    """Create a large log file with repetitive data in larger chunks."""
    target_size_bytes = target_size_gb * 1024**3
    chunk_size_bytes = chunk_size_mb * 1024**2
    current_size = 0
    i = 0
    with open(filepath, "wb") as file:
        while current_size < target_size_bytes:
            # Generate a chunk of repetitive data
            chunk = generate_data(chunk_size_bytes)
            file.write(chunk)
            current_size += len(chunk)
            if current_size % (1024**2) == 0:  # Print progress every MB
                print(f"Written {current_size / (1024**2):.2f} MB")

    print(f"File {filepath} created with size {target_size_gb} GB")


# Ensure /var/log is writable or change the path to a directory where you have write access
log_file_path = "/var/log/dummy.log"
create_large_log_file(log_file_path, 1)
