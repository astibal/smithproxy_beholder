import sys

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, \
    QAbstractItemView, QShortcut
from ui.asciitable import AsciiTable


class HexEditorWidget(QWidget):
    data_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.indice_newline = []
        self.initUI()
        self.editing = False

    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.inputLineEdit = QLineEdit()
        self.loadButton = QPushButton("Load Data")
        self.tableWidget = QTableWidget()

        self.layout.addWidget(self.inputLineEdit)
        self.layout.addWidget(self.loadButton)
        self.layout.addWidget(self.tableWidget)
        self.outputButton = QPushButton("Copy PyBy")
        self.layout.addWidget(self.outputButton)

        self.loadButton.clicked.connect(self.load_data)
        self.outputButton.clicked.connect(self.on_output_button)

        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(16)  # Display 16 bytes per row
        for i in range(self.tableWidget.columnCount()):
            self.tableWidget.setColumnWidth(i, 20)

        self.tableWidget.setHorizontalHeaderLabels([f"{i:02X}" for i in range(16)])
        self.tableWidget.verticalHeader().setVisible(True)
        self.tableWidget.verticalHeader().setFixedWidth(40)

        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget.setSelectionMode(QAbstractItemView.NoSelection)
        self.tableWidget.resizeColumnsToContents()

        self.tableWidget.setStyleSheet("QTableView {"
                                       "gridline-color: #f0f0f0 "
                                       "}")

        self.tableWidget.doubleClicked.connect(self.on_item_double_clicked)
        self.shortcut_ins = QShortcut(QKeySequence(Qt.Key_Insert), self)
        self.shortcut_ins.activated.connect(self.insert_byte)

        # self.shortcut_return = QShortcut(QKeySequence(Qt.Key_Return), self)
        # self.shortcut_return.activated.connect(self.new_line)

        self.shortcut_f2 = QShortcut(QKeySequence(Qt.Key_F2), self)
        self.shortcut_f2.activated.connect(self.edit_current_cell)

        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_esc.activated.connect(self.esc_pressed)

        self.shortcut_t = QShortcut(QKeySequence(Qt.Key_F3), self)
        self.shortcut_t.activated.connect(self.t_pressed)

    def load_data(self):
        byte_data_str = self.inputLineEdit.text()
        try:
            byte_data = eval(byte_data_str, {"__builtins__": {}})
            if isinstance(byte_data, bytes):
                self.load_bytes(byte_data)
            else:
                print("Input is not a valid bytes object.")
        except (SyntaxError, NameError) as e:
            print(f"Invalid input: {e}")

        self.data_updated.emit()

    @staticmethod
    def byte_string(byte):
        if 32 <= byte < 127:
            return f"{chr(byte)}"
        else:
            return f"{byte:02X}"

    def load_bytes(self, byte_data: bytes | bytearray):
        self.tableWidget.clearContents()
        rows = len(byte_data) // 16 + (1 if len(byte_data) % 16 else 0)
        self.tableWidget.setRowCount(rows)
        self.tableWidget.setVerticalHeaderLabels([f"{16 * i:0002X}" for i in range(16)])

        for i, byte in enumerate(byte_data):

            item = QTableWidgetItem(self.byte_string(byte))
            if 32 <= byte < 127:
                item.setBackground(QColor(240, 255, 240))

            self.tableWidget.setItem(i // 16, i % 16, item)

        self.tableWidget.resizeColumnsToContents()

    def cell_byte(self, row: int, column: int):
        item = self.tableWidget.item(row, column)
        if item:
            str_item = item.text()
            if len(str_item) == 2:
                return int(str_item, 16)
            else:
                return ord(str_item)

    def get_bytes(self) -> bytes:
        bytesList = bytearray()
        for row in range(self.tableWidget.rowCount()):
            for column in range(self.tableWidget.columnCount()):
                byte = self.cell_byte(row, column)
                if byte is not None:
                    bytesList.append(byte)
        return bytes(bytesList)

    def on_output_button(self):
        bytes_ = self.get_bytes()
        self.inputLineEdit.setText(f"{repr(bytes_)} : OUT")

    def swap_cell_style(self, item):
        if item:
            row = item.row()
            col = item.column()
            item = self.tableWidget.item(row, col)
            str_item = item.text()
            if len(str_item) == 2:
                byte = int(str_item, 16)
                if 32 <= byte < 127:
                    item.setText(f"{chr(byte)}")
            else:
                byte = ord(str_item)
                item.setText(f"{byte:02X}")

    def on_item_double_clicked(self, item):
        self.swap_cell_style(item)

    def insert_byte(self):
        # Get currently selected item's position.
        current_item = self.tableWidget.currentItem()
        row = current_item.row()
        col = current_item.column()
        insert_pos = row * 16 + col
        # Insert a byte (e.g., 0) into the bytearray at the desired position.
        data = bytearray(self.get_bytes())
        data.insert(insert_pos, 0)
        self.load_bytes(bytes(data))

        self.tableWidget.setCurrentCell(row, col)

    def new_line(self):
        # Get currently selected item's position.
        current_item = self.tableWidget.currentItem()
        row = current_item.row()
        col = current_item.column()
        pos = row * 16 + col
        self.indice_newline.append(pos)

    def edit_current_cell(self):
        current_item = self.tableWidget.currentItem()
        self.tableWidget.editItem(current_item)

    def esc_pressed(self):
        current_item = self.tableWidget.currentItem()
        if current_item is not None:
            self.tableWidget.editItem(current_item)
        self.setFocus()

    def t_pressed(self):
        dialog = AsciiTable(self)
        if dialog.exec_():
            byte = dialog.selectedByte()
            self.tableWidget.currentItem().setText(self.byte_string(byte))


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication


    class MainWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.hexEditorWidget = HexEditorWidget()
            self.hexEditorWidget.data_updated.connect(self.on_new_data)
            self.layout = QVBoxLayout(self)
            self.layout.addWidget(self.hexEditorWidget)

        def on_new_data(self):
            pass


    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.resize(mainWindow.sizeHint())
    mainWindow.setMinimumWidth(1000)
    mainWindow.show()
    sys.exit(app.exec_())
