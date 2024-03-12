import logging
import sys
import threading
import time

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt5.QtWidgets import QApplication

from ui.config import Config
from ui.mainwindow import MainWindow
from ui.state import State

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()
log.propagate = False

class Timer(QObject):
    enabled = True
    def run(self):
        while Timer.enabled:
            time.sleep(1)
            Timer.emit_signal()

    def start(self):
        threading.Thread(target=self.run).start()

    @staticmethod
    def emit_signal():
        State.events.click_1s.emit()

    @staticmethod
    def stop_it():
        Timer.enabled = False


if __name__ == "__main__":
    # Initialize and run the PyQt application
    qt_app = QApplication(sys.argv)
    qt_app.aboutToQuit.connect(Timer.stop_it)

    Config.load_config()
    mainWindow = MainWindow()

    timer = Timer()
    timer.start()

    mainWindow.show()
    sys.exit(qt_app.exec_())
