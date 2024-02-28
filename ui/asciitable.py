from PyQt5.Qt import QApplication, QDialog, QTableWidget, QTableWidgetItem, QAbstractItemView, QVBoxLayout
import sys

from PyQt5.QtWidgets import QMainWindow, QPushButton, QLabel, QWidget, QSizePolicy


class AsciiTable(QDialog):
    AsciiNames = {
        0x00: "\\0",
        0x01: "SOH",
        0x02: "STX",
        0x03: "ETX",
        0x04: "EOT",
        0x05: "ENQ",
        0x06: "ACK",
        0x07: "\\a",
        0x08: "\\b",
        0x09: "\\t",
        0x0A: "\\n",
        0x0B: "\\v",
        0x0C: "\\f",
        0x0D: "\\r",
        0x0E: "SO",
        0x0F: "SI",
        0x10: "DLE",
        0x11: "DC1",
        0x12: "DC2",
        0x13: "DC3",
        0x14: "DC4",
        0x15: "NAK",
        0x16: "SYN",
        0x17: "ETB",
        0x18: "CAN",
        0x19: "EM",
        0x1A: "SUB",
        0x1B: "ESC",
        0x1C: "FS",
        0x1D: "GS",
        0x1E: "RS",
        0x1F: "US",
        0x7F: "DEL"
    }

    def __init__(self, parent=None):
        super(AsciiTable, self).__init__(parent)
        self.table = QTableWidget()
        self.table.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.table.setColumnCount(8)
        rows = 16
        self.table.setRowCount(rows)
        # Define column and row headers
        self.table.setHorizontalHeaderLabels([f"{i}" for i in range(8)])
        self.table.setVerticalHeaderLabels([f"0x{8*i:02X}_" for i in range(rows)])

        # Fill table with ASCII values
        for ascii_value in range(128):
            row = ascii_value // 8
            col = ascii_value % 8
            if ascii_value in AsciiTable.AsciiNames:
                item_value = AsciiTable.AsciiNames[ascii_value]
            elif 32 <= ascii_value <= 126:
                item_value = chr(ascii_value)
            else:
                item_value = f"{ascii_value:02x}"
            self.table.setItem(row, col, QTableWidgetItem(item_value))

        # Adjust column width and row height for better visibility
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        # Define selection behavior
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)

        # Calculate headers size
        vertical_header_width = self.table.verticalHeader().width()
        horizontal_header_height = self.table.horizontalHeader().height()
        total_rows_height = sum([self.table.rowHeight(i) for i in range(self.table.rowCount())])
        total_columns_width = sum([self.table.columnWidth(i) for i in range(self.table.columnCount())])

        self.table.setFixedWidth(total_columns_width + vertical_header_width + 52)
        self.table.setFixedHeight(total_rows_height + horizontal_header_height + 4)

        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(self.table)

        # Connect itemDoubleClicked signal to slot
        self.table.itemDoubleClicked.connect(self._item_double_clicked)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.adjustSize()

        # Store ASCII value on double click
        self.byte_value = None

    def _item_double_clicked(self, item):
        # self.byte_value = int(item.text(), 16)
        row = item.row()
        col = item.column()

        pos = row * 8 + col

        self.byte_value = int(pos)
        self.accept()  # close dialog

    def selectedByte(self) -> bytes:
        return self.byte_value

    def selectedHexStr(self) -> str:
        return f"{self.byte_value:02x}"

    def selectedDecStr(self) -> str:
        return f"{self.byte_value:02}"

