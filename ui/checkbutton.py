from PyQt5.QtWidgets import QPushButton


class CheckButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super(CheckButton, self).__init__(*args, **kwargs)
        self.setCheckable(True)
        self.clicked.connect(self.update_status)
        self.update_status()

    def update_status(self):
        if self.isChecked():
            self.setStyleSheet(
                "QPushButton { "
                "background-color: darkgrey; border: 1px solid black; "
                "padding: 3px 20px; border-radius: 2px; "
                "}"
            )
        else:
            self.setStyleSheet(
                "QPushButton { "
                "background-color: 0xf0f0f0; border: 1px solid black; "
                "padding: 3px 20px; border-radius: 2px; "
                "}"
            )

