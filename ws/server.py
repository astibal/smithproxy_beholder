import json
import sys
import threading
from pprint import pprint, pformat

from PyQt5.QtCore import QThread, pyqtSignal, Qt

from flask import Flask, request, jsonify
from ui.state import State

# Create the Flask app
flask_app = Flask(__name__)


class FlaskThread(QThread):
    updated = pyqtSignal(str)  # Signal to update the GUI

    def __init__(self):
        super().__init__()

        @flask_app.route('/api/update', methods=['POST'])
        def update():
            # data = request.get_json(force=True)
            data = request.get_data().decode()

            with State.lock:
                skip_click = State.ui.skip_click

            if not skip_click:
                self.updated.emit(data)  # Emit signal with JSON data
                State.events.button_process.wait()  # Wait for the button to be clicked
                State.events.button_process.clear()  # Reset the event for the next API call

            with State.lock:
                return_data = State.response_data
                return_data["processed"] = False
                return_data["message"] = ""

                return_data = jsonify(return_data)
            # Reset shared data for the next request (optional based on your use case)
            return return_data

        @flask_app.route('/webhook/<string:key>', methods=['POST'])
        def webhook(key: str):

            print(f"== Handler start:")
            # some code to check key string

            # Process the incoming JSON payload
            payload = request.json

            # Replace the below line with your processing logic
            print(f"== Received payload:")
            print(payload)
            print(f"== Pretty:")
            pprint(payload)
            print("==========")

            try:
                if payload["action"] == "access-request":
                    print("::: action - access-request")
                    result = "accept"
                    if "2001:67c:68::76" in payload['details']['session']:
                        result = "reject"

                    return jsonify({
                        "access-response": result
                    }), 200
                if payload["action"] == "connection-content":
                    print("::: action - connection content")

                    reply_body = {
                        "action": "none"
                    }

                    try:
                        reply_body["action"] = "replace"
                        reply_body["content"] = payload['details']['info']['content']

                        with State.lock:
                            wait_for_data = not State.ui.skip_click

                        if wait_for_data:
                            # data = request.get_json(force=True)
                            data = request.get_data().decode()
                            self.updated.emit(data)  # Emit signal with JSON data

                            print("Now waiting for data")
                            State.events.button_process.wait()  # Wait for the button to be clicked
                            State.events.button_process.clear()  # Reset the event for the next API call
                            print("Data received")

                    except KeyError:
                        print("::: error, no 'content'")
                        pass

                    print(f"::: sending {reply_body}")
                    return jsonify(reply_body), 200

            except KeyError as e:
                print(f'KeyError: {e}')
            except Exception as gen_e:
                print(f'General exception: {gen_e}')

            return jsonify({"status": "success"}), 200

    def run(self):
        flask_app.run(port=5000, debug=False, use_reloader=False)
