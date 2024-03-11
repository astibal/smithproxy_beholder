import sys
import re
from contextlib import contextmanager

def session_tuple(value: str):
    pattern = r"(?:.*_)?([\d.:a-fA-F]+):(\d+)"
    pattern = pattern + r"\+" + pattern
    match = re.search(pattern, value)

    if match:
        return match.groups()
    else:
        return None

def print_bytes(input_bytes):
    ret = ""
    for i in range(0, len(input_bytes), 16):
        slice = input_bytes[i:i + 16]
        hex_bytes = ' '.join(f'{b:02x}' for b in slice)
        hex_bytes = hex_bytes.ljust(16 * 3)  # each byte becomes 'xy ' so 3 chars long
        ascii_repr = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in slice)
        ret += f'{i:04x}: {hex_bytes} | {ascii_repr}\n'
    return ret

@contextmanager
def capture_stdout_as_string():
    import io
    old_stdout = sys.stdout  # Save the current stdout
    sys.stdout = io.StringIO()  # Redirect stdout to a StringIO object
    yield sys.stdout
    sys.stdout = old_stdout  # Restore stdout