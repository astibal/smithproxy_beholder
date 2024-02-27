import logging
import sys

from PyQt5.QtWidgets import QApplication

from ui.config import Config
from ui.mainwindow import MainWindow

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()
log.propagate = False

if __name__ == "__main__":
    # Initialize and run the PyQt application
    qt_app = QApplication(sys.argv)

    Config.load_config()
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(qt_app.exec_())
