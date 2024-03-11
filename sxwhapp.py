import logging
import sys

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication

from ui.config import Config
from ui.mainwindow import MainWindow
from ui.state import State

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()
log.propagate = False

class Timer(QObject):
    def start(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.emit_signal)
        self.timer.start(1000)

    def emit_signal(self):
        State.events.click_1s.emit()

if __name__ == "__main__":
    # Initialize and run the PyQt application
    qt_app = QApplication(sys.argv)

    Config.load_config()
    mainWindow = MainWindow()

    timer = Timer()
    timer.start()

    mainWindow.show()
    sys.exit(qt_app.exec_())
