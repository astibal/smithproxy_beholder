import base64
import logging
import ssl
from pprint import pformat
import traceback

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from flask import Flask, request, jsonify

from ui.state import State
from ui.config import Config

log = logging.getLogger(__name__)

# Create the Flask app
flask_app = Flask(__name__)


class FlaskThread(QThread):
    received_content = pyqtSignal(str)  # Signal to update content data

    def __init__(self):
        super().__init__()

        @flask_app.route('/webhook/<string:key>', methods=['POST'])
        def webhook(key: str):

            with Config.lock:
                api_key = Config.config["api_key"]

            if api_key and key != api_key:
                log.error(f"Invalid API key {key}")
                return jsonify({"error": "Invalid API key"}), 400

            log.debug(f"== Handler start:")
            # some code to check key string

            # Process the incoming JSON payload
            payload = request.json

            # Replace the below line with your processing logic
            log.info(f"== Received payload:")
            log.debug(payload)
            log.debug(f"== Pretty:")
            log.debug(pformat(payload))
            log.debug("==========")

            try:
                if payload["action"] == "access-request":
                    return self.process_access_request(payload)

                elif payload["action"] == "connection-content":
                    return self.process_connection_content(payload)

                elif payload["action"] == "connection-start":
                    return self.process_connection_start(payload)

                elif payload["action"] == "connection-stop":
                    return self.process_connection_stop(payload)

                elif payload["action"] == "ping":
                    return self.process_ping(payload)


            except KeyError as e:
                log.error(f'KeyError: {e}')
                exception_traceback = traceback.format_exc()
                log.debug(exception_traceback)

            except Exception as gen_e:
                log.error(f'General exception: {gen_e}')
                exception_traceback = traceback.format_exc()
                log.debug(exception_traceback)

            return jsonify({"status": "success"}), 200

    def process_access_request(self, payload):
        log.debug("::: action - access-request")
        result = "accept"
        if "2001:67c:68::76" in payload['details']['session']:
            result = "reject"

        return jsonify({
            "access-response": result
        }), 200

    def process_connection_content(self, payload):
        log.debug("::: action - connection content")

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
                self.received_content.emit(data)  # Emit signal with JSON data

                log.debug("Now waiting for data")
                State.events.button_process.wait()  # Wait for the button to be clicked
                State.events.button_process.clear()  # Reset the event for the next API call
                log.debug("Data received")

                with State.lock:

                    cont = State.ui.content_tab.content_replacement
                    if cont:
                        if isinstance(cont, str):
                            log.debug(f"custom replacement detected: {len(cont)}B")
                            cont = bytes(cont, 'utf-8')

                        if isinstance(cont, bytes):
                            reply_body["content"] = base64.b64encode(cont).decode()
                        else:
                            log.error("replacement not 'bytes' or 'str'")

                        State.ui.content_tab.content_replacement = None

        except KeyError:
            log.error("::: error, no 'content'")
            pass

        log.debug(f"::: sending {reply_body}")
        return jsonify(reply_body), 200

    def process_connection_start(self, payload):

        session_label = payload["details"]["info"]["session"]
        session_id = payload["id"]

        with State.lock:
            State.sessions.sessions.insert(session_id, session_label)
            log.debug("session map:")
            log.debug(str(State.sessions.sessions.forward))
            log.debug(str(State.sessions.sessions.inverse))

        State.events.received_session_start.emit(session_id, session_label)

        return jsonify({}), 200

    def process_connection_stop(self, payload):

        session_label = payload["details"]["info"]["session"]
        session_id = payload["id"]
        with State.lock:
            State.sessions.sessions.remove(session_id)
            log.debug("session map:")
            log.debug(str(State.sessions.sessions.forward))
            log.debug(str(State.sessions.sessions.inverse))

        State.events.received_session_stop.emit(session_id, session_label)

        return jsonify({}), 200

    def process_ping(self, payload):

        with State.lock:
            to_rem = []
            for id in State.sessions.sessions.forward:
                if payload['proxies'] and not id in payload['proxies']:
                    to_rem.append(id)

            for id in to_rem:
                log.debug(f"proxy {id} removed (ping)")
                State.sessions.sessions.remove(id)

        return jsonify({}), 200

    def run(self):
        with Config.lock:
            port = Config.config["port"]
            addr = Config.config["address"]
            tlsctx = Config.ssl_context

        fallback = False
        if tlsctx:
            try:
                flask_app.run(host=addr, port=port, debug=False, use_reloader=False, ssl_context=tlsctx)
            except ssl.SSLError as e:
                log.error(f"TLS error when starting server: {e}")
                fallback = True

        if not tlsctx or fallback:
            flask_app.run(host=addr, port=port, debug=False, use_reloader=False)

