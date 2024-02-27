import logging
import datetime

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QTextEdit, QComboBox, QHBoxLayout

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

        self.signal.connect(self.widget.append)

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
        self.widget_logger = None
        self.initUI()

    def initUI(self):
        self.logEdit = QTextEdit()
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

        layout.addLayout(buttonBar)

        # add logging to the widget
        self.widget_logger = WidgetLogger(self.logEdit)
        self.logEdit.setReadOnly(True)
        font = load_font_prog()
        self.logEdit.setFont(font)
        self.setLayout(layout)

    def on_collect_button_clicked(self):
        now = datetime.datetime.now()

        if self.collectButton.isChecked():
            self.logEdit.append(f"--- LogViewer Start --- : {now}")
            self.widget_logger.enabled = True
        else:
            self.logEdit.append(f"--- LogViewer Stop --- : {now}")
            self.widget_logger.enabled = False

    def on_log_level(self, text):
        log.setLevel(text)
