from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, \
    QMessageBox, QCheckBox, QStyle, QHBoxLayout, QFileDialog

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
            self.tls_field.setChecked(Config.config.get('use_tls', False))
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
        certlayout = QHBoxLayout()
        certlayout.addWidget(self.cert_field)
        cert_filepicker = QPushButton()
        cert_filepicker.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        cert_filepicker.setFixedWidth(40)
        cert_filepicker.clicked.connect(self.get_file_cert)
        certlayout.addWidget(cert_filepicker)
        layout.addLayout(certlayout)

        layout.addWidget(QLabel("Key Path (optional)"))
        keylayout = QHBoxLayout()
        keylayout.addWidget(self.key_field)
        key_filepicker = QPushButton()
        key_filepicker.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        key_filepicker.setFixedWidth(40)
        key_filepicker.clicked.connect(self.get_file_key)
        keylayout.addWidget(key_filepicker)
        layout.addLayout(keylayout)

        layout.addWidget(save_button)

        self.setLayout(layout)
        self.setGeometry(300,300, 300, 400)

    def get_file_cert(self):
        f =  self.openFilePicker("Select Certificate",
                                   "Certificate Files (*.pem);;All Files (*)")

        if f:
            self.cert_field.setText(f)

    def get_file_key(self):
        f =  self.openFilePicker("Select Certificate Key",
                                   "PEM Files (*.pem);;All Files (*)")

        if f:
            self.key_field.setText(f)

    def openFilePicker(self, title: str, filter: str) -> str:
        # example filter: "Certificate Files (*.pem);;All Files (*)"
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly

        filt = "All Files (*)"
        if filter:
            filt = filter

        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        # dialog.setNameFilter('PEM Files (*.pem)')

        fnm, _ = dialog.getOpenFileName(None, title, "", filt,
                                             options=options)

        return fnm

    def save_settings(self):
        config_patch = {
            "address": self.address_field.text(),
            "port": self.port_field.text(),
            "api_key": self.api_key_field.text(),
            "use_tls":  self.tls_field.isChecked(),
            "cert_path": self.cert_field.text(),
            "key_path": self.key_field.text()
        }

        with Config.lock:
            Config.config.update(config_patch)
        Config.save_config()

        self.close()

