from PyQt5.QtWidgets import QMainWindow, QTabWidget, QMenuBar, QAction, QFileDialog

from ui.tab_content import ContentWidget
from ui.tab_log import LogWidget

from ui.config import Config

import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Smithproxy WebHook Application')
        self.setGeometry(100, 100, 1200, 800)

        project_menu = self.menuBar().addMenu('Project')
        open_project_menu = QAction('Open Directory', self)
        project_menu.addAction(open_project_menu)
        open_project_menu.triggered.connect(self.open_project_dir)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        self.content_widget = ContentWidget()
        self.tab_widget.addTab(self.content_widget, 'Content')

        self.log_widget = LogWidget()
        self.tab_widget.addTab(self.log_widget, 'Logs')

        self.setCentralWidget(self.tab_widget)

    def open_project_dir(self):
        directory = QFileDialog.getExistingDirectory(None, "Select Directory")
        with Config.lock:
            Config.config['project_path'] = directory

        Config.save_config()

        self.content_widget.on_script_slot_button(1)