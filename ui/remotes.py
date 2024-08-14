import logging
import time
from pprint import pformat
import atexit

from PyQt5.QtCore import QTimer, QSize, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QCheckBox, QComboBox, QWidget, QVBoxLayout, \
    QPushButton, QLabel, QTextEdit, QLineEdit, QHBoxLayout, QMenu

from ui.state import State
from util.fonts import load_font_prog
from ui.checkbutton import CheckButton
from ui.msg import dialog_yes_no

from urllib.parse import urlparse
import requests
import json
from typing import Dict
import functools

from ws.server import FlaskThread


def is_url(text: str) -> bool:
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


log = logging.getLogger('remotes')
log.setLevel(logging.DEBUG)
logsx = logging.getLogger('sx_api')
logsx.setLevel(logging.DEBUG)

class options:
    ca_bundle = None

class SmithproxyAPI:

    class API:
        AUTHORIZE = "/api/authorize"
        WH_REGISTER = "/api/webhook/register"
        WH_UNREGISTER = "/api/webhook/unregister"

    def make_url(self, url: str) -> str:
        return f"{self.base_url}{url}"

    def __init__(self, base_url: str, verify: bool):
        self.base_url = base_url
        self.verify = verify
        self.secret = None
        self.api_token = None
        self.csrf_token = None

        self.AUTHENTICATED = False
        self.access_table = {} # url: str -> timestamp (to track where we have been and when)
        self.wh_dynamic_key = None

    def __del__(self):
        self.unregister_webhook_service_if_needed()

    def set_dynamic_key(self, key: str):
        self.wh_dynamic_key = key

    def serialize_out(self) -> dict:
        return {
            'base_url': self.base_url,
            'verify': self.verify,
            'secret': self.secret,
        }

    def serialize_in(self, data: dict):
        self.base_url = data['base_url']
        self.verify = data['verify']
        self.secret = data['secret']

    def set_secret(self, secret: str):
        self.secret = secret

    @staticmethod
    def authenticated(func):
        def wrapper(*args, **kwargs):
            if args[0]._authenticate():
                return func(*args, **kwargs)

        return wrapper

    def _authenticate(self):
        if self.AUTHENTICATED:
            logsx.debug("Authenticated already")
            return True

        if not self.secret:
            logsx.error("No secret set")
            return False

        url = self.make_url(SmithproxyAPI.API.AUTHORIZE)
        params = {"key": f"{self.secret}"}

        try:
            verify_value = self.verify
            if self.verify and options.ca_bundle:
                verify_value = options.ca_bundle

            response = requests.get(url, params=params, verify=verify_value)
            # response.text contains the body of the server's response
            if response.status_code == 200 and response.content:

                data = response.json()
                if data:
                    logsx.debug(f"Response: {pformat(data)}")
                    self.api_token = data["auth_token"]
                    self.csrf_token = data["csrf_token"]

                    self.access_table[url] = time.time()
                    self.AUTHENTICATED = True

                return True
            else:
                self.AUTHENTICATED = False

        except (requests.exceptions.RequestException, KeyError) as e:
            logsx.error(f"An error occurred: {e}")
            logsx.error(f"URL: {url}, params: {params}, verify: {self.verify}")

        return False

    def _send_request(self, method: str, url: str, payload: dict) -> bool:
        # generic requests
        try:
            verify_value = self.verify
            if self.verify and options.ca_bundle:
                verify_value = options.ca_bundle

            response = requests.request(method=method, url=url, json=payload, verify=verify_value)
            if response.status_code == 200:
                log.info(f"_send_request: '{url[len(self.base_url):]}' status: {response.status_code}")
                self.access_table[url] = time.time()
                return True
            else:
                log.error(f"_send_request: status: {response.status_code}")

        except (requests.exceptions.RequestException, KeyError) as e:
            logsx.error(f"_send_request: an error occurred: {e}")
            logsx.error(f"_send_request: URL: {url}, params: {payload}, verify: {self.verify}")

        return False


    @authenticated
    def register_webhook_service(self, webhook_url: str, webhook_verify: bool) -> bool:
        wh = webhook_url
        if self.wh_dynamic_key:
            wh = f"{wh}/{self.wh_dynamic_key}"
        pay = {
            "auth_token": self.api_token,
            "csrf_token": self.csrf_token,
            "params": {
                "rande_url": f"{wh}",
                "rande_tls_verify": webhook_verify,
            }
        }
        url = self.make_url(SmithproxyAPI.API.WH_REGISTER)
        self.access_table[url] = time.time()
        ret = self._send_request("POST", url, pay)
        if not ret:
            self.AUTHENTICATED = False
        return ret

    def unregister_webhook_service_if_needed(self):
        if self.AUTHENTICATED:
            if time.time() - self.access_table.get(self.make_url(self.API.WH_REGISTER), 0) < 60:
                log.debug("unregistering is worth it")
                self.unregister_webhook_service()  # be a good guys and unregister

    @authenticated
    def unregister_webhook_service(self) -> bool:
        pay = {
            "auth_token": self.api_token,
            "csrf_token": self.csrf_token,
            "params": {}
        }
        url = self.make_url(SmithproxyAPI.API.WH_UNREGISTER)
        return self._send_request("POST", url, pay)

