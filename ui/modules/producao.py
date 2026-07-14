# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class ProducaoWidget(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario

        layout = QVBoxLayout(self)

        titulo = QLabel("Produção / Cozinha")
        titulo.setObjectName("tituloPagina")

        mensagem = QLabel("Módulo de Produção em desenvolvimento.")

        layout.addWidget(titulo)
        layout.addWidget(mensagem)
        layout.addStretch()

    def atualizar(self):
        pass