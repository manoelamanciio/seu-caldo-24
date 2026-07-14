# -*- coding: utf-8 -*-
"""
Módulo PDV / Atendimento.
Sistema Seu Caldo 24 - M.A Sistemas
"""

from bson import ObjectId
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from db.database import get_db
from services.financeiro_service import FinanceiroService
from services.pdv_service import PdvService
from utils.helpers import alerta, confirmar, fmt_data, fmt_moeda, info


def _configurar_tabela(tabela):
    tabela.horizontalHeader().setSectionResizeMode(
        QHeaderView.Stretch
    )
    tabela.setEditTriggers(QTableWidget.NoEditTriggers)
    tabela.setSelectionBehavior(QTableWidget.SelectRows)
    tabela.setSelectionMode(QTableWidget.SingleSelection)


class AbrirComandaDialog(QDialog):
    def __init__(self, parent=None, usuario=None):
        super().__init__(parent)

        self.db = get_db()
        self.service = PdvService()
        self.usuario = usuario

        self.setWindowTitle("Abrir Comanda")
        self.setMinimumWidth(430)

        layout = QFormLayout(self)

        self.tipo = QComboBox()
        self.tipo.addItems(["Salão", "Balcão", "Delivery"])

        self.referencia = QLineEdit()
        self.referencia.setPlaceholderText(
            "Ex.: Mesa 03, balcão, nome do delivery"
        )

        self.cliente = QComboBox()
        self.cliente.addItem("(Nenhum)", None)

        for cliente in self.db.clientes.find(
            {"ativo": True}
        ).sort("nome_razao", 1):
            self.cliente.addItem(
                cliente.get("nome_razao", ""),
                str(cliente["_id"]),
            )

        layout.addRow("Atendimento:", self.tipo)
        layout.addRow("Referência:", self.referencia)
        layout.addRow("Cliente:", self.cliente)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(self.reject)

        abrir = QPushButton("Abrir comanda")
        abrir.clicked.connect(self._abrir)

        botoes.addWidget(cancelar)
        botoes.addWidget(abrir)

        layout.addRow(botoes)

    def _abrir(self):
        try:
            _, numero = self.service.abrir_comanda(
                self.tipo.currentText(),
                self.referencia.text(),
                self.cliente.currentData(),
                self.usuario,
            )

            info(
                self,
                "Comanda aberta",
                f"Comanda nº {numero} aberta com sucesso.",
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class FecharComandaDialog(QDialog):
    def __init__(self, parent=None, comanda=None):
        super().__init__(parent)

        self.service = PdvService()
        self.financeiro = FinanceiroService()
        self.comanda = comanda

        self.setWindowTitle("Fechar Comanda")
        self.setMinimumWidth(430)

        layout = QFormLayout(self)

        layout.addRow(
            "Comanda:",
            QLabel(str(comanda.get("numero", ""))),
        )
        layout.addRow(
            "Total:",
            QLabel(fmt_moeda(comanda.get("total", 0))),
        )

        self.forma = QComboBox()
        self.forma.addItems([
            "Dinheiro",
            "PIX",
            "Cartão Débito",
            "Cartão Crédito",
            "Correntista",
        ])

        self.conta = QComboBox()
        self.conta.addItem("(Caixa geral)", None)

        for conta in self.financeiro.listar_contas_bancarias():
            self.conta.addItem(
                conta.get("nome", ""),
                str(conta["_id"]),
            )

        layout.addRow("Forma de pagamento:", self.forma)
        layout.addRow("Conta de destino:", self.conta)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(self.reject)

        fechar = QPushButton("Confirmar fechamento")
        fechar.clicked.connect(self._fechar)

        botoes.addWidget(cancelar)
        botoes.addWidget(fechar)

        layout.addRow(botoes)

    def _fechar(self):
        try:
            numero = self.service.fechar_comanda(
                str(self.comanda["_id"]),
                self.forma.currentText(),
                self.conta.currentData(),
            )

            info(
                self,
                "Venda concluída",
                f"Venda nº {numero} concluída com sucesso.",
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class AbaComandas(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario
        self.db = get_db()
        self.service = PdvService()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        abrir = QPushButton("+ Abrir Comanda")
        abrir.clicked.connect(self._abrir_comanda)

        fechar = QPushButton("Fechar Comanda")
        fechar.clicked.connect(self._fechar_comanda)

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnPerigo")
        cancelar.clicked.connect(self._cancelar_comanda)

        topo.addWidget(abrir)
        topo.addWidget(fechar)
        topo.addWidget(cancelar)
        topo.addStretch()

        layout.addLayout(topo)

        area = QHBoxLayout()

        # Lista de comandas
        esquerda = QVBoxLayout()
        esquerda.addWidget(QLabel("Comandas abertas"))

        self.tabela_comandas = QTableWidget(0, 6)
        self.tabela_comandas.setHorizontalHeaderLabels([
            "Número",
            "Tipo",
            "Referência",
            "Cliente",
            "Total",
            "Aberta em",
        ])
        _configurar_tabela(self.tabela_comandas)
        self.tabela_comandas.itemSelectionChanged.connect(
            self._carregar_itens
        )

        esquerda.addWidget(self.tabela_comandas)

        # Itens da comanda
        direita = QVBoxLayout()
        direita.addWidget(QLabel("Itens da comanda"))

        linha_item = QHBoxLayout()

        self.produto = QComboBox()
        for produto in self.db.produtos.find().sort("nome", 1):
            self.produto.addItem(
                f"{produto.get('nome', '')} - {fmt_moeda(produto.get('preco_venda', 0))}",
                str(produto["_id"]),
            )

        self.quantidade = QDoubleSpinBox()
        self.quantidade.setRange(0.001, 999999)
        self.quantidade.setDecimals(3)
        self.quantidade.setValue(1)

        adicionar = QPushButton("Adicionar")
        adicionar.clicked.connect(self._adicionar_item)

        remover = QPushButton("Remover")
        remover.setObjectName("btnPerigo")
        remover.clicked.connect(self._remover_item)

        linha_item.addWidget(self.produto, 2)
        linha_item.addWidget(self.quantidade)
        linha_item.addWidget(adicionar)
        linha_item.addWidget(remover)

        direita.addLayout(linha_item)

        self.tabela_itens = QTableWidget(0, 4)
        self.tabela_itens.setHorizontalHeaderLabels([
            "Produto",
            "Quantidade",
            "Preço unitário",
            "Total",
        ])
        _configurar_tabela(self.tabela_itens)

        direita.addWidget(self.tabela_itens)

        ajustes = QHBoxLayout()

        self.desconto = QDoubleSpinBox()
        self.desconto.setPrefix("R$ ")
        self.desconto.setDecimals(2)
        self.desconto.setMaximum(999999)

        self.acrescimo = QDoubleSpinBox()
        self.acrescimo.setPrefix("R$ ")
        self.acrescimo.setDecimals(2)
        self.acrescimo.setMaximum(999999)

        aplicar = QPushButton("Aplicar ajustes")
        aplicar.setObjectName("btnSecundario")
        aplicar.clicked.connect(self._aplicar_ajustes)

        self.lbl_total = QLabel("Total: R$ 0,00")
        self.lbl_total.setStyleSheet(
            "font-size:18px; font-weight:bold;"
        )

        ajustes.addWidget(QLabel("Desconto:"))
        ajustes.addWidget(self.desconto)
        ajustes.addWidget(QLabel("Acréscimo:"))
        ajustes.addWidget(self.acrescimo)
        ajustes.addWidget(aplicar)
        ajustes.addStretch()
        ajustes.addWidget(self.lbl_total)

        direita.addLayout(ajustes)

        area.addLayout(esquerda, 1)
        area.addLayout(direita, 1)

        layout.addLayout(area)

        self.atualizar()

    def atualizar(self):
        comandas = self.service.listar_comandas("Aberta")

        self.tabela_comandas.setRowCount(0)

        for comanda in comandas:
            row = self.tabela_comandas.rowCount()
            self.tabela_comandas.insertRow(row)

            item_numero = QTableWidgetItem(
                str(comanda.get("numero", ""))
            )
            item_numero.setData(
                Qt.UserRole,
                str(comanda["_id"]),
            )

            valores = [
                item_numero,
                QTableWidgetItem(
                    comanda.get("tipo_atendimento", "")
                ),
                QTableWidgetItem(
                    comanda.get("referencia", "")
                ),
                QTableWidgetItem(
                    comanda.get("cliente_nome", "")
                ),
                QTableWidgetItem(
                    fmt_moeda(comanda.get("total", 0))
                ),
                QTableWidgetItem(
                    fmt_data(comanda.get("aberta_em"))
                ),
            ]

            for coluna, item in enumerate(valores):
                self.tabela_comandas.setItem(
                    row,
                    coluna,
                    item,
                )

        self._carregar_itens()

    def comanda_selecionada(self):
        row = self.tabela_comandas.currentRow()

        if row < 0:
            return None

        comanda_id = self.tabela_comandas.item(
            row,
            0,
        ).data(Qt.UserRole)

        return self.service.buscar_comanda(comanda_id)

    def _carregar_itens(self):
        comanda = self.comanda_selecionada()

        self.tabela_itens.setRowCount(0)

        if not comanda:
            self.lbl_total.setText("Total: R$ 0,00")
            return

        for item in comanda.get("itens", []):
            row = self.tabela_itens.rowCount()
            self.tabela_itens.insertRow(row)

            valores = [
                item.get("produto_nome", ""),
                item.get("quantidade", 0),
                fmt_moeda(item.get("preco_unit", 0)),
                fmt_moeda(item.get("total", 0)),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela_itens.setItem(
                    row,
                    coluna,
                    QTableWidgetItem(str(valor)),
                )

        self.desconto.setValue(
            float(comanda.get("desconto", 0))
        )
        self.acrescimo.setValue(
            float(comanda.get("acrescimo", 0))
        )
        self.lbl_total.setText(
            f"Total: {fmt_moeda(comanda.get('total', 0))}"
        )

    def _abrir_comanda(self):
        if AbrirComandaDialog(
            self,
            self.usuario,
        ).exec():
            self.atualizar()

    def _adicionar_item(self):
        comanda = self.comanda_selecionada()

        if not comanda:
            alerta(
                self,
                "Atenção",
                "Selecione uma comanda.",
            )
            return

        try:
            self.service.adicionar_item(
                str(comanda["_id"]),
                self.produto.currentData(),
                self.quantidade.value(),
            )
            self.atualizar()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))

    def _remover_item(self):
        comanda = self.comanda_selecionada()
        row = self.tabela_itens.currentRow()

        if not comanda or row < 0:
            alerta(
                self,
                "Atenção",
                "Selecione uma comanda e um item.",
            )
            return

        try:
            self.service.remover_item(
                str(comanda["_id"]),
                row,
            )
            self.atualizar()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))

    def _aplicar_ajustes(self):
        comanda = self.comanda_selecionada()

        if not comanda:
            alerta(
                self,
                "Atenção",
                "Selecione uma comanda.",
            )
            return

        try:
            self.service.aplicar_ajustes(
                str(comanda["_id"]),
                self.desconto.value(),
                self.acrescimo.value(),
            )
            self.atualizar()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))

    def _fechar_comanda(self):
        comanda = self.comanda_selecionada()

        if not comanda:
            alerta(
                self,
                "Atenção",
                "Selecione uma comanda.",
            )
            return

        if FecharComandaDialog(
            self,
            comanda,
        ).exec():
            self.atualizar()

    def _cancelar_comanda(self):
        comanda = self.comanda_selecionada()

        if not comanda:
            alerta(
                self,
                "Atenção",
                "Selecione uma comanda.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Cancelar Comanda")
        form = QFormLayout(dialog)

        motivo = QTextEdit()
        motivo.setFixedHeight(80)

        form.addRow("Motivo:", motivo)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Voltar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(dialog.reject)

        confirmar_btn = QPushButton("Cancelar comanda")
        confirmar_btn.setObjectName("btnPerigo")

        def executar():
            try:
                self.service.cancelar_comanda(
                    str(comanda["_id"]),
                    motivo.toPlainText(),
                )
                dialog.accept()
            except ValueError as exc:
                alerta(dialog, "Atenção", str(exc))

        confirmar_btn.clicked.connect(executar)

        botoes.addWidget(cancelar)
        botoes.addWidget(confirmar_btn)
        form.addRow(botoes)

        if dialog.exec():
            self.atualizar()


