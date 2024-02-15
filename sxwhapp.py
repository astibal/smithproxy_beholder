import logging
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget

from ui.tab_content import ContentWidget

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Smithproxy WebHook Application')
        self.setGeometry(100, 100, 1200, 800)

        self.tab_widget = QTabWidget()
        self.content_widget = ContentWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        self.tab_widget.addTab(self.content_widget, 'Content')

        self.setCentralWidget(self.tab_widget)


if __name__ == "__main__":
    # Initialize and run the PyQt application
    qt_app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(qt_app.exec_())
