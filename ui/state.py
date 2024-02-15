import threading
from util.bidict import BiDict
from PyQt5 import QtCore


class Global:
    lock = threading.RLock()
    storage = {}

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
            session_id: str
            session_label: str

            # content bytes received
            content_data: bytes = None
            content_side: str
            content_replacement: bytes = None

    class sessions:
        sessions = BiDict()
