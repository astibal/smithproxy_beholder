import sys
import re
from contextlib import contextmanager

class CharFilter:
    # Class attributes storing regex patterns
    ALPHANUMERIC_REGEX = r'[^a-zA-Z0-9]'
    FILENAME_REGEX = r'[^a-zA-Z0-9_.-]'
    BASE_FILENAME_REGEX = r'[\\/]|(\.\.)'
    EMAIL_REGEX = r'[^a-zA-Z0-9@._-]'
    USERNAME_REGEX = r'[^a-zA-Z0-9_]'

    @staticmethod
    def alphanumeric(input_string: str, replacement=None) -> str:
        repl = replacement or ''
        return re.sub(CharFilter.ALPHANUMERIC_REGEX, repl, input_string)

    @staticmethod
    def filename(input_string: str, replacement=None) -> str:
        repl = replacement or ''
        return re.sub(CharFilter.FILENAME_REGEX, repl, input_string)

    @staticmethod
    def base_filename(input_string: str, replacement=None) -> str:
        repl = replacement or ''
        sanitized = re.sub(CharFilter.BASE_FILENAME_REGEX, repl, input_string)
        return CharFilter.filename(sanitized, replacement=repl)

    @staticmethod
    def email(input_string: str, replacement=None) -> str:
        repl = replacement or ''
        return re.sub(CharFilter.EMAIL_REGEX, repl, input_string)

    @staticmethod
    def username(input_string: str, replacement=None) -> str:
        repl = replacement or ''
        return re.sub(CharFilter.USERNAME_REGEX, repl, input_string)

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