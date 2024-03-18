import base64
import json
import logging
import ssl
from pprint import pformat
import traceback
from typing import AnyStr

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from flask import Flask, request, jsonify, abort

from ui.state import State
from ui.config import Config

log = logging.getLogger()

class FlaskThread(QThread):
    # Create the Flask app
    app = None
    received_content = pyqtSignal(str)  # Signal to update content data

    def __init__(self):
        super().__init__()

        # FlaskThread.app.logger.handlers = []
        wzlog = logging.getLogger('werkzeug')
        wzlog.propagate = False
        wzlog.handlers = []
        wzlog.setLevel("ERROR")

        FlaskThread.app = Flask(__name__)
        FlaskThread.app.logger.handlers = []
        FlaskThread.app.logger.setLevel("ERROR")

        @FlaskThread.app.route('/stream-updates/<string:key>', methods=['POST'])
        def stream(key: str):
            with Config.lock:
                api_key = Config.config["api_key"]

            if 'Transfer-Encoding' not in request.headers or \
                    'chunked' not in request.headers['Transfer-Encoding']:
                abort(411)

            if api_key and key != api_key:
                log.error(f"Invalid API key {key}")
                abort(400)

            while True:
                # First read the chunk size (in hex)
                chunk_size = request.stream.readline()
                if chunk_size == b'':
                    return jsonify({"status": "success"})

                # Convert chunk size from hex to int
                chunk_size = int(chunk_size, 16)

                # Read the chunk data of `chunk_size` length
                chunk_data = request.stream.read(chunk_size)

                # Skip the trailing `\r\n` after the chunk data
                request.stream.read(2)

                self.process_stream_update(chunk_data)

        @FlaskThread.app.route('/webhook/<string:key>', methods=['POST'])
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
            log.debug(f"== Received payload:")
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

                elif payload["action"] == "connection-info":
                    return self.process_connection_info(payload)

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

    def get_action_retcode(self, code):
        if 200 <= code < 300:
            if State.ui.request_ping_plus:
                State.ui.request_ping_plus = False
                return 202
        return code

    def process_access_request(self, payload):

        session_label = payload["details"]["session"]
        log.info(f"::: action - access-request - {session_label}")

        result = "accept"
        if "2001:67c:68::76" in payload['details']['session']:
            result = "reject"

        return jsonify({
            "access-response": result
        }), 200

    def process_connection_content(self, payload):
        session_label = payload["details"]["info"]["session"]
        log.info(f"::: action - connection content - {session_label}")

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
        log.info(f"::: action - connection start - {session_label}")

        session_id = payload["id"]

        with State.lock:
            State.sessions.sessions.insert(session_id, session_label)
            log.debug("session map:")
            log.debug(str(State.sessions.sessions.forward))
            log.debug(str(State.sessions.sessions.inverse))

        State.events.received_session_start.emit(session_id, session_label, json.dumps(payload))

        return jsonify({}), self.get_action_retcode(200)

    def process_connection_stop(self, payload):
        session_label = payload["details"]["info"]["session"]
        log.info(f"::: action - connection stop - {session_label}")

        session_id = payload["id"]
        with State.lock:
            State.sessions.sessions.remove(session_id)
            log.debug("session map:")
            log.debug(str(State.sessions.sessions.forward))
            log.debug(str(State.sessions.sessions.inverse))

        State.events.received_session_stop.emit(session_id, session_label, json.dumps(payload))

        return jsonify({}), self.get_action_retcode(200)

    def process_connection_info(self, payload):
        session_id = payload["id"]
        log.info(f"::: action - connection info - {session_id}")

        with State.lock:
            log.debug("session map:")
            log.debug(str(State.sessions.sessions.forward))
            log.debug(str(State.sessions.sessions.inverse))

        State.events.received_session_info.emit(session_id, None, json.dumps(payload))

        return jsonify({}), self.get_action_retcode(200)

    def process_ping(self, payload):
        log.info("::: action - ping")

        with State.lock:
            to_rem = []
            for id in State.sessions.sessions.forward:
                if payload['proxies'] and not id in payload['proxies']:
                    to_rem.append(id)

            for id in to_rem:
                log.debug(f"proxy {id} removed (ping)")
                State.sessions.sessions.remove(id)

            try:
                if payload['proxies-plus']:
                    log.info("ping-plus received")
                    for tup in payload['proxies-plus']:
                        tup = tup.split('=')
                        if len(tup) == 2 and tup[0] and not State.sessions.sessions.forward.get(tup[0]):
                            State.sessions.sessions.insert(tup[0], tup[1])
                            log.debug(f"proxy {tup[0]} + {tup[1]} added (ping-plus)")
            except KeyError:
                pass

        State.events.received_ping.emit()

        return jsonify({}), 200

    def process_stream_update(self, chunk_data: AnyStr):
        log.info(f'stream-update: {len(chunk_data)}B received: {str(chunk_data)}')

    def run(self):
        with Config.lock:
            port = Config.config["port"]
            addr = Config.config["address"]
            tlsctx = Config.ssl_context

        fallback = False
        if tlsctx:
            try:
                FlaskThread.app.run(host=addr, port=port, debug=False, use_reloader=False, ssl_context=tlsctx)
            except ssl.SSLError as e:
                log.error(f"TLS error when starting server: {e}")
                fallback = True

        if not tlsctx or fallback:
            FlaskThread.app.run(host=addr, port=port, debug=False, use_reloader=False)

