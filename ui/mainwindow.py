from PyQt5.QtWidgets import QMainWindow, QTabWidget

from ui.tab_content import ContentWidget
from ui.tab_log import LogWidget

import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Smithproxy WebHook Application')
        self.setGeometry(100, 100, 1200, 800)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        self.content_widget = ContentWidget()
        self.tab_widget.addTab(self.content_widget, 'Content')

        self.log_widget = LogWidget()
        self.tab_widget.addTab(self.log_widget, 'Logs')

        self.setCentralWidget(self.tab_widget)