SxDict: Dict[str, SmithproxyAPI]
class TableWidget(QTableWidget):

    tablechanged = pyqtSignal()

    def __init__(self, *args, **kwargs):
        QTableWidget.__init__(self, *args, **kwargs)

        self.service = None
        self.connect_status = {}    # url -> status
        self.sx_remotes: SxDict = {}   # url -> RemoteSmithproxy
        self.inactive = True    # consider table incomplete - don't trigger any communications

        self.COL = ['URL', 'Auth-Token', 'Verify', 'Type', 'Connect']
        self.COL_URL = 0
        self.COL_AUTHTOKEN = 1
        self.COL_VERIFY = 2
        self.COL_TYPE = 3
        self.COL_CONNECT = 4

        self.setHorizontalHeaderLabels(self.COL)

        self.font = load_font_prog()

        # Create a QTimer
        self.timer = QTimer()

        # Setup the timer to call a function every 10 seconds
        self.timer.timeout.connect(self._ten_seconds)

        # Start the timer and set the timing to 10 seconds
        self.timer.start(10 * 1000)  # QTimer works in milliseconds

        self.resizeColumnsToContents()
        self.itemChanged.connect(self.on_item_changed)
        self.on_item_changed_white_list = [] # (row, col) tuple list, where we avoid recursion

        atexit.register(self.cleanup)

    def serialize_out(self):

        ret = {
            'remotes': []
        }

        verify = True
        typ = "Smithproxy"
        conn = False

        for row in range(self.rowCount()):
            url = str(self.item(row, 0).text())
            verify_widget = self.cellWidget(row, self.COL_VERIFY)
            if verify_widget is not None:
                verify = verify_widget.isChecked()

            typ_widget = self.cellWidget(row, self.COL_TYPE)
            if typ_widget is not None:
                typ = typ_widget.currentText()

            conn_widget = self.cellWidget(row, self.COL_CONNECT)
            if conn_widget is not None:
                conn = self.cellWidget(row, self.COL_CONNECT).isChecked()

            entry = {
                'type': typ,
                'connected': conn,
                'data': self.sx_remotes[url].serialize_out()
            }
            ret['remotes'].append(entry)

        return ret


    def serialize_in(self, indata: dict):
        if 'remotes' in indata.keys():
            for item in indata['remotes']:
                try:
                    if item['type'] == "Smithproxy":
                        self.add_smithproxy(item['data']['base_url'],
                                            item['data']['secret'],
                                            item['data']['verify'], "Smithproxy", item['connected'])
                except KeyError:
                    pass

    def cleanup(self):
        for remote in self.sx_remotes.keys():
            sx = self.sx_remotes[remote]
            sx.unregister_webhook_service()

    def activate(self):
        self.inactive = False

    def deactivate(self):
        self.inactive = True

    def webhookUrl(self):
        return self.service

    def setWebhookUrl(self, url: str):
        self.service = url

    def _ten_seconds(self):
        self._run_connects()

    def _run_connects(self):

        if not self.service or "[XXX]" in self.service or not is_url(self.service):
            log.error("my webhook URL not set!")
            return

        rows = self.rowCount()
        for r in range(rows):
            url = self.item(r, self.COL_URL).text()
            is_set_to_connect = self.cellWidget(r, self.COL_CONNECT).isChecked()

            if url not in self.connect_status.keys():
                self.connect_status[url] = False

            cur_connect_status = self.connect_status[url]
            if cur_connect_status and not is_set_to_connect:
                log.debug(f"{r}: should disconnect")
                self.connect_status[url] = False
                self.unregister(url)
            elif cur_connect_status:
                log.debug(f"{r}: connected, refreshing")
                self.connect_status[url] = self.register(url)
            elif is_set_to_connect:
                log.debug(f"{r}: registering")
                self.connect_status[url] = self.register(url)
            else:
                log.debug(f"{r}: inactive")


    def _connect(self):
        pass

    def add_smithproxy(self, url, token, verify, _type, connect):

        self.connect_status[url] = False
        sx = SmithproxyAPI(url, verify)
        sx.set_secret(token)
        with State.lock:
            sx.set_dynamic_key(State.auth.register(url))
        self.sx_remotes[url] = sx

        self.on_item_changed_white_list.append((0,0))
        self._add_row(url, token, verify, _type, connect)
        self.on_item_changed_white_list.remove((0, 0))

    def _add_row(self, url, token, verify, _type, connect):
        row = self.rowCount()
        self.insertRow(row)
        url_item = QTableWidgetItem(url)
        url_item.setData(Qt.UserRole, url)
        url_item.setFont(self.font)
        self.setItem(row, self.COL_URL, url_item)
        self.connect_status[url] = False

        token_item = QTableWidgetItem(token)
        token_item.setData(Qt.UserRole, token_item)
        token_item.setFont(self.font)
        self.setItem(row, self.COL_AUTHTOKEN, token_item)
        self.connect_status[url] = False

        chkbox_verify = QCheckBox()
        chkbox_verify.setChecked(verify)
        chkbox_verify.setFont(self.font)
        self.setCellWidget(row, self.COL_VERIFY, chkbox_verify)
        chkbox_verify.stateChanged.connect(self.on_item_changed)

        combobox_type = QComboBox()
        combobox_type.addItems(["Smithproxy", "Doomster"])
        combobox_type.setCurrentText(_type)
        combobox_type.setFont(self.font)
        self.setCellWidget(row, self.COL_TYPE, combobox_type)
        combobox_type.currentTextChanged.connect(self.on_item_changed)

        chkbox_connect = QCheckBox()
        chkbox_connect.setChecked(connect)
        self.setCellWidget(row, self.COL_CONNECT, chkbox_connect)
        chkbox_connect.stateChanged.connect(self.on_item_changed)

        for r in range(self.rowCount()):
            self.resizeRowToContents(r)

        for c in range(self.columnCount()):
            self.resizeColumnToContents(c)

    def register(self, url):
        if url in self.sx_remotes.keys():
            sx = self.sx_remotes[url]
            return sx.register_webhook_service(self.service, sx.verify)
        else:
            log.error(f"register: remote '{url}' not found")

    def unregister(self, url):
        if url in self.sx_remotes.keys():
            sx = self.sx_remotes[url]
            return sx.unregister_webhook_service_if_needed()
        else:
            log.error(f"unregister: remote '{url}' not found")


    def on_item_changed(self):
        if self.inactive:
            return

        row = self.currentRow()
        col = self.currentColumn()

        pos = (row, col)
        if pos in self.on_item_changed_white_list or pos == (-1,-1):
            return

        self.on_item_changed_white_list.append(pos)


        # load old value, and replace it with a new value
        url_item = self.item(row, self.COL_URL)
        url_old = url_item.data(Qt.UserRole)
        url = url_item.text()
        url_item.setData(Qt.UserRole, url)

        # load old value, and replace it with a new value
        auth_item = self.item(row, self.COL_AUTHTOKEN)
        auth_old = auth_item.data(Qt.UserRole)
        auth = auth_item.text()
        auth_item.setData(Qt.UserRole, auth)

        verify = self.cellWidget(row, self.COL_VERIFY).isChecked()
        type = self.cellWidget(row, self.COL_TYPE).currentText()
        conn = self.cellWidget(row, self.COL_CONNECT).isChecked()


        new = False
        if url in self.sx_remotes.keys():
            log.debug(f"existing smithproxy at '{url}'")
            sx = self.sx_remotes[url]
        else:
            new = True
            sx = SmithproxyAPI(url, verify)
            with State.lock:
                sx.set_dynamic_key(State.auth.register(url))

            self.sx_remotes[url] = sx
            log.debug(f"new smithproxy at '{url}'")

            if url_old in self.sx_remotes.keys():
                log.debug(f"deleting old smithproxy at '{url}'")
                del self.sx_remotes[url_old]

        sx.verify = verify

        if auth != sx.secret or url != sx.base_url:
            log.debug(f"smithproxy at '{url}' - credentials changed")
            sx.secret = auth
            sx.base_url = url
            sx.AUTHENTICATED = False

        self.on_item_changed_white_list.remove(pos)
        self.tablechanged.emit()

    def contextMenuEvent(self, event):
        contextMenu = QMenu(self)
        addAction = contextMenu.addAction("Add")
        addAction.triggered.connect(self.add_defautl_row)
        remAction = contextMenu.addAction("Remove")
        remAction.triggered.connect(self.remove_row)

        action = contextMenu.exec_(self.viewport().mapToGlobal(event.pos()))

    def add_defautl_row(self):
        self.add_smithproxy('https://', "verysecret", True, 'Smithproxy', False)

    def remove_row(self):

        item = self.selectedItems()[0]
        row = item.row()
        item0 = self.item(row, 0)
        url = item0.text()

        if not dialog_yes_no("Delete this entry", f"Are you sure you want to delete:\n {url}"):
            return

        if url in self.sx_remotes.keys():
            del self.sx_remotes[url]

        self.removeRow(row)
        self.tablechanged.emit()



