import threading

class State:
    # Shared data structure for response
    response_data = {"processed": False, "message": ""}
    lock = threading.Lock()

    class events:
        # Shared event for button click signaling
        button_process = threading.Event()

    class ui:

        # should we just ignore everything and let webhooks flow with default answers
        skip_click = True
        # content bytes received
        content_data = None
