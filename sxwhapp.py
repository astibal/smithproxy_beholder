import logging
import sys

from PyQt5.QtWidgets import QApplication
from ui.mainwindow import MainWindow
from ui.config import Config

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()

if __name__ == "__main__":
    # Initialize and run the PyQt application
    qt_app = QApplication(sys.argv)

    mainWindow = MainWindow()
    Config.load_config()
    mainWindow.show()
    sys.exit(qt_app.exec_())
