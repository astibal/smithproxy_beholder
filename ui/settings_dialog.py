from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, \
    QMessageBox, QCheckBox

from ui.config import Config


class SettingsDialog(QDialog):
    def __init__(self):
        super(SettingsDialog, self).__init__()

        self.address_field = QLineEdit()
        self.port_field = QLineEdit()
        self.api_key_field = QLineEdit()
        self.tls_field = QCheckBox()
        self.cert_field = QLineEdit()
        self.key_field = QLineEdit()

        with Config.lock:
            self.address_field.setText(Config.config.get('address', ''))
            self.port_field.setText(str(Config.config.get('port', '')))
            self.api_key_field.setText(Config.config.get('api_key', ''))
            self.tls_field.setChecked(Config.config.get('is_tls', False))
            self.cert_field.setText(Config.config.get('cert_path', ''))
            self.key_field.setText(Config.config.get('key_path', ''))

        save_button = QPushButton('Save and Close')
        save_button.clicked.connect(self.save_settings)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Listening Address"))
        layout.addWidget(self.address_field)
        layout.addWidget(QLabel("Port"))
        layout.addWidget(self.port_field)
        layout.addWidget(QLabel("API Key"))
        layout.addWidget(self.api_key_field)
        layout.addWidget(QLabel("TLS?"))
        layout.addWidget(self.tls_field)
        layout.addWidget(QLabel("Certificate Path (optional)"))
        layout.addWidget(self.cert_field)
        layout.addWidget(QLabel("Key Path (optional)"))
        layout.addWidget(self.key_field)
        layout.addWidget(save_button)

        self.setLayout(layout)
        self.setGeometry(300,300, 300, 400)

    def save_settings(self):
        config_patch = {
            "address": self.address_field.text(),
            "port": self.port_field.text(),
            "api_key": self.api_key_field.text(),
            "is_tls":  self.tls_field.isChecked(),
            "cert_path": self.cert_field.text(),
            "key_path": self.key_field.text()
        }

        with Config.lock:
            Config.config.update(config_patch)
        Config.save_config()

        self.close()

