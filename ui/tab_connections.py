import base64
import copy
import functools
import json
import sys
import time
from pprint import pformat

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtGui import QTextOption
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QWidget, QTextEdit, QSplitter, \
    QHBoxLayout, QCheckBox, QLabel, QShortcut, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem

from util.fonts import load_font_prog
from util.err import error_pyperclip
from util.util import session_tuple
from util.util import capture_stdout_as_string, print_bytes
from ui.static_text import S
from .checkbutton import CheckButton
from .common import create_python_editor

try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython
    import pyperclip
except ImportError:
    print("This app requires Scintilla and pyperclip, optionally markdown for help.")
    print("Ubuntu: apt-get install python3-pyqt5.qsci python3-pyperclip")
    sys.exit(1)

import ws.server
from .state import State, Global
from .config import Config

import logging

log = logging.getLogger()

class ConnectionTab(QWidget):

    class cfg:
        conn_headers = ["Source", "Src Port", "Destination", "Dst Port", "State" ]
        conn_headers_Source = 0
        conn_headers_Src_Port = 1
        conn_headers_Dst = 2
        conn_headers_Dst_Port = 3
        conn_headers_State = 4

        conn_headers_len = len(conn_headers)
        TimeoutSec = 30


    def __init__(self):
        super().__init__()

        self.initUI()
        State.events.received_session_start.connect(self.on_session_start)
        State.events.received_session_stop.connect(self.on_session_stop)
        State.events.received_session_info.connect(self.on_session_info)

    def initUI(self):
        mainLayout = QHBoxLayout()
        splitter = QSplitter(Qt.Horizontal)

        # Left side components (Existing functionality)
        leftContainer = QWidget()
        leftLayout = QVBoxLayout()
        leftContainer.setLayout(leftLayout)

        rightContainer = QWidget()
        rightLayout = QVBoxLayout()
        rightContainer.setLayout(rightLayout)

        splitter.addWidget(leftContainer)
        splitter.addWidget(rightContainer)
        mainLayout.addWidget(splitter)

        self.connection_list = QTableWidget(0, ConnectionTab.cfg.conn_headers_len)
        self.connection_list.setHorizontalHeaderLabels(ConnectionTab.cfg.conn_headers)
        self.connection_list.verticalHeader().setVisible(False)
        leftLayout.addWidget(self.connection_list)

        self.connection_details = QTextEdit()
        self.connection_details.setReadOnly(True)
        self.connection_details.setWordWrapMode(QTextOption.NoWrap)
        self.connection_details.setFont(load_font_prog())


        self.connection_list.cellClicked.connect(self.on_cell_clicked)
        self.connection_list.cellActivated.connect(self.on_cell_clicked)
        self.connection_list.currentCellChanged.connect(self.on_cell_clicked)

        rightLayout.addWidget(self.connection_details)

        self.setLayout(mainLayout)


    def on_cell_clicked(self, row, col):
        data_item = self.connection_list.item(row, 0)
        if data_item is not None:
            metadata = data_item.data(Qt.UserRole)
            if metadata is not None:
                self.connection_details.setText(pformat(metadata, indent=2, sort_dicts=True, compact=True))

    def delete_rows(self, rows: [int]):
        for i in sorted(rows, reverse=True):
            self.connection_list.removeRow(i)

    def make_row_uneditable(self, row):
        for col in range(ConnectionTab.cfg.conn_headers_len):
            item = self.connection_list.item(row, col)
            if item is not None:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

    def on_session_start(self, id: str, label: str, js: str):
        rows = self.connection_list.rowCount()
        self.connection_list.setRowCount(rows + 1)

        metadata = {
            "id": id,
            "label": label,
            "start":  {
                "ts": time.time(),
                "js": json.loads(js)
            }
        }

        tup = session_tuple(label)
        tup = tup if tup is not None else []

        items = []
        for i in range(ConnectionTab.cfg.conn_headers_len):
            title = ""
            if i < len(tup):
                title = tup[i]

            item = QTableWidgetItem(title)
            item.setData(Qt.UserRole, metadata)
            items.append(item)

        for i in range(len(items)):
            self.connection_list.setItem(rows, i, items[i])

        self.make_row_uneditable(rows)
        self.remove_stales()
        self.connection_list.resizeColumnsToContents()
        self.connection_list.resizeRowToContents(rows)

    def remove_stales(self):
        to_rem = []

        for i in range(0, self.connection_list.rowCount()):
            item = self.connection_list.item(i, 0)
            data_1 = item.data(Qt.UserRole + 1)
            if data_1 is not None:
                if time.time() > data_1['delete_ts']:
                    to_rem.append(i)
            else:
                data_1 = {
                    "delete_ts": time.time() + ConnectionTab.cfg.TimeoutSec
                }
                item.setData(Qt.UserRole + 1, data_1)

        if len(to_rem) > 0:
            self.delete_rows(to_rem)

    def on_session_stop(self, id: str, label: str, js: str):
        log.info(f'session stop for {label}')

        for i in range(0, self.connection_list.rowCount()):
            item = self.connection_list.item(i, 0)
            data = item.data(Qt.UserRole)

            if data is not None and data['id'] == id:

                stop = {
                    "ts": time.time(),
                    "js": json.loads(js)
                }

                state_item = self.connection_list.item(i, ConnectionTab.cfg.conn_headers_State)
                state_item.setText(f'CLOSED')
                data['stop'] = stop
                item.setData(Qt.UserRole, data)

        self.remove_stales()
        self.connection_list.resizeColumnsToContents()

    def on_session_info(self, id: str, label: str, js: str):
        for i in range(0, self.connection_list.rowCount()):
            item = self.connection_list.item(i, 0)
            data = item.data(Qt.UserRole)

            if data is not None and data['id'] == id:
                info = {
                    "ts": time.time(),
                    "js": json.loads(js)
                }

                if 'info' not in data.keys():
                    data['info'] = []
                data['info'].append(info)

                item.setData(Qt.UserRole, data)

        self.remove_stales()
        self.connection_list.resizeColumnsToContents()
