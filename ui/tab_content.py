import base64
import copy
import json
import sys
import functools

from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QWidget, QTextEdit, QSplitter, \
    QHBoxLayout, QCheckBox, QLabel, QShortcut
from PyQt5.QtGui import QKeySequence
from util.fonts import load_font_prog

try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython
except ImportError:
    print("This app requires Scintilla")
    print("Ubuntu: apt-get install python3-pyqt5.qsci")
    sys.exit(1)

from contextlib import contextmanager

import ws.server
from .state import State, Global
from .config import Config

import logging
log = logging.getLogger()

@contextmanager
def capture_stdout_as_string():
    import io
    old_stdout = sys.stdout  # Save the current stdout
    sys.stdout = io.StringIO()  # Redirect stdout to a StringIO object
    yield sys.stdout
    sys.stdout = old_stdout  # Restore stdout


def print_bytes(input_bytes):
    ret = ""
    for i in range(0, len(input_bytes), 16):
        slice = input_bytes[i:i + 16]
        hex_bytes = ' '.join(f'{b:02x}' for b in slice)
        hex_bytes = hex_bytes.ljust(16 * 3)  # each byte becomes 'xy ' so 3 chars long
        ascii_repr = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in slice)
        ret += f'{i:04x}: {hex_bytes} | {ascii_repr}\n'
    return ret


