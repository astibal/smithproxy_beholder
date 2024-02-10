import json
import sys
import threading
from pprint import pprint, pformat
from PyQt5.QtWidgets import QApplication

from ui.mainw import MainWindow
from ui.state import State

if __name__ == "__main__":
    # Initialize and run the PyQt application
    qt_app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(qt_app.exec_())
