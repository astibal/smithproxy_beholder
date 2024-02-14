import base64
import json
import sys
import copy

from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit, QSplitter, \
    QHBoxLayout, QCheckBox, QLabel
from PyQt5.QtCore import Qt
from PyQt5 import QtGui

try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython
except ImportError:
    print("This app requires Scintilla")
    print("Ubuntu: apt-get install python3-pyqt5.qsci")
    sys.exit(1)

from contextlib import contextmanager

import ws.server
from .state import State


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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Smithproxy WebHook Application')
        self.setGeometry(100, 100, 800, 400)

        self.initUI()

        # Start the Flask thread
        self.flaskThread = ws.server.FlaskThread()
        self.flaskThread.updated.connect(self.update_display)
        self.flaskThread.start()

    def initUI(self):
        # Main layout and splitter
        mainLayout = QHBoxLayout()
        splitter = QSplitter(Qt.Horizontal)

        # Left side components (Existing functionality)
        leftContainer = QWidget()
        leftLayout = QVBoxLayout()
        self.textEdit = QTextEdit()
        font = QtGui.QFont("Courier", 11)  # "Courier" is a commonly available monospaced font
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
        MainWindow.set_label_bg_color(self.replacementLabel, "LightGray")

        leftLayout.addWidget(self.textEdit)

        leftButtons = QHBoxLayout()
        leftButtons.addWidget(self.button)
        leftButtons.addWidget(self.skipConditionChkBox)
        leftButtons.addWidget(self.replacementLabel)
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
            "# Available variables:\n"
            "#    content_data - bytes of content data received from the proxy\n"
            "#    content_replacement - None or bytes used by proxy to replace original content\n"
            "#    auto_process - set to True to trigger 'Process' action after script finishes."
            "\n\n"
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
        rightLayout.addWidget(self.scriptEdit)
        rightLayout.addWidget(self.executeButton)
        rightLayout.addWidget(self.outputEdit)
        rightContainer.setLayout(rightLayout)

        # Add containers to splitter and set the main widget
        splitter.addWidget(leftContainer)
        splitter.addWidget(rightContainer)
        splitter.setSizes([400, 400])

        # Set the main layout
        mainWidget = QWidget()
        mainWidget.setLayout(mainLayout)
        mainLayout.addWidget(splitter)
        self.setCentralWidget(mainWidget)

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

        MainWindow.set_label_bg_color(self.replacementLabel, "LightGray")
        self.replacementLabel.setText("No replacement")

    def on_skip_condition_toggled(self, state):
        if state == Qt.CheckState.Checked:
            print("Checked")
            with State.lock:
                State.ui.skip_click = True
        else:
            print("UnChecked")
            with State.lock:
                State.ui.skip_click = False

    def on_script_changed(self):
        self.autoRunCheckBox.setCheckState(Qt.Unchecked)

    def on_autorun_toggled(self, state):
        if state == Qt.CheckState.Checked:
            with State.lock:
                State.ui.autorun = True
        else:
            with State.lock:
                State.ui.autorun = False

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
                        'content_data': copy.copy(State.ui.content_data),
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
                print(f"Got replacement data: {len(State.ui.content_replacement)}B")
                self.replacementLabel.setText(f"replacement {len(exported_data['content_replacement'])}B")
                MainWindow.set_label_bg_color(self.replacementLabel, "LightCoral")
        else:
            print("no replacements this time")
            self.replacementLabel.setText(f"No replacement")
            MainWindow.set_label_bg_color(self.replacementLabel, "LightGray")

        if exported_data['auto_process']:
            self.on_button_clicked()

    def update_display(self, data):
        print("update_display")
        with State.lock:
            should_update = not State.ui.skip_click

        if should_update:
            content = json.loads(data)['details']['info']['content']
            content = base64.b64decode(content)
            with State.lock:
                State.ui.content_data = copy.copy(content)

            content = print_bytes(content)

            self.textEdit.setText(f"Received data:\n\n{content}\n\nClick 'Process Request' to respond.")

            # run the script on data arrival
            with State.lock:
                should_execute = State.ui.autorun
            if should_execute:
                self.execute_script()

            self.button.setDisabled(False)