class ContentWidget(QWidget):

    DEFAULT_SCRIPT = \
            "# Available variables:\n" \
            "# -- INPUT variables --\n" \
            "#  content_data - bytes of content data received from the proxy\n" \
            "#  content_side - 'L' or 'R', if from client('L'), or server respectively ('R')\n" \
            "#  session_id - unique proxy session identifier\n" \
            "#  session_label - string containing IPs and ports\n" \
            "# -- STORAGE --\n" \
            "#  storage - dict with persistent memory data\n" \
            "#  storage_lock - always access storage with the lock! ('with storage_lock:')\n" \
            "# -- OUTPUT variables --\n" \
            "#  content_replacement - None or bytes used by proxy to replace original content\n" \
            "#  auto_process - set to True to trigger 'Process' action after script finishes." \
            "\n\n" \
            "# info function example:\n" \
            "def info():\n" \
            "    if content_data:\n" \
            "        print(f'{session_id}: {session_label} recv {len(content_data)}B from {content_side}')\n" \
            "\n\n"

    def __init__(self):
        super().__init__()

        self.initUI()

        # Start the Flask thread
        self.flaskThread = ws.server.FlaskThread()
        self.flaskThread.received_content.connect(self.update_content_text)
        self.flaskThread.start()

        State.events.received_session_start.connect(self.on_session_start)
        State.events.received_session_stop.connect(self.on_session_stop)

    def initUI(self):
        # Main layout and splitter
        mainLayout = QHBoxLayout()
        splitter = QSplitter(Qt.Horizontal)

        # Left side components (Existing functionality)
        leftContainer = QWidget()
        leftLayout = QVBoxLayout()
        self.conLabel = QLabel()
        self.textEdit = QTextEdit()
        font = load_font_prog()

        self.textEdit.setFont(font)

        self.textEdit.setReadOnly(True)
        self.button = QPushButton('Process Request')
        self.button.clicked.connect(self.on_button_clicked)
        self.button.setDisabled(True)

        self.skipConditionChkBox = QCheckBox('Skip', self)
        self.skipConditionChkBox.setCheckState(Qt.Checked)
        self.skipConditionChkBox.stateChanged.connect(self.on_skip_condition_toggled)
        self.replacementLabel = QLabel()
        self.replacementLabel.setText("No Replacement")
        ContentWidget.set_label_bg_color(self.replacementLabel, "LightGray")
        self.conStateLabel = QLabel()
        self.conStateLabel.setText("ConnState: ?")

        leftLayout.addWidget(self.conLabel)
        leftLayout.addWidget(self.textEdit)

        leftButtons = QHBoxLayout()
        leftButtons.addWidget(self.button)
        leftButtons.addWidget(self.skipConditionChkBox)
        leftButtons.addWidget(self.replacementLabel)
        leftButtons.addWidget(self.conStateLabel)
        leftLayout.addLayout(leftButtons)
        leftContainer.setLayout(leftLayout)

        # Right side components (New functionality for script execution)
        rightContainer = QWidget()
        rightLayout = QVBoxLayout()

        # self.scriptEdit = QTextEdit()
        # self.scriptEdit.setFont(font)
        lexer = QsciLexerPython()
        self.scriptEdit = QsciScintilla()
        lexer.setFont(font)
        self.scriptEdit.setLexer(lexer)

        self.scriptEdit.setText(
            Config.load_content_script(1)
        )
        self.scriptEdit.textChanged.connect(self.on_script_changed)

        self.executeButton = QPushButton('Execute Script')
        self.executeButton.clicked.connect(self.execute_script)
        self.outputEdit = QTextEdit()
        self.outputEdit.setFont(font)
        self.outputEdit.setReadOnly(True)

        rightLayoutTopButtons = QHBoxLayout()
        self.autoRunCheckBox = QCheckBox('Auto-Execute', self)
        self.autoRunCheckBox.stateChanged.connect(self.on_autorun_toggled)
        rightLayoutTopButtons.addWidget(self.autoRunCheckBox)
        rightLayout.addLayout(rightLayoutTopButtons)

        rightLayoutSlotButtons = QHBoxLayout()
        self.scriptSlots = []
        for i in range(1,6):
            button = QPushButton(f"#{i}")
            button.clicked.connect(functools.partial(
                    self.on_script_slot_button, i))
            self.scriptSlots.append(button)
            rightLayoutSlotButtons.addWidget(button)
        rightLayout.addLayout(rightLayoutSlotButtons)


        rightLayout.addWidget(self.scriptEdit)
        rightLayout.addWidget(self.executeButton)
        rightLayout.addWidget(self.outputEdit)
        rightContainer.setLayout(rightLayout)

        # Add containers to splitter and set the main widget
        splitter.addWidget(leftContainer)
        splitter.addWidget(rightContainer)
        splitter.setSizes([650, 550])

        # Set the main layout
        mainWidget = QWidget()
        mainWidget.setLayout(mainLayout)
        mainLayout.addWidget(splitter)
        # self.setCentralWidget(mainWidget)

        self.setLayout(mainLayout)


    def on_button_clicked(self):
        # Update shared data structure to be included in the Flask response

        with State.lock:
            State.response_data["processed"] = True
            State.response_data["message"] = "Request has been processed successfully."
        # Signal the Flask thread that the button has been clicked
        State.events.button_process.set()

        self.textEdit.clear()
        with State.lock:
            State.ui.content_data = None
        self.button.setDisabled(True)

        ContentWidget.set_label_bg_color(self.replacementLabel, "LightGray")
        self.replacementLabel.setText("No replacement")

    def on_skip_condition_toggled(self, state):
        if state == Qt.CheckState.Checked:
            log.debug("Checked")
            with State.lock:
                State.ui.skip_click = True
        else:
            log.debug("UnChecked")
            with State.lock:
                State.ui.skip_click = False

    def on_script_changed(self):
        self.autoRunCheckBox.setCheckState(Qt.Unchecked)
        with State.lock:
            curslot = State.ui.content_tab.current_script_slot

        Config.save_content_script(curslot, self.scriptEdit.text())

    def on_autorun_toggled(self, state):
        if state == Qt.CheckState.Checked:
            with State.lock:
                State.ui.autorun = True
        else:
            with State.lock:
                State.ui.autorun = False

    def on_session_start(self, id: str, label: str):
        log.debug(f"on_session_start: new session: {id}:{label}")


    def on_session_stop(self, id: str, label: str):
        log.debug(f"on_session_stop: closed session: {id}:{label}")
        with State.lock:
            died = State.ui.content_tab.session_id == id
        if died:
            self.conStateLabel.setText("ConState: CLOSED")
            with State.lock:
                label = State.ui.content_tab.session_label
            self.conLabel.setText(f"(closed) {label}")

    @staticmethod
    def set_label_bg_color(label: QLabel, color_name: str):
        label.setStyleSheet(f'QLabel {{ background-color : {color_name}; }}')

    def validate_results(self, exported_data: dict):
        if exported_data['content_replacement']:
            if isinstance(exported_data['content_replacement'], str) \
                    or isinstance(exported_data['content_replacement'], bytes):
                return

            raise TypeError("content_replacement: must be 'bytes' or 'str'")

    def execute_script(self):
        # Get the script from scriptEdit
        script = self.scriptEdit.text()
        output = ""

        # Use the capture_stdout_as_string context manager to capture output
        with capture_stdout_as_string() as captured_output:
            try:
                with State.lock:
                    State.ui.content_replacement = None
                    exported_data = {
                        "__name__": "__main__",
                        'content_data': copy.copy(State.ui.content_tab.content_data),
                        'content_side': State.ui.content_tab.content_side,
                        'session_id': State.ui.content_tab.session_id,
                        'session_label': State.ui.content_tab.session_label,
                        'storage': Global.storage,
                        'storage_lock': Global.lock,
                        'content_replacement': None,
                        'auto_process': False
                    }

                # Execute the script
                exec(script, exported_data)
                # After script execution, captured_output.getvalue() contains the output
                output = captured_output.getvalue()
                self.validate_results(exported_data)

            except Exception as e:
                was_checked = self.autoRunCheckBox.checkState() == Qt.Checked
                self.autoRunCheckBox.setCheckState(Qt.Unchecked)
                if was_checked:
                    output += ">>> Auto-run was disabled\n"
                output += f">>> Error executing script: {e}\n"
                output += ">>>\n"
                self.outputEdit.setText(output)
                return

        # Display the output in the outputEdit text box
        self.outputEdit.setText(output)

        # collect results
        if exported_data['content_replacement']:
            with State.lock:
                State.ui.content_replacement = exported_data['content_replacement']
                log.debug(f"Got replacement data: {len(State.ui.content_replacement)}B")
                self.replacementLabel.setText(f"replacement {len(exported_data['content_replacement'])}B")
                ContentWidget.set_label_bg_color(self.replacementLabel, "LightCoral")
        else:
            log.debug("no replacements this time")
            self.replacementLabel.setText(f"No replacement")
            ContentWidget.set_label_bg_color(self.replacementLabel, "LightGray")

        if exported_data['auto_process']:
            self.on_button_clicked()

    def update_content_text(self, data):
        log.debug("update_display")
        with State.lock:
            should_update = not State.ui.skip_click

        if should_update:
            js = json.loads(data)
            content = js['details']['info']['content']
            content = base64.b64decode(content)
            session_label = js['details']['info']['session']
            session_side = js['details']['info']['side']
            session_id = js['id']

            with State.lock:
                State.ui.content_tab.content_data = copy.copy(content)
                State.ui.content_tab.session_id = session_id
                State.ui.content_tab.session_label = session_label
                State.ui.content_tab.content_side = session_side

            content = print_bytes(content)

            self.textEdit.setText(f"Received data:\n\n{content}\n\nClick 'Process Request' to respond.")
            self.conStateLabel.setText("ConState: LIVE")
            self.conLabel.setText(f"{session_label}")

            # run the script on data arrival
            with State.lock:
                should_execute = State.ui.autorun
            if should_execute:
                self.execute_script()

            self.button.setDisabled(False)

    def on_script_slot_button(self, number):
        # number - it's not index, it starts with 1
        with State.lock:
            State.ui.content_tab.current_script_slot = number

        script_text = Config.load_content_script(number)
        if not script_text:
            if number == 1:
                script_text = ContentWidget.DEFAULT_SCRIPT
            else:
                script_text = self.scriptSlots[number - 1].text()

        self.scriptEdit.setText(script_text)