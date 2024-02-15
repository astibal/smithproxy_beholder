import logging

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QTextEdit


log = logging.getLogger()


class WidgetLogger(logging.Handler, QtCore.QObject):
    signal = QtCore.pyqtSignal(str)
    def __init__(self, parent: QTextEdit):
        logging.Handler.__init__(self)
        QtCore.QObject.__init__(self, parent)
        self.widget = parent

        self.signal.connect(self.widget.append)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        msg = self.format(record)
        # self.widget.append(msg)
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

        # add logging to the widget
        self.widget_logger = WidgetLogger(self.logEdit)
        self.logEdit.setReadOnly(True)
        self.logEdit.setFont(QtGui.QFont("Courier", 10))

        log.addHandler(self.widget_logger)

        self.setLayout(layout)
