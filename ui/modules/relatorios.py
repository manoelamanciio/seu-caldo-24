# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class RelatoriosWidget(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario

        layout = QVBoxLayout(self)

        titulo = QLabel("Relatórios")
        titulo.setObjectName("tituloPagina")

        mensagem = QLabel("Módulo de Relatórios em desenvolvimento.")

        layout.addWidget(titulo)
        layout.addWidget(mensagem)
        layout.addStretch()

    def atualizar(self):
        pass