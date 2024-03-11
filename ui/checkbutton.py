from PyQt5.QtWidgets import QPushButton


class CheckButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super(CheckButton, self).__init__(*args, **kwargs)
        self.setCheckable(True)
        self.clicked.connect(self.update_status)
        self.color_border_checked = "darkgray"
        self.color_border_unchecked = "darkgray"
        self.color_button_checked = "lightgrey"
        self.color_button_unchecked = "#f0f0f0"
        self.update_status()

    def setChecked(self, state):
        super().setChecked(state)
        self.update_status()

    def update_status(self):
        if self.isChecked():
            self.setStyleSheet(
                "QPushButton { "
                f"background-color: {self.color_button_checked}; border: 1px solid {self.color_border_checked}; "
                "padding: 3px 20px; border-radius: 2px; "
                "}"
            )
        else:
            self.setStyleSheet(
                "QPushButton { "
                f"background-color: {self.color_button_unchecked}; border: 1px solid {self.color_border_unchecked}; "
                "padding: 3px 20px; border-radius: 2px; "
                "}"
            )

