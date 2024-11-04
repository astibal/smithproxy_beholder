import logging
import datetime

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QTextEdit, QComboBox, QHBoxLayout, QLabel, QPlainTextEdit

from util.fonts import load_font_prog, remove_ansi_color_codes

from ui.checkbutton import CheckButton
from ws.server import FlaskThread

log = logging.getLogger()


class WidgetLogger(logging.Handler, QtCore.QObject):
    signal = QtCore.pyqtSignal(str)

    def __init__(self, parent: QTextEdit):
        logging.Handler.__init__(self)
        QtCore.QObject.__init__(self, parent)
        self.widget = parent
        self.enabled = False

        self.signal.connect(self.widget.appendPlainText)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.setFormatter(formatter)

        # now remove old handlers

        log.handlers = []
        log.addHandler(self)
        # FlaskThread.app.logger.addHandler(self)

        wzlog = logging.getLogger('werkzeug')
        wzlog.handlers = []
        wzlog.addHandler(self)

    def emit(self, record):
        if self.enabled:
            msg = remove_ansi_color_codes(self.format(record))
            self.signal.emit(msg)


class LogWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.MAXLINES = 100
        self.widget_logger = None
        self.initUI()

    def initUI(self):
        self.logEdit = QPlainTextEdit()
        layout = QVBoxLayout()
        layout.addWidget(self.logEdit)

        buttonBar = QHBoxLayout()
        buttonBar.setAlignment(Qt.AlignLeft)
        self.logLevelDropDown = QComboBox(self)
        self.logLevelDropDown.addItems(["DEBUG", "INFO", "WARNING"])
        self.logLevelDropDown.currentTextChanged.connect(self.on_log_level)
        self.logLevelDropDown.setFixedWidth(200)
        self.logLevelDropDown.setCurrentText("INFO")
        buttonBar.addWidget(self.logLevelDropDown)

        self.collectButton = CheckButton("Collect")
        self.collectButton.setMaximumWidth(200)
        self.collectButton.clicked.connect(self.on_collect_button_clicked)
        buttonBar.addWidget(self.collectButton)


        linesLab = QLabel("Lines:")
        linesLab.setMaximumWidth(200)
        buttonBar.addWidget(linesLab)

        self.lineCount = QComboBox()
        self.lineCount.setMaximumWidth(200)
        self.lineCount.setCurrentText(f"{self.MAXLINES}")
        self.lineCount.addItems([f"{self.MAXLINES}", "500", "1000", "5000"])
        self.lineCount.currentTextChanged.connect(self.on_linecount_change)
        buttonBar.addWidget(self.lineCount)
        buttonBar.addStretch(4)

        self.editLinesLab = QLabel()
        buttonBar.addWidget(self.editLinesLab)

        layout.addLayout(buttonBar)

        # add logging to the widget
        self.widget_logger = WidgetLogger(self.logEdit)
        self.logEdit.setReadOnly(True)
        font = load_font_prog()
        self.logEdit.setFont(font)
        self.logEdit.textChanged.connect(self.on_text_change)
        self.setLayout(layout)

    def remove_first_n_lines(self, n):
        self.logEdit.setUpdatesEnabled(False)
        cursor = self.logEdit.textCursor()  # Get the QTextCursor
        cursor.movePosition(cursor.Start)  # Move cursor to start of text
        for _ in range(n):
            cursor.movePosition(cursor.Down, cursor.KeepAnchor)  # Select down to next line
        cursor.removeSelectedText()  # Remove the selected text
        self.logEdit.setUpdatesEnabled(True)

    def truncate_to_maxlines(self):
        count = self.logEdit.document().blockCount()
        if count > self.MAXLINES:
            self.remove_first_n_lines(count - self.MAXLINES)

    def on_linecount_change(self):
        count = int(self.lineCount.currentText())
        self.MAXLINES = count

    def on_collect_button_clicked(self):
        now = datetime.datetime.now()

        if self.collectButton.isChecked():
            self.logEdit.appendPlainText(f"--- LogViewer Start --- : {now}")
            self.widget_logger.enabled = True
        else:
            self.logEdit.appendPlainText(f"--- LogViewer Stop --- : {now}")
            self.widget_logger.enabled = False

    def on_log_level(self, text):

        rem = logging.getLogger('remotes')
        rem.setLevel(text)
        sx = logging.getLogger('sx_api')
        sx.setLevel(text)

        log.setLevel(text)

    def on_text_change(self):
        self.truncate_to_maxlines()
        c = self.logEdit.document().blockCount()
        self.editLinesLab.setText(f"Lines: {c}")