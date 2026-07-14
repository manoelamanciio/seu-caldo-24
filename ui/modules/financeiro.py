# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class FinanceiroWidget(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario

        layout = QVBoxLayout(self)

        titulo = QLabel("Financeiro / Contas")
        titulo.setObjectName("tituloPagina")

        mensagem = QLabel("Módulo Financeiro em desenvolvimento.")

        layout.addWidget(titulo)
        layout.addWidget(mensagem)
        layout.addStretch()

    def atualizar(self):
        pass