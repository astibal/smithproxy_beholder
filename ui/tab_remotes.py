from PyQt5.QtWidgets import QVBoxLayout, QWidget

import socket

from ui.remotes import RemotesWidget
from ui.config import Config

class RemoteTab(QWidget):
    def __init__(self):
        super().__init__()
        self.remote_widget = None
        self.initUI()



    @staticmethod
    def compose_service_url():
        scheme = "http"
        hostname = socket.gethostname()
        if Config.config['use_tls']:
            scheme = "https"

        return f"{scheme}://{hostname}:{Config.config['port']}/webhook/{Config.config['api_key']}"

    def serialize_in(self):
        if 'remotes' in Config.config.keys():
            self.remote_widget.serialize_in(Config.config['remotes'])

    def serialize_out(self):
        data = self.remote_widget.serialize_out()
        Config.config['remotes'] = data
        Config.save_config()

    def on_changed(self):
        self.serialize_out()

    def initUI(self):
        layout = QVBoxLayout()
        self.remote_widget = RemotesWidget(RemoteTab.compose_service_url())
        layout.addWidget(self.remote_widget)
        self.setLayout(layout)

        self.serialize_in()
        self.remote_widget.table.activate()
        self.remote_widget.table.tablechanged.connect(self.on_changed)
        self.remote_widget.service_change.connect(self.on_changed)
