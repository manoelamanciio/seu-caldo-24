# -*- coding: utf-8 -*-
import bcrypt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                                QPushButton, QFrame, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from db.database import get_db
from config import EMPRESA


class LoginWindow(QWidget):
    def __init__(self, on_login_sucesso):
        super().__init__()
        self.on_login_sucesso = on_login_sucesso
        self.db = get_db()
        self.setWindowTitle(f"{EMPRESA['nome_fantasia']} - Login")
        self.resize(420, 480)
        self._montar_ui()

    def _montar_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("card")
        card.setProperty("class", "card")
        card.setFixedWidth(340)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)

        titulo = QLabel(EMPRESA["nome_fantasia"])
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setFont(QFont("Segoe UI", 22, QFont.Bold))
        titulo.setStyleSheet("color:#E8590C;")

        subtitulo = QLabel("Sistema de Gestão Integrada")
        subtitulo.setAlignment(Qt.AlignCenter)
        subtitulo.setStyleSheet("color:#aaaaaa;")

        status_conexao = QLabel("● Conectado ao banco de dados" if self.db.online else "● Sem conexão com o MongoDB")
        status_conexao.setAlignment(Qt.AlignCenter)
        status_conexao.setStyleSheet(f"color:{'#2ECC71' if self.db.online else '#E74C3C'}; font-size:11px;")

        self.input_login = QLineEdit()
        self.input_login.setPlaceholderText("Usuário")

        self.input_senha = QLineEdit()
        self.input_senha.setPlaceholderText("Senha")
        self.input_senha.setEchoMode(QLineEdit.Password)
        self.input_senha.returnPressed.connect(self._tentar_login)

        btn_entrar = QPushButton("Entrar")
        btn_entrar.setMinimumHeight(38)
        btn_entrar.clicked.connect(self._tentar_login)

        dica = QLabel("Usuário padrão: admin / Senha: admin123")
        dica.setAlignment(Qt.AlignCenter)
        dica.setStyleSheet("color:#666; font-size:10px;")

        rodape = QLabel(f"Desenvolvido por {EMPRESA['desenvolvido_por']}")
        rodape.setAlignment(Qt.AlignCenter)
        rodape.setStyleSheet("color:#555; font-size:10px; margin-top: 10px;")

        card_layout.addWidget(titulo)
        card_layout.addWidget(subtitulo)
        card_layout.addWidget(status_conexao)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.input_login)
        card_layout.addWidget(self.input_senha)
        card_layout.addWidget(btn_entrar)
        card_layout.addWidget(dica)

        layout.addWidget(card)
        layout.addWidget(rodape)

    def _tentar_login(self):
        login = self.input_login.text().strip()
        senha = self.input_senha.text().strip()

        if not login or not senha:
            QMessageBox.warning(self, "Atenção", "Informe usuário e senha.")
            return

        if not self.db.online:
            QMessageBox.critical(self, "Erro de conexão",
                                  "Não foi possível conectar ao MongoDB.\n"
                                  "Verifique se o serviço 'mongod' está em execução em localhost:27017.")
            return

        usuario = self.db.usuarios.find_one({"login": login, "ativo": True})
        if not usuario:
            QMessageBox.critical(self, "Erro", "Usuário não encontrado ou inativo.")
            return

        if not bcrypt.checkpw(senha.encode(), usuario["senha_hash"]):
            QMessageBox.critical(self, "Erro", "Senha incorreta.")
            return

        self.on_login_sucesso(usuario)