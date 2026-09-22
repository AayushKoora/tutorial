import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

BUTTONS = [
    ["7", "8", "9", "/"],
    ["4", "5", "6", "*"],
    ["1", "2", "3", "-"],
    ["0", ".", "=", "+"],
]


class CalculatorPage(QWidget):
    def __init__(self):
        super().__init__()

        self.display = QLabel("0")
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setStyleSheet("font-size: 32px; padding: 12px;")

        grid = QGridLayout()
        grid.setSpacing(6)

        for row, button_row in enumerate(BUTTONS):
            for col, label in enumerate(button_row):
                button = QPushButton(label)
                button.setStyleSheet("font-size: 20px; padding: 16px;")
                grid.addWidget(button, row, col)

        clear_button = QPushButton("C")
        clear_button.setStyleSheet("font-size: 20px; padding: 16px;")
        grid.addWidget(clear_button, len(BUTTONS), 0, 1, len(BUTTONS[0]))

        layout = QVBoxLayout()
        layout.addWidget(self.display)
        layout.addLayout(grid)
        self.setLayout(layout)


class CalculatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("calculator_app")
        self.resize(400, 500)
        self.setCentralWidget(CalculatorPage())


def main():
    app = QApplication(sys.argv)
    window = CalculatorApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
