import hashlib
import ssl
import threading

from PyQt5 import QtCore

from util.bidict import BiDict


class Global:
    lock = threading.RLock()
    storage = {}
    samples = {1: None, 2: None, 3: None}
    samples_metadata = {1: {}, 2: {}, 3: {}}

class State:
    # Shared data structure for response
    response_data = {"processed": False, "message": ""}
    lock = threading.Lock()


    class auth:
        dynamic_data = {}  # token -> identity string (for future use)
        dynamic_token = []
        MAX_TOKENS = 200
        @staticmethod
        def register(identity) -> str:
            rand = ssl.RAND_bytes(32)
            hashed = hashlib.sha256(rand)
            hashed = hashed.hexdigest()
            State.auth.dynamic_data[hashed] = identity
            State.auth.dynamic_token.append(hashed)

            if len(State.auth.dynamic_token) > State.auth.MAX_TOKENS:
                State.auth.dynamic_token.pop(0)
                del State.auth.dynamic_data[hashed]

            return hashed

        @staticmethod
        def validate_token(tok: str) -> bool:
            return tok in State.auth.dynamic_token


    class StateEvents(QtCore.QObject):
        # Shared event for button click signaling
        button_process = threading.Event()
        received_session_start = QtCore.pyqtSignal(str, str, str)
        received_session_stop = QtCore.pyqtSignal(str, str, str)
        received_session_info = QtCore.pyqtSignal(str, str, str)
        received_ping = QtCore.pyqtSignal()
        click_1s = QtCore.pyqtSignal()

    events = StateEvents()

    class ui:
        # should we just ignore everything and let webhooks flow with default answers
        skip_click: bool = True
        request_ping_plus = True

        class content_tab:
            autorun: bool = False

            session_id: str = None
            session_label: str = None

            # content bytes received
            content_data: bytes = None
            content_data_last: bytes = None
            content_side: str = None
            content_replacement: bytes = None

            current_script_slot: int = 1

        class workbench_tab:
            current_script_slot: int = 1
            autorun: bool = False
            current_sample = None
            current_sample_key = 1
            current_output = None

    class sessions:
        sessions = BiDict()
