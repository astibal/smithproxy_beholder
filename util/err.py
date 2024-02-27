import platform
from PyQt5.QtWidgets import QMessageBox
import logging

log = logging.getLogger()


def error_pyperclip():
    error_body = "cannot copy data to clipboard"
    if "Linux" in platform.system():
        err = "Linux: to fix clipboard problem, consider to install: libgtk-3-dev"
        log.info(err)
        error_body += f"\n{err}"

    log.error(f"Clipboard Error: {error_body}")
    m = QMessageBox(QMessageBox.Warning, "Clipboard Error", error_body)
    m.exec()
