import sys

from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import flappy_game
import scores_db


class LauncherPage(QWidget):
    def __init__(self):
        super().__init__()

        title = QLabel("Flappy Bird")
        title.setStyleSheet("font-size: 28px; font-weight: bold; padding: 12px;")

        self.player_list = QListWidget()

        self.new_name_edit = QLineEdit()
        self.new_name_edit.setPlaceholderText("New player name (press Enter)")

        self.best_score_label = QLabel("Best Score: —")
        self.best_score_label.setStyleSheet("font-size: 18px; padding: 6px;")

        self.play_button = QPushButton("Play")
        self.play_button.setStyleSheet("font-size: 20px; padding: 16px;")
        self.play_button.setEnabled(False)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(QLabel("Pick an existing player:"))
        layout.addWidget(self.player_list)
        layout.addWidget(self.new_name_edit)
        layout.addWidget(self.best_score_label)
        layout.addWidget(self.play_button)
        self.setLayout(layout)

    def set_players(self, names):
        self.player_list.clear()
        self.player_list.addItems(names)

    def set_best_score(self, best_score):
        self.best_score_label.setText(f"Best Score: {best_score}")

    def set_play_enabled(self, enabled):
        self.play_button.setEnabled(enabled)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("flappy_app")
        self.resize(400, 420)

        self.connection = scores_db.connect()
        self.selected_name = None
        self.selected_best_score = 0

        self.page = LauncherPage()
        self.page.set_players(scores_db.list_players(self.connection))
        self.page.player_list.itemSelectionChanged.connect(self.on_player_selected)
        self.page.new_name_edit.returnPressed.connect(self.on_new_name_confirmed)
        self.page.play_button.clicked.connect(self.on_play_clicked)
        self.setCentralWidget(self.page)

    def on_player_selected(self):
        items = self.page.player_list.selectedItems()
        if not items:
            return
        self.page.new_name_edit.clear()
        self.select_player(items[0].text())

    def on_new_name_confirmed(self):
        name = self.page.new_name_edit.text().strip()
        self.page.new_name_edit.clear()
        if not name:
            return

        self.select_player(name)
        self.refresh_player_list()

    def select_player(self, name):
        self.selected_name = name
        self.selected_best_score = scores_db.get_or_create_player(
            self.connection, name
        )
        self.page.set_best_score(self.selected_best_score)
        self.page.set_play_enabled(True)

    def refresh_player_list(self):
        self.page.player_list.blockSignals(True)
        self.page.set_players(scores_db.list_players(self.connection))
        for index in range(self.page.player_list.count()):
            item = self.page.player_list.item(index)
            if item.text() == self.selected_name:
                self.page.player_list.setCurrentItem(item)
                break
        self.page.player_list.blockSignals(False)

    def on_play_clicked(self):
        try:
            rounds = flappy_game.run_game(
                self.selected_name, self.selected_best_score
            )
        except Exception as error:
            QMessageBox.critical(self, "Flappy Bird Error", str(error))
            return

        for score, played_at in rounds:
            scores_db.log_round(self.connection, self.selected_name, score, played_at)

        self.selected_best_score = scores_db.get_or_create_player(
            self.connection, self.selected_name
        )
        self.page.set_best_score(self.selected_best_score)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
