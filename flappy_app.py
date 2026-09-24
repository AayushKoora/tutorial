import sys

from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import flappy_game


class LauncherPage(QWidget):
    def __init__(self):
        super().__init__()

        title = QLabel("Flappy Bird")
        title.setStyleSheet("font-size: 28px; font-weight: bold; padding: 12px;")

        self.high_score_label = QLabel("High Score: 0")
        self.high_score_label.setStyleSheet("font-size: 18px; padding: 6px;")

        self.play_button = QPushButton("Play")
        self.play_button.setStyleSheet("font-size: 20px; padding: 16px;")

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(self.high_score_label)
        layout.addWidget(self.play_button)
        self.setLayout(layout)

    def set_high_score(self, high_score):
        self.high_score_label.setText(f"High Score: {high_score}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("flappy_app")
        self.resize(400, 300)

        self.high_score = 0

        self.page = LauncherPage()
        self.page.play_button.clicked.connect(self.on_play_clicked)
        self.setCentralWidget(self.page)

    def on_play_clicked(self):
        try:
            score = flappy_game.run_game()
        except Exception as error:
            QMessageBox.critical(self, "Flappy Bird Error", str(error))
            return

        if score > self.high_score:
            self.high_score = score
            self.page.set_high_score(self.high_score)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
