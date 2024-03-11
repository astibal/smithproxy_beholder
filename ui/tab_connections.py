import json
import json
import sys
import time
from pprint import pformat

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QTextOption, QColor
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QTextEdit, QSplitter, \
    QHBoxLayout, QTableWidget, QTableWidgetItem, QTabWidget

from util.fonts import load_font_prog
from util.util import session_tuple

try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython
    import pyperclip
except ImportError:
    print("This app requires Scintilla and pyperclip, optionally markdown for help.")
    print("Ubuntu: apt-get install python3-pyqt5.qsci python3-pyperclip")
    sys.exit(1)

from .state import State

import logging

log = logging.getLogger()


class ConnectionsTableWidget(QTableWidget):

    removing_row = pyqtSignal(int)
    class cfg:
        conn_headers = ["Source", "Src Port", "Destination", "Dst Port", "State"]
        conn_headers_Source = 0
        conn_headers_Src_Port = 1
        conn_headers_Dst = 2
        conn_headers_Dst_Port = 3
        conn_headers_State = 4

        conn_headers_len = len(conn_headers)
        TimeoutSec = 30
        color_expiring = "#f0f0f0"

    def __init__(self, rows: int, parent=None):
        super().__init__(rows, ConnectionsTableWidget.cfg.conn_headers_len, parent)

        self.setHorizontalHeaderLabels(ConnectionsTableWidget.cfg.conn_headers)
        self.verticalHeader().setVisible(False)

        self.cellClicked.connect(self.on_cell_clicked)
        self.cellActivated.connect(self.on_cell_clicked)
        self.currentCellChanged.connect(self.on_cell_clicked)
        State.events.click_1s.connect(self.rescan_connections)

        self.connection_details = None
        self.rescan = False

        self.table_font = load_font_prog()
        self.table_font.setPointSize(self.table_font.pointSize() - 1)

    def set_details_widget(self, connection_details: QTextEdit):
        self.connection_details = connection_details

    def set_rescan(self, rescan: bool):
        self.rescan = rescan

    def on_cell_clicked(self, row, col):
        data_item = self.item(row, 0)
        if data_item is not None:
            metadata = data_item.data(Qt.UserRole)
            if metadata is not None and self.connection_details:
                self.connection_details.setText(pformat(metadata, indent=2, sort_dicts=True, compact=True))

    def delete_rows(self, rows: [int]):
        for i in sorted(rows, reverse=True):
            self.removing_row.emit(i)
            self.removeRow(i)

    def custom_resize_columns(self):
        for column in range(self.columnCount()):
            width = self.columnWidth(column)
            max_width = 0
            for row in range(self.rowCount()):
                item = self.item(row, column)
                if item:
                    new_width = self.fontMetrics().width(
                        item.text()) + 20  # adding padding for visibility
                    max_width = new_width if new_width > max_width else max_width
            if max_width > width:
                self.setColumnWidth(column, max_width)

    def make_row_uneditable(self, row):
        for col in range(ConnectionsTableWidget.cfg.conn_headers_len):
            item = self.item(row, col)
            if item is not None:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

    def remove_stales(self):
        to_rem = []

        for i in range(0, self.rowCount()):
            item = self.item(i, 0)
            if item:
                data_1 = item.data(Qt.UserRole + 1)
                if data_1 is not None:
                    if time.time() > data_1['delete_ts']:
                        to_rem.append(i)
                    elif data_1['delete_ts'] - time.time() < self.cfg.TimeoutSec / 3:
                        status_item = self.item(i, self.cfg.conn_headers_State)
                        if status_item:
                            status_item.setBackground(QColor(self.cfg.color_expiring))
                else:
                    status_item = self.item(i, self.cfg.conn_headers_State)
                    if status_item.text() in ["CLOSED", ]:
                        data_1 = {
                            "delete_ts": time.time() + self.cfg.TimeoutSec
                        }
                        item.setData(Qt.UserRole + 1, data_1)

        if len(to_rem) > 0:
            self.delete_rows(to_rem)

    def rescan_connections(self):
        if self.rescan:
            self.remove_stales()
            self.custom_resize_columns()


    def add_connection(self, id: str, label: str, js: str):
        rows = self.rowCount()
        self.insertRow(0)

        metadata = {
            "id": id,
            "label": label,
            "start": {
                "ts": time.time(),
                "js": json.loads(js)
            }
        }

        tup = session_tuple(label)
        tup = tup if tup is not None else []

        items = []
        for i in range(ConnectionsTableWidget.cfg.conn_headers_len):
            title = ""
            if i < len(tup):
                title = tup[i]

            item = QTableWidgetItem(title)
            item.setData(Qt.UserRole, metadata)
            item.setFont(self.table_font)
            items.append(item)

        for i in range(len(items)):
            self.setItem(0, i, items[i])

        self.make_row_uneditable(0)
        self.remove_stales()
        self.custom_resize_columns()
        self.resizeRowToContents(0)



    def stop_connection(self, id: str, label: str, js: str):
        log.info(f'session stop for {label}')

        for i in range(0, self.rowCount()):
            item = self.item(i, 0)
            if not item:
                continue

            data = item.data(Qt.UserRole)

            if data is not None and data['id'] == id:
                stop = {
                    "ts": time.time(),
                    "js": json.loads(js)
                }

                state_item = self.item(i, ConnectionsTableWidget.cfg.conn_headers_State)
                state_item.setText(f'CLOSED')
                data['stop'] = stop
                item.setData(Qt.UserRole, data)

        self.remove_stales()
        self.custom_resize_columns()

    def add_connection_info(self, id: str, label: str, js: str):
        for i in range(0, self.rowCount()):
            item = self.item(i, 0)
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
        self.custom_resize_columns()


