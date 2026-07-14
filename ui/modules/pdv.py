# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class PdvWidget(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario

        layout = QVBoxLayout(self)

        titulo = QLabel("PDV / Atendimento")
        titulo.setObjectName("tituloPagina")

        mensagem = QLabel("Módulo de PDV em desenvolvimento.")

        layout.addWidget(titulo)
        layout.addWidget(mensagem)
        layout.addStretch()

    def atualizar(self):
        pass