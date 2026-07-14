# -*- coding: utf-8 -*-

import sys

from PySide6.QtWidgets import QApplication

from db.database import get_db
from ui.login import LoginWindow
from ui.main_window import MainWindow
from ui.theme import QSS


def iniciar():
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)

    db = get_db()

    if db.online:
        db.criar_indices()
        db.seed_inicial()

    janelas = {}

    def login_sucesso(usuario):
        janelas["principal"] = MainWindow(usuario)
        janelas["principal"].show()
        janelas["login"].close()

    janelas["login"] = LoginWindow(login_sucesso)
    janelas["login"].show()

    sys.exit(app.exec())


if __name__ == "__main__":
    iniciar()