class AbaHistoricoVendas(QWidget):
    def __init__(self):
        super().__init__()

        self.service = PdvService()

        layout = QVBoxLayout(self)

        atualizar = QPushButton("Atualizar")
        atualizar.setObjectName("btnSecundario")
        atualizar.clicked.connect(self.atualizar)

        topo = QHBoxLayout()
        topo.addWidget(atualizar)
        topo.addStretch()

        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels([
            "Venda",
            "Data",
            "Atendimento",
            "Referência",
            "Cliente",
            "Pagamento",
            "Itens",
            "Total",
        ])
        _configurar_tabela(self.tabela)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        vendas = self.service.listar_vendas()

        self.tabela.setRowCount(0)

        for venda in vendas:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            valores = [
                venda.get("numero", ""),
                fmt_data(venda.get("data")),
                venda.get("tipo_atendimento", ""),
                venda.get("referencia", ""),
                venda.get("cliente_nome", ""),
                venda.get("forma_pagamento", ""),
                len(venda.get("itens", [])),
                fmt_moeda(venda.get("total", 0)),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela.setItem(
                    row,
                    coluna,
                    QTableWidgetItem(str(valor)),
                )


class PdvWidget(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        titulo = QLabel("PDV / Atendimento")
        titulo.setObjectName("tituloPagina")

        layout.addWidget(titulo)

        self.tabs = QTabWidget()

        self.aba_comandas = AbaComandas(usuario)
        self.aba_historico = AbaHistoricoVendas()

        self.tabs.addTab(
            self.aba_comandas,
            "Comandas / Mesas"
        )
        self.tabs.addTab(
            self.aba_historico,
            "Histórico de Vendas"
        )

        layout.addWidget(self.tabs)

    def atualizar(self):
        self.aba_comandas.atualizar()
        self.aba_historico.atualizar()