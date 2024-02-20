import base64
import copy
import functools
import json
import platform
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QWidget, QTextEdit, QSplitter, \
    QHBoxLayout, QCheckBox, QLabel, QShortcut, QMessageBox

from util.fonts import load_font_prog
from ui.static_text import S

try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython
    import pyperclip
except ImportError:
    print("This app requires Scintilla")
    print("Ubuntu: apt-get install python3-pyqt5.qsci python3-pyperclip")
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
    processButton: QPushButton | QPushButton
    DEFAULT_SCRIPT = S.py_default_script

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
        self.textEdit.setText(S.txt_skip_checked)

        self.processButton = QPushButton('Process Request')
        self.processButton.clicked.connect(self.on_button_clicked)
        self.processButton.setDisabled(True)

        self.skipConditionChkBox = QCheckBox('Skip', self)
        sc_skipConditionChkBox = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_K), self)
        sc_skipConditionChkBox.activated.connect(self.skipConditionChkBox.toggle)

        self.skipConditionChkBox.setCheckState(Qt.Checked)
        self.skipConditionChkBox.stateChanged.connect(self.on_skip_condition_toggled)
        self.replacementLabel = QLabel()
        self.replacementLabel.setText("No Replacement")
        ContentWidget.set_label_bg_color(self.replacementLabel, "LightGray")
        self.conStateLabel = QLabel()
        self.conStateLabel.setText("ConnState: ?")

        leftLayout.addWidget(self.conLabel)

        leftCopyButtons = QHBoxLayout()
        self.copyAsTextButton = QPushButton("Copy: Text")
        self.copyAsPythonBytes = QPushButton("Copy: PyBy")
        self.copyAsTextButton.setMaximumWidth(100)
        self.copyAsPythonBytes.setMaximumWidth(100)
        self.copyAsTextButton.clicked.connect(self.on_copy_text)
        self.copyAsPythonBytes.clicked.connect(self.on_copy_pyby)
        leftCopyButtons.addWidget(self.copyAsTextButton)
        leftCopyButtons.addWidget(self.copyAsPythonBytes)
        leftCopyButtons.addStretch(1)

        self.copyToSample1 = QPushButton("Copy: S1")
        self.copyToSample2 = QPushButton("Copy: S2")
        self.copyToSample3 = QPushButton("Copy: S3")
        self.copyToSample1.clicked.connect(functools.partial(self.on_copy_sample, 1))
        self.copyToSample2.clicked.connect(functools.partial(self.on_copy_sample, 2))
        self.copyToSample3.clicked.connect(functools.partial(self.on_copy_sample, 3))
        leftCopyButtons.addWidget(self.copyToSample1)
        leftCopyButtons.addWidget(self.copyToSample2)
        leftCopyButtons.addWidget(self.copyToSample3)
        leftCopyButtons.setAlignment(Qt.AlignLeft)
        leftLayout.addLayout(leftCopyButtons)

        leftLayout.addWidget(self.textEdit)

        leftButtons = QHBoxLayout()
        leftButtons.addWidget(self.processButton)
        sc_processButton = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_P), self)
        sc_processButton.activated.connect(self.processButton.click)

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

        sc1 = Config.load_content_script(1)
        if not sc1: sc1 = S.py_default_script
        self.scriptEdit.setText(sc1)

        self.scriptEdit.textChanged.connect(self.on_script_changed)

        self.executeButton = QPushButton('Execute &Script')
        self.executeButton.clicked.connect(self.execute_script)
        sc_exe_script = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_S), self)
        sc_exe_script.activated.connect(self.executeButton.click)

        self.outputEdit = QTextEdit()
        self.outputEdit.setFont(font)
        self.outputEdit.setReadOnly(True)

        rightLayoutTopButtons = QHBoxLayout()
        self.autoRunCheckBox = QCheckBox('Auto-&Execute', self)
        sc_autorun = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_E), self)
        sc_autorun.activated.connect(self.autoRunCheckBox.toggle)

        self.autoRunCheckBox.stateChanged.connect(self.on_autorun_toggled)
        rightLayoutTopButtons.addWidget(self.autoRunCheckBox)
        rightLayout.addLayout(rightLayoutTopButtons)

        rightLayoutSlotButtons = QHBoxLayout()
        self.scriptSlots = []
        for i in range(1, 6):
            button = QPushButton(f"#{i}")
            shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_0 + i), self)

            button.clicked.connect(functools.partial(
                self.on_script_slot_button, i))
            shortcut.activated.connect(functools.partial(
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
        self.processButton.setDisabled(True)

        ContentWidget.set_label_bg_color(self.replacementLabel, "LightGray")
        self.replacementLabel.setText("No replacement")

    def on_skip_condition_toggled(self, state):
        if state == Qt.CheckState.Checked:
            with State.lock:
                State.ui.skip_click = True
                self.textEdit.setText(S.txt_skip_checked)
        else:
            with State.lock:
                State.ui.skip_click = False
                self.textEdit.setText(S.txt_skip_unchecked)

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
            self.textEdit.setStyleSheet("QTextEdit { color: gray; }")

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
                    State.ui.content_tab.content_replacement = None
                    exported_data = {
                        "__name__": "__main__",
                        'content_data': copy.copy(State.ui.content_tab.content_data),
                        'content_side': State.ui.content_tab.content_side,
                        'session_id': State.ui.content_tab.session_id,
                        'session_label': State.ui.content_tab.session_label,
                        'storage': Global.storage,
                        'storage_lock': Global.lock,
                        'samples': Global.samples,
                        'content_replacement': None,
                        'auto_process': False
                    }

                with Config.lock:
                    # add possibility to import directly from project path
                    sys.path.append(Config.config['project_path'])

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
                State.ui.content_tab.content_replacement = exported_data['content_replacement']
                log.debug(f"Got replacement data: {len(State.ui.content_tab.content_replacement)}B")
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
                State.ui.content_tab.content_data_last = copy.copy(content)
                State.ui.content_tab.session_id = session_id
                State.ui.content_tab.session_label = session_label
                State.ui.content_tab.content_side = session_side

            content = print_bytes(content)

            self.textEdit.setText(f""
                      f"Received data:\n\n{content}\n\n"
                      f"1. You may run the script to modify content,\n"
                      f"2. Click 'Process Request' to respond to confirm the payload.\n"
                      f"3. Process can be automated:\n"
                      f"      - 'Auto-Execute' check-box will run script on data arrival (1.)\n"
                      f"      - setting 'auto_process' variable in the script (2.)")
            self.conStateLabel.setText("ConState: LIVE")
            self.conLabel.setText(f"{session_label}")

            # run the script on data arrival
            with State.lock:
                should_execute = State.ui.autorun
            if should_execute:
                self.execute_script()

            self.processButton.setDisabled(False)
            self.textEdit.setStyleSheet("")

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


    def on_copy_text(self):
        try:
            with State.lock:
                if State.ui.content_tab.content_data_last:
                    pyperclip.copy(print_bytes(State.ui.content_tab.content_data_last))

        except ValueError as e:
            m = QMessageBox(QMessageBox.Warning, "Clipboard Error", "cannot copy data to clipboard")
            m.exec()
            if "Linux" in platform.system():
                log.info("To fix clipboard problem, consider to install: libgtk-3-dev")

    def on_copy_pyby(self):
        try:
            with State.lock:
                if State.ui.content_tab.content_data_last:
                    pyperclip.copy(repr(State.ui.content_tab.content_data_last))

        except ValueError as e:
            m = QMessageBox(QMessageBox.Warning, "Clipboard Error", "cannot copy data to clipboard")
            m.exec()
            if "Linux" in platform.system():
                log.info("To fix clipboard problem, consider to install: libgtk-3-dev")

    def on_copy_sample(self, slot: int):
        with Global.lock:
            if State.ui.content_tab.content_data_last:
                Global.samples[slot] = copy.copy(State.ui.content_tab.content_data_last)

