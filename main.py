import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget


class HomePage(QWidget):
    def __init__(self):
        super().__init__()

        title = QLabel("Home Page")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addStretch()
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt Application")
        self.resize(800, 600)
        self.setCentralWidget(HomePage())


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
