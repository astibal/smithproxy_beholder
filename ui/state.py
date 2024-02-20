import threading

from PyQt5 import QtCore

from util.bidict import BiDict


class Global:
    lock = threading.RLock()
    storage = {}
    samples = {1: None, 2: None, 3: None}

class State:
    # Shared data structure for response
    response_data = {"processed": False, "message": ""}
    lock = threading.Lock()

    class StateEvents(QtCore.QObject):
        # Shared event for button click signaling
        button_process = threading.Event()
        received_session_start = QtCore.pyqtSignal(str, str)
        received_session_stop = QtCore.pyqtSignal(str, str)

    events = StateEvents()

    class ui:
        # should we just ignore everything and let webhooks flow with default answers
        skip_click: bool = True
        #
        autorun: bool = False

        class content_tab:
            session_id: str = None
            session_label: str = None

            # content bytes received
            content_data: bytes = None
            content_data_last: bytes = None
            content_side: str = None
            content_replacement: bytes = None

            current_script_slot: int = 1

    class sessions:
        sessions = BiDict()