class RemotesWidget(QWidget):

    service_change = pyqtSignal()
    def __init__(self, service: str):
        super().__init__()

        #self.service = service
        self.layout = QVBoxLayout()


        self.label = QLabel("My URL:")
        self.layout.addWidget(self.label)

        hb = QHBoxLayout()
        self.my_url = QLineEdit(service)
        self.my_url.setReadOnly(True)
        self.my_url.setDisabled(True)
        self.url_button = CheckButton("Edit")
        self.url_button.setChecked(False)
        self.url_button.setMaximumWidth(100)
        self.url_button.clicked.connect(self.on_edit_url)

        hb.addWidget(self.my_url)
        hb.addWidget(self.url_button)
        self.layout.addLayout(hb)

        hb2 = QHBoxLayout()
        self.my_service_lab = QLabel("Active service URL:  ")
        self.my_service = QLabel(service)
        hb2.addWidget(self.my_service_lab)
        hb2.addWidget(self.my_service)
        hb2.addStretch(2)
        self.layout.addLayout(hb2)

        self.table = TableWidget(0, 5)
        self.table.setWebhookUrl(service)
        self.layout.addWidget(self.table)

        self.setLayout(self.layout)

    def serialize_in(self, data: dict):
        service = data["service"]
        self.table.setWebhookUrl(service)
        self.my_url.setText(service)
        self.my_service.setText(service)

        self.table.serialize_in(data['entries'])

    def serialize_out(self):
        return {
            "service": self.table.webhookUrl(),
            "entries": self.table.serialize_out()
        }

    def invalidate_all_remotes(self):
        pass

    def on_edit_url(self):
        self.my_url.setReadOnly(not self.url_button.isChecked())
        self.my_url.setDisabled(not self.url_button.isChecked())

        if not self.url_button.isChecked():
            self.url_button.setText("Edit")
            url = self.my_url.text()
            if url != self.table.webhookUrl():
                self.table.setWebhookUrl(url)

                print("Service change")
                self.invalidate_all_remotes()

                self.table.setWebhookUrl(url)
                self.service_change.emit()

            self.my_service.setText(self.table.webhookUrl())
        else:
            self.url_button.setText("Save")


def main():
    app = QApplication([])
    main_widget = RemotesWidget("http://172.30.1.253:5000/webhook/secretkey")
    main_widget.table.add_smithproxy('https://sx1:55555', "verysecret", False, 'Smithproxy', False)
    main_widget.table.add_smithproxy('https://sx2:55555', "verysecret", False, 'Doomster', False)
    main_widget.table.activate()
    main_widget.show()
    app.exec_()


if __name__ == "__main__":
    from urllib3 import disable_warnings as debug_disable_verify_warnings_I_know_what_I_am_doing
    debug_disable_verify_warnings_I_know_what_I_am_doing()
    main()
