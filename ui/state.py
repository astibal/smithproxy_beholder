import threading

class State:
    # Shared data structure for response
    response_data = {"processed": False, "message": ""}
    lock = threading.Lock()

    class events:
        # Shared event for button click signaling
        button_process = threading.Event()

    class ui:
        skip_click = True
