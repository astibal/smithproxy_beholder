import json
import sys
import threading
from pprint import pprint, pformat

from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit, QSplitter, \
    QHBoxLayout, QCheckBox
from PyQt5.QtCore import QThread, pyqtSignal, Qt

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
        self.textEdit.setReadOnly(True)
        self.button = QPushButton('Process Request')
        self.button.clicked.connect(self.on_button_clicked)
        self.button.setDisabled(True)

        self.skipConditionChkBox = QCheckBox('Skip', self)
        self.skipConditionChkBox.setCheckState(Qt.Checked)
        self.skipConditionChkBox.stateChanged.connect(self.on_skip_condition_toggled)

        leftLayout.addWidget(self.textEdit)

        leftButtons = QHBoxLayout()
        leftButtons.addWidget(self.button)
        leftButtons.addWidget(self.skipConditionChkBox)
        leftLayout.addLayout(leftButtons)
        leftContainer.setLayout(leftLayout)

        # Right side components (New functionality for script execution)
        rightContainer = QWidget()
        rightLayout = QVBoxLayout()
        self.scriptEdit = QTextEdit()
        self.executeButton = QPushButton('Execute Script')
        self.executeButton.clicked.connect(self.execute_script)
        self.outputEdit = QTextEdit()
        self.outputEdit.setReadOnly(True)
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
        self.button.setDisabled(True)

    def on_skip_condition_toggled(self, state):
        if state == Qt.CheckState.Checked:
            print("Checked")
            with State.lock:
                State.ui.skip_click = True
        else:
            print("UnChecked")
            with State.lock:
                State.ui.skip_click = False

    def execute_script(self):
        # Get the script from scriptEdit
        script = self.scriptEdit.toPlainText()

        # Use the capture_stdout_as_string context manager to capture output
        with capture_stdout_as_string() as captured_output:
            try:
                # Execute the script
                exec(script, {"__name__": "__main__"})
                # After script execution, captured_output.getvalue() contains the output
                output = captured_output.getvalue()
            except Exception as e:
                output = f"Error executing script: {e}"

        # Display the output in the outputEdit text box
        self.outputEdit.setText(output)

    def update_display(self, data):
        print("update_display")
        with State.lock:
            should_update = not State.ui.skip_click

        if should_update:
            self.textEdit.setText(f"Received data: {pformat(data)}\n\nClick 'Process Request' to respond.")
            self.button.setDisabled(False)