class ConnectionTab(QWidget):

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

        self.conn_live_table = ConnectionsTableWidget(0)
        self.conn_live_table.set_rescan(True)
        self.conn_attic_table = ConnectionsTableWidget(0)
        self.conn_live_table.set_rescan(False)

        leftLayout.addWidget(self.conn_live_table)

        self.connection_details = QTextEdit()
        self.conn_live_table.set_details_widget(self.connection_details)
        self.conn_attic_table.set_details_widget(self.connection_details)
        self.connection_details.setReadOnly(True)
        self.connection_details.setWordWrapMode(QTextOption.NoWrap)
        self.connection_details.setFont(load_font_prog())

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        live_widget = QWidget()
        live_layout = QVBoxLayout()
        live_widget.setLayout(live_layout)
        live_layout.addWidget(self.conn_live_table)
        self.tab_widget.addTab(live_widget, "Live")

        attic_widget = QWidget()
        attic_layout = QVBoxLayout()
        attic_widget.setLayout(attic_layout)
        attic_layout.addWidget(self.conn_attic_table)
        self.tab_widget.addTab(attic_widget, "Attic")

        leftLayout.addWidget(self.tab_widget)
        rightLayout.addWidget(self.connection_details)

        self.setLayout(mainLayout)

        self.conn_live_table.removing_row.connect(self.on_live_connection_delete)

    def on_session_start(self, id: str, label: str, js: str):
        self.conn_live_table.add_connection(id, label, js)

    def on_session_stop(self, id: str, label: str, js: str):
        self.conn_live_table.stop_connection(id, label, js)

    def on_session_info(self, id: str, label: str, js: str):
        self.conn_live_table.add_connection_info(id, label, js)

    def on_live_connection_delete(self, row: int):

        self.conn_attic_table.insertRow(0)

        for col in range(self.conn_live_table.cfg.conn_headers_len):
            item = self.conn_live_table.item(row, col)

            new_item = QTableWidgetItem(item.text())
            new_item.setFont(self.conn_attic_table.table_font)
            new_item.setData(Qt.UserRole, item.data(Qt.UserRole))
            new_item.setData(Qt.UserRole + 1, item.data(Qt.UserRole))

            self.conn_attic_table.setItem(0, col, new_item)

        self.conn_attic_table.make_row_uneditable(0)
        self.conn_attic_table.resizeRowToContents(0)
        self.conn_attic_table.custom_resize_columns()

