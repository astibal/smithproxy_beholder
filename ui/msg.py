from PyQt5.QtWidgets import QMessageBox


def dialog_yes_no(title: str, message: str) -> None:
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Question)
    msg_box.setText(message)
    msg_box.setWindowTitle(title)
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

    return_value = msg_box.exec()
    if return_value == QMessageBox.Yes:
        return True

    return False