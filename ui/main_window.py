# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                                QPushButton, QStackedWidget, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from config import EMPRESA
from db.database import get_db

from ui.modules.dashboard import DashboardWidget
from ui.modules.estoque import EstoqueWidget
from ui.modules.clientes import ClientesWidget
from ui.modules.producao import ProducaoWidget
from ui.modules.financeiro import FinanceiroWidget
from ui.modules.pdv import PdvWidget
from ui.modules.relatorios import RelatoriosWidget

from ui.modules.administracao import AdministracaoWidget


class MainWindow(QMainWindow):
    def __init__(self, usuario_logado):
        super().__init__()
        self.usuario = usuario_logado
        self.db = get_db()
        self.setWindowTitle(f"{EMPRESA['nome_fantasia']} - Sistema de Gestão | M.A Sistemas")
        self.resize(1360, 800)

        self.botoes_menu = {}
        self._montar_ui()

    # ------------------------------------------------------------------
    def _montar_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        layout_geral = QHBoxLayout(central)
        layout_geral.setContentsMargins(0, 0, 0, 0)
        layout_geral.setSpacing(0)

        # ---------------- Sidebar ----------------
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(2)

        logo = QLabel(EMPRESA["nome_fantasia"])
        logo.setObjectName("logo")
        sub = QLabel("M.A Sistemas")
        sub.setObjectName("subtitulo")

        sidebar_layout.addWidget(logo)
        sidebar_layout.addWidget(sub)
        sidebar_layout.addSpacing(20)

        self.stack = QStackedWidget()

        modulos = [
            ("📊  Dashboard", DashboardWidget),
            ("📦  Estoque", EstoqueWidget),
            ("🤝  Clientes / Fidelidade", ClientesWidget),
            ("👨‍🍳  Produção / Cozinha", ProducaoWidget),
            ("💰  Financeiro", FinanceiroWidget),
            ("🧾  PDV / Atendimento", PdvWidget),
            ("📑  Relatórios", RelatoriosWidget),
            ("⚙️  Administração", AdministracaoWidget),
        ]

        for i, (nome, classe) in enumerate(modulos):
            widget = classe(self.usuario)
            self.stack.addWidget(widget)

            btn = QPushButton(nome)
            btn.setObjectName("menuBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, idx=i, b=btn: self._trocar_pagina(idx, b))
            sidebar_layout.addWidget(btn)
            self.botoes_menu[i] = btn

        sidebar_layout.addStretch()

        rodape_usuario = QFrame()
        rodape_layout = QVBoxLayout(rodape_usuario)
        lbl_usuario = QLabel(f"👤 {self.usuario['nome']}")
        lbl_perfil = QLabel(self.usuario.get("perfil", ""))
        lbl_perfil.setStyleSheet("color:#888; font-size:11px;")
        rodape_layout.addWidget(lbl_usuario)
        rodape_layout.addWidget(lbl_perfil)
        sidebar_layout.addWidget(rodape_usuario)

        # ---------------- Conteúdo ----------------
        layout_geral.addWidget(sidebar)
        layout_geral.addWidget(self.stack, 1)

        self._trocar_pagina(0, self.botoes_menu[0])

    def _trocar_pagina(self, indice, botao):
        self.stack.setCurrentIndex(indice)
        for b in self.botoes_menu.values():
            b.setObjectName("menuBtn")
            b.style().unpolish(b)
            b.style().polish(b)
        botao.setObjectName("menuBtnAtivo")
        botao.style().unpolish(botao)
        botao.style().polish(botao)

        # Atualiza dados sempre que o usuário entra em uma aba (dados "vivos")
        widget_atual = self.stack.currentWidget()
        if hasattr(widget_atual, "atualizar"):
            widget_atual.atualizar()