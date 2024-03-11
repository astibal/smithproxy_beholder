import base64
import copy
import functools
import json
import platform
import sys
import time

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QWidget, QTextEdit, QSplitter, \
    QHBoxLayout, QCheckBox, QLabel, QShortcut, QMessageBox

from util.fonts import load_font_prog
from ui.static_text import S
from .checkbutton import CheckButton
from .common import create_python_editor

try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython
    import pyperclip
except ImportError:
    print("This app requires Scintilla and pyperclip, optionally markdown for help.")
    print("Ubuntu: apt-get install python3-pyqt5.qsci python3-pyperclip")
    sys.exit(1)

from util.util import capture_stdout_as_string, print_bytes
from util.err import error_pyperclip

from .state import State, Global
from .config import Config

import logging

log = logging.getLogger()


class WorkbenchTab(QWidget):
    DEFAULT_SCRIPT = S.py_default_script

    def __init__(self):
        super().__init__()

        self.initUI()

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
        self.textEdit.setText(S.txt_sample_empty)
        self.textEdit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.textEdit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.textEdit.setLineWrapMode(QTextEdit.NoWrap)

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

        for i in range(1, 4):
            self.loadSampleX = QPushButton(f"Load: S{i}")
            self.loadSampleX.clicked.connect(functools.partial(self.on_load_sample, i))
            leftCopyButtons.addWidget(self.loadSampleX)

        leftCopyButtons.setAlignment(Qt.AlignLeft)
        leftLayout.addLayout(leftCopyButtons)

        leftLayout.addWidget(self.textEdit)

        leftButtons = QHBoxLayout()
        leftLayout.addLayout(leftButtons)
        leftContainer.setLayout(leftLayout)

        # Right side components (New functionality for script execution)
        rightContainerSplitter = QSplitter(Qt.Vertical)
        rightTopContainer = QWidget()
        rightBottomContainer = QWidget()

        rightContainerSplitter.addWidget(rightTopContainer)
        rightContainerSplitter.addWidget(rightBottomContainer)
        rightContainerSplitter.setStretchFactor(0, 80)
        rightContainerSplitter.setStretchFactor(1, 20)

        rightTopLayout = QVBoxLayout()
        rightBottomLayout = QVBoxLayout()
        lexer = QsciLexerPython()
        self.scriptEdit = create_python_editor()
        lexer.setFont(font)

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
        rightTopLayout.addLayout(rightLayoutTopButtons)

        rightLayoutSlotButtons = QHBoxLayout()
        self.scriptSlots = []
        self.buttons = {} # slot_nr -> CheckButton

        for i in range(1, 6):
            button = CheckButton(f"#{i}")
            self.buttons[i] = button
            shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_0 + i), self)

            button.clicked.connect(functools.partial(
                self.on_script_slot_button, i))
            shortcut.activated.connect(functools.partial(
                self.on_script_slot_button, i))
            self.scriptSlots.append(button)

            rightLayoutSlotButtons.addWidget(button)
        rightTopLayout.addLayout(rightLayoutSlotButtons)

        self.on_script_slot_button(1)

        rightTopLayout.addWidget(self.scriptEdit)
        rightTopLayout.addWidget(self.executeButton)
        rightTopContainer.setLayout(rightTopLayout)

        rightBottomLayout.addWidget(self.outputEdit)
        rightBottomContainer.setLayout(rightBottomLayout)

        # Add containers to splitter and set the main widget
        splitter.addWidget(leftContainer)
        splitter.addWidget(rightContainerSplitter)

        splitter.setStretchFactor(0, 50)
        splitter.setStretchFactor(1, 50)

        # Set the main layout
        mainWidget = QWidget()
        mainWidget.setLayout(mainLayout)
        mainLayout.addWidget(splitter)
        # self.setCentralWidget(mainWidget)

        self.setLayout(mainLayout)

    def on_script_changed(self):
        self.autoRunCheckBox.setCheckState(Qt.Unchecked)
        with State.lock:
            curslot = State.ui.content_tab.current_script_slot

        Config.save_content_script(curslot, self.scriptEdit.text())

    def on_autorun_toggled(self, state):
        if state == Qt.CheckState.Checked:
            with State.lock:
                State.ui.workbench_tab.autorun = True
        else:
            with State.lock:
                State.ui.workbench_tab.autorun = False

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
                    sample_key = State.ui.workbench_tab.current_sample_key

                with Global.lock:
                    sample_meta = {}
                    if sample_key in Global.samples_metadata.keys():
                        hot_data = Global.samples_metadata[sample_key]
                        if hot_data:
                            sample_meta = copy.deepcopy(hot_data)

                with State.lock:

                    # reset results
                    State.ui.content_tab.content_replacement = None
                    State.ui.workbench_tab.current_output = None

                    # prepare shared data (fake live variables, default to None)
                    exported_data = {
                        "__name__": "__main__",
                        'content_data': copy.copy(State.ui.workbench_tab.current_sample),
                        'content_side': sample_meta.get('content_side', None),
                        'session_id': sample_meta.get('session_id', None),
                        'session_label': sample_meta.get('session_label', None),
                        'storage': Global.storage,
                        'storage_lock': Global.lock,
                        'samples': Global.samples,
                        'samples_metadata': Global.samples_metadata,
                        'content_replacement': None,
                        'auto_process': False
                    }
                    exported_data['__appvars__'] = exported_data

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
        if exported_data['content_replacement']:
            data = exported_data['content_replacement']
            if isinstance(data, str):
                data = data.encode()

            self.textEdit.setText(print_bytes(data))

            with State.lock:
                State.ui.workbench_tab.current_output = data
                self.textEdit.setText(print_bytes(data))
        else:
            log.debug("no replacements this time")


    def on_script_slot_button(self, number):
        # number - it's not index, it starts with 1
        with State.lock:
            # change buttons state only when clicking to non-active button
            if State.ui.content_tab.current_script_slot != number:
                State.ui.content_tab.current_script_slot = number
                for sl_id in self.buttons.keys():
                    if sl_id != number:
                        self.buttons[sl_id].setChecked(False)
            else:
                self.buttons[number].setChecked(True)


        script_text = Config.load_content_script(number)
        if not script_text:
            if number == 1:
                script_text = WorkbenchTab.DEFAULT_SCRIPT
            else:
                script_text = self.scriptSlots[number - 1].text()

        self.scriptEdit.setText(script_text)

    def on_copy_text(self):
        try:
            with State.lock:
                if State.ui.workbench_tab.current_output:
                    pyperclip.copy(print_bytes(State.ui.workbench_tab.current_output))
                elif State.ui.workbench_tab.current_sample:
                    pyperclip.copy(print_bytes(State.ui.workbench_tab.current_sample))

        except ValueError as e:
            error_pyperclip()

    def on_copy_pyby(self):
        try:
            with State.lock:
                if State.ui.workbench_tab.current_output:
                    pyperclip.copy(repr(State.ui.workbench_tab.current_output))
                elif State.ui.workbench_tab.current_sample:
                    pyperclip.copy(repr(State.ui.workbench_tab.current_sample))

        except ValueError as e:
            error_pyperclip()

    def on_load_sample(self, slot: int):

        data = None

        with Global.lock:
            if Global.samples[slot]:
                data = Global.samples[slot]
                self.textEdit.setText(print_bytes(data))
            else:
                self.textEdit.setText(f"# slot {slot} empty")

        with State.lock:
            State.ui.workbench_tab.current_sample = data
            State.ui.workbench_tab.current_sample_key = slot
            State.ui.workbench_tab.current_output = None
