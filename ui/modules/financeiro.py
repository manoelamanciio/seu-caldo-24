# -*- coding: utf-8 -*-
"""
Módulo Financeiro.
Sistema Seu Caldo 24 - M.A Sistemas
"""

import datetime

from bson import ObjectId
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
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
from utils.helpers import alerta, confirmar, fmt_data, fmt_moeda, info


def _configurar_tabela(tabela):
    tabela.horizontalHeader().setSectionResizeMode(
        QHeaderView.Stretch
    )
    tabela.setEditTriggers(QTableWidget.NoEditTriggers)
    tabela.setSelectionBehavior(QTableWidget.SelectRows)
    tabela.setSelectionMode(QTableWidget.SingleSelection)


def _to_datetime(qdate):
    data = qdate.toPython()
    return datetime.datetime.combine(
        data,
        datetime.time(12, 0),
    )


class ContaPagarDialog(QDialog):
    def __init__(self, parent=None, conta=None):
        super().__init__(parent)

        self.db = get_db()
        self.service = FinanceiroService()
        self.conta = conta

        self.setWindowTitle(
            "Editar Conta a Pagar"
            if conta
            else "Nova Conta a Pagar"
        )
        self.setMinimumWidth(500)

        layout = QFormLayout(self)

        self.descricao = QLineEdit()

        self.fornecedor = QComboBox()
        self.fornecedor.addItem("(Nenhum)", None)
        for item in self.db.fornecedores.find().sort("nome", 1):
            self.fornecedor.addItem(
                item.get("nome", ""),
                str(item["_id"]),
            )

        self.categoria = QLineEdit()
        self.categoria.setPlaceholderText(
            "Ex.: Insumos, aluguel, energia"
        )

        self.centro_custo = QComboBox()
        self.centro_custo.addItems([
            "Loja",
            "Cozinha",
            "Depósito",
            "Administrativo",
            "Marketing",
            "Outros",
        ])

        self.valor = QDoubleSpinBox()
        self.valor.setPrefix("R$ ")
        self.valor.setDecimals(2)
        self.valor.setMaximum(99999999)

        self.vencimento = QDateEdit()
        self.vencimento.setCalendarPopup(True)
        self.vencimento.setDate(QDate.currentDate())

        self.forma_pagamento = QComboBox()
        self.forma_pagamento.addItems([
            "Dinheiro",
            "PIX",
            "Boleto",
            "Cartão",
            "Transferência",
            "Débito automático",
            "Outro",
        ])

        self.observacoes = QTextEdit()
        self.observacoes.setFixedHeight(80)

        layout.addRow("Descrição:", self.descricao)
        layout.addRow("Fornecedor:", self.fornecedor)
        layout.addRow("Categoria:", self.categoria)
        layout.addRow("Centro de custo:", self.centro_custo)
        layout.addRow("Valor:", self.valor)
        layout.addRow("Vencimento:", self.vencimento)
        layout.addRow("Forma de pagamento:", self.forma_pagamento)
        layout.addRow("Observações:", self.observacoes)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(self.reject)

        salvar = QPushButton("Salvar")
        salvar.clicked.connect(self._salvar)

        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)

        layout.addRow(botoes)

        if conta:
            self._preencher(conta)

    def _preencher(self, conta):
        self.descricao.setText(conta.get("descricao", ""))

        fornecedor_id = conta.get("fornecedor_id")
        idx = self.fornecedor.findData(fornecedor_id)
        if idx >= 0:
            self.fornecedor.setCurrentIndex(idx)

        self.categoria.setText(conta.get("categoria", ""))
        self.centro_custo.setCurrentText(
            conta.get("centro_custo", "Loja")
        )
        self.valor.setValue(float(conta.get("valor", 0)))

        vencimento = conta.get("vencimento")
        if vencimento:
            self.vencimento.setDate(
                QDate(
                    vencimento.year,
                    vencimento.month,
                    vencimento.day,
                )
            )

        self.forma_pagamento.setCurrentText(
            conta.get("forma_pagamento", "Dinheiro")
        )
        self.observacoes.setPlainText(
            conta.get("observacoes", "")
        )

    def _salvar(self):
        fornecedor_id = self.fornecedor.currentData()
        fornecedor_nome = self.fornecedor.currentText()
        if not fornecedor_id:
            fornecedor_nome = ""

        dados = {
            "descricao": self.descricao.text(),
            "fornecedor_id": fornecedor_id,
            "fornecedor_nome": fornecedor_nome,
            "categoria": self.categoria.text(),
            "centro_custo": self.centro_custo.currentText(),
            "valor": self.valor.value(),
            "vencimento": _to_datetime(
                self.vencimento.date()
            ),
            "forma_pagamento": (
                self.forma_pagamento.currentText()
            ),
            "observacoes": self.observacoes.toPlainText(),
            "status": (
                self.conta.get("status", "Pendente")
                if self.conta
                else "Pendente"
            ),
            "valor_pago": (
                self.conta.get("valor_pago", 0)
                if self.conta
                else 0
            ),
        }

        try:
            conta_id = (
                str(self.conta["_id"])
                if self.conta
                else None
            )
            self.service.salvar_conta_pagar(
                dados,
                conta_id=conta_id,
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class ContaReceberDialog(QDialog):
    def __init__(self, parent=None, conta=None):
        super().__init__(parent)

        self.db = get_db()
        self.service = FinanceiroService()
        self.conta = conta

        self.setWindowTitle(
            "Editar Conta a Receber"
            if conta
            else "Nova Conta a Receber"
        )
        self.setMinimumWidth(500)

        layout = QFormLayout(self)

        self.descricao = QLineEdit()

        self.cliente = QComboBox()
        self.cliente.addItem("(Nenhum)", None)
        for item in self.db.clientes.find().sort("nome_razao", 1):
            self.cliente.addItem(
                item.get("nome_razao", ""),
                str(item["_id"]),
            )

        self.categoria = QLineEdit()
        self.categoria.setPlaceholderText(
            "Ex.: Venda, serviço, correntista"
        )

        self.valor = QDoubleSpinBox()
        self.valor.setPrefix("R$ ")
        self.valor.setDecimals(2)
        self.valor.setMaximum(99999999)

        self.vencimento = QDateEdit()
        self.vencimento.setCalendarPopup(True)
        self.vencimento.setDate(QDate.currentDate())

        self.forma_recebimento = QComboBox()
        self.forma_recebimento.addItems([
            "Dinheiro",
            "PIX",
            "Cartão Débito",
            "Cartão Crédito",
            "Boleto",
            "Transferência",
            "Outro",
        ])

        self.observacoes = QTextEdit()
        self.observacoes.setFixedHeight(80)

        layout.addRow("Descrição:", self.descricao)
        layout.addRow("Cliente:", self.cliente)
        layout.addRow("Categoria:", self.categoria)
        layout.addRow("Valor:", self.valor)
        layout.addRow("Vencimento:", self.vencimento)
        layout.addRow("Forma de recebimento:", self.forma_recebimento)
        layout.addRow("Observações:", self.observacoes)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(self.reject)

        salvar = QPushButton("Salvar")
        salvar.clicked.connect(self._salvar)

        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)

        layout.addRow(botoes)

        if conta:
            self._preencher(conta)

    def _preencher(self, conta):
        self.descricao.setText(conta.get("descricao", ""))

        cliente_id = conta.get("cliente_id")
        idx = self.cliente.findData(cliente_id)
        if idx >= 0:
            self.cliente.setCurrentIndex(idx)

        self.categoria.setText(conta.get("categoria", ""))
        self.valor.setValue(float(conta.get("valor", 0)))

        vencimento = conta.get("vencimento")
        if vencimento:
            self.vencimento.setDate(
                QDate(
                    vencimento.year,
                    vencimento.month,
                    vencimento.day,
                )
            )

        self.forma_recebimento.setCurrentText(
            conta.get("forma_recebimento", "Dinheiro")
        )
        self.observacoes.setPlainText(
            conta.get("observacoes", "")
        )

    def _salvar(self):
        cliente_id = self.cliente.currentData()
        cliente_nome = self.cliente.currentText()
        if not cliente_id:
            cliente_nome = ""

        dados = {
            "descricao": self.descricao.text(),
            "cliente_id": cliente_id,
            "cliente_nome": cliente_nome,
            "categoria": self.categoria.text(),
            "valor": self.valor.value(),
            "vencimento": _to_datetime(
                self.vencimento.date()
            ),
            "forma_recebimento": (
                self.forma_recebimento.currentText()
            ),
            "observacoes": self.observacoes.toPlainText(),
            "status": (
                self.conta.get("status", "Pendente")
                if self.conta
                else "Pendente"
            ),
            "valor_recebido": (
                self.conta.get("valor_recebido", 0)
                if self.conta
                else 0
            ),
        }

        try:
            conta_id = (
                str(self.conta["_id"])
                if self.conta
                else None
            )
            self.service.salvar_conta_receber(
                dados,
                conta_id=conta_id,
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class MovimentoCaixaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.service = FinanceiroService()

        self.setWindowTitle("Novo Movimento de Caixa")
        self.setMinimumWidth(450)

        layout = QFormLayout(self)

        self.tipo = QComboBox()
        self.tipo.addItems(["Entrada", "Saída"])

        self.descricao = QLineEdit()

        self.valor = QDoubleSpinBox()
        self.valor.setPrefix("R$ ")
        self.valor.setDecimals(2)
        self.valor.setMaximum(99999999)

        self.categoria = QLineEdit()
        self.centro_custo = QComboBox()
        self.centro_custo.addItems([
            "Loja",
            "Cozinha",
            "Depósito",
            "Administrativo",
            "Marketing",
            "Outros",
        ])

        self.conta = QComboBox()
        self.conta.addItem("(Caixa geral)", None)
        for item in self.service.listar_contas_bancarias():
            self.conta.addItem(
                item.get("nome", ""),
                str(item["_id"]),
            )

        layout.addRow("Tipo:", self.tipo)
        layout.addRow("Descrição:", self.descricao)
        layout.addRow("Valor:", self.valor)
        layout.addRow("Categoria:", self.categoria)
        layout.addRow("Centro de custo:", self.centro_custo)
        layout.addRow("Conta:", self.conta)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(self.reject)

        salvar = QPushButton("Registrar")
        salvar.clicked.connect(self._salvar)

        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)

        layout.addRow(botoes)

    def _salvar(self):
        try:
            self.service.registrar_movimento_caixa(
                tipo=self.tipo.currentText(),
                descricao=self.descricao.text(),
                valor=self.valor.value(),
                categoria=self.categoria.text(),
                centro_custo=self.centro_custo.currentText(),
                conta_bancaria_id=self.conta.currentData(),
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class ContaBancariaDialog(QDialog):
    def __init__(self, parent=None, conta=None):
        super().__init__(parent)

        self.service = FinanceiroService()
        self.conta = conta

        self.setWindowTitle(
            "Editar Conta Bancária"
            if conta
            else "Nova Conta Bancária"
        )
        self.setMinimumWidth(430)

        layout = QFormLayout(self)

        self.nome = QLineEdit()
        self.banco = QLineEdit()
        self.agencia = QLineEdit()
        self.numero_conta = QLineEdit()

        self.tipo = QComboBox()
        self.tipo.addItems([
            "Conta Corrente",
            "Conta Poupança",
            "Conta Digital",
            "Caixa",
        ])

        self.saldo = QDoubleSpinBox()
        self.saldo.setPrefix("R$ ")
        self.saldo.setDecimals(2)
        self.saldo.setRange(-99999999, 99999999)

        self.ativo = QCheckBox("Conta ativa")
        self.ativo.setChecked(True)

        layout.addRow("Nome interno:", self.nome)
        layout.addRow("Banco:", self.banco)
        layout.addRow("Agência:", self.agencia)
        layout.addRow("Número da conta:", self.numero_conta)
        layout.addRow("Tipo:", self.tipo)
        layout.addRow("Saldo atual:", self.saldo)
        layout.addRow("Status:", self.ativo)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(self.reject)

        salvar = QPushButton("Salvar")
        salvar.clicked.connect(self._salvar)

        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)

        layout.addRow(botoes)

        if conta:
            self.nome.setText(conta.get("nome", ""))
            self.banco.setText(conta.get("banco", ""))
            self.agencia.setText(conta.get("agencia", ""))
            self.numero_conta.setText(
                conta.get("numero_conta", "")
            )
            self.tipo.setCurrentText(
                conta.get("tipo", "Conta Corrente")
            )
            self.saldo.setValue(
                float(conta.get("saldo_atual", 0))
            )
            self.ativo.setChecked(
                conta.get("ativo", True)
            )

    def _salvar(self):
        try:
            conta_id = (
                str(self.conta["_id"])
                if self.conta
                else None
            )
            self.service.salvar_conta_bancaria(
                {
                    "nome": self.nome.text(),
                    "banco": self.banco.text(),
                    "agencia": self.agencia.text(),
                    "numero_conta": self.numero_conta.text(),
                    "tipo": self.tipo.currentText(),
                    "saldo_atual": self.saldo.value(),
                    "ativo": self.ativo.isChecked(),
                },
                conta_id=conta_id,
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class OperadoraCartaoDialog(QDialog):
    def __init__(self, parent=None, operadora=None):
        super().__init__(parent)

        self.service = FinanceiroService()
        self.operadora = operadora

        self.setWindowTitle(
            "Editar Operadora"
            if operadora
            else "Nova Operadora de Cartão"
        )
        self.setMinimumWidth(430)

        layout = QFormLayout(self)

        self.nome = QLineEdit()

        self.taxa_debito = QDoubleSpinBox()
        self.taxa_debito.setSuffix(" %")
        self.taxa_debito.setDecimals(2)
        self.taxa_debito.setMaximum(100)

        self.taxa_credito = QDoubleSpinBox()
        self.taxa_credito.setSuffix(" %")
        self.taxa_credito.setDecimals(2)
        self.taxa_credito.setMaximum(100)

        self.prazo_debito = QDoubleSpinBox()
        self.prazo_debito.setSuffix(" dias")
        self.prazo_debito.setDecimals(0)
        self.prazo_debito.setMaximum(365)

        self.prazo_credito = QDoubleSpinBox()
        self.prazo_credito.setSuffix(" dias")
        self.prazo_credito.setDecimals(0)
        self.prazo_credito.setMaximum(365)

        self.ativo = QCheckBox("Operadora ativa")
        self.ativo.setChecked(True)

        layout.addRow("Nome:", self.nome)
        layout.addRow("Taxa débito:", self.taxa_debito)
        layout.addRow("Taxa crédito:", self.taxa_credito)
        layout.addRow("Prazo débito:", self.prazo_debito)
        layout.addRow("Prazo crédito:", self.prazo_credito)
        layout.addRow("Status:", self.ativo)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(self.reject)

        salvar = QPushButton("Salvar")
        salvar.clicked.connect(self._salvar)

        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)

        layout.addRow(botoes)

        if operadora:
            self.nome.setText(operadora.get("nome", ""))
            self.taxa_debito.setValue(
                float(operadora.get("taxa_debito", 0))
            )
            self.taxa_credito.setValue(
                float(operadora.get("taxa_credito", 0))
            )
            self.prazo_debito.setValue(
                int(operadora.get("prazo_debito", 1))
            )
            self.prazo_credito.setValue(
                int(operadora.get("prazo_credito", 30))
            )
            self.ativo.setChecked(
                operadora.get("ativo", True)
            )

    def _salvar(self):
        try:
            operadora_id = (
                str(self.operadora["_id"])
                if self.operadora
                else None
            )
            self.service.salvar_operadora_cartao(
                {
                    "nome": self.nome.text(),
                    "taxa_debito": self.taxa_debito.value(),
                    "taxa_credito": self.taxa_credito.value(),
                    "prazo_debito": int(
                        self.prazo_debito.value()
                    ),
                    "prazo_credito": int(
                        self.prazo_credito.value()
                    ),
                    "ativo": self.ativo.isChecked(),
                },
                operadora_id=operadora_id,
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class AbaContasPagar(QWidget):
    def __init__(self):
        super().__init__()

        self.service = FinanceiroService()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        self.busca = QLineEdit()
        self.busca.setPlaceholderText(
            "Buscar conta, fornecedor ou categoria..."
        )
        self.busca.textChanged.connect(self.atualizar)

        self.status = QComboBox()
        self.status.addItems([
            "Todos",
            "Pendente",
            "Parcial",
            "Paga",
        ])
        self.status.currentTextChanged.connect(self.atualizar)

        novo = QPushButton("+ Nova Conta")
        novo.clicked.connect(self._novo)

        editar = QPushButton("Editar")
        editar.setObjectName("btnSecundario")
        editar.clicked.connect(self._editar)

        pagar = QPushButton("Registrar pagamento")
        pagar.clicked.connect(self._pagar)

        excluir = QPushButton("Excluir")
        excluir.setObjectName("btnPerigo")
        excluir.clicked.connect(self._excluir)

        topo.addWidget(self.busca, 1)
        topo.addWidget(self.status)
        topo.addWidget(novo)
        topo.addWidget(editar)
        topo.addWidget(pagar)
        topo.addWidget(excluir)

        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels([
            "Descrição",
            "Fornecedor",
            "Categoria",
            "Centro de custo",
            "Vencimento",
            "Valor",
            "Pago",
            "Status",
        ])
        _configurar_tabela(self.tabela)
        self.tabela.doubleClicked.connect(self._editar)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        contas = self.service.listar_contas_pagar(
            self.status.currentText(),
            self.busca.text(),
        )

        self.tabela.setRowCount(0)

        for conta in contas:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            item = QTableWidgetItem(
                conta.get("descricao", "")
            )
            item.setData(Qt.UserRole, str(conta["_id"]))

            valores = [
                item,
                QTableWidgetItem(
                    conta.get("fornecedor_nome", "")
                ),
                QTableWidgetItem(
                    conta.get("categoria", "")
                ),
                QTableWidgetItem(
                    conta.get("centro_custo", "")
                ),
                QTableWidgetItem(
                    fmt_data(conta.get("vencimento"))
                ),
                QTableWidgetItem(
                    fmt_moeda(conta.get("valor", 0))
                ),
                QTableWidgetItem(
                    fmt_moeda(conta.get("valor_pago", 0))
                ),
                QTableWidgetItem(
                    conta.get("status", "")
                ),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela.setItem(row, coluna, valor)

    def conta_selecionada(self):
        row = self.tabela.currentRow()
        if row < 0:
            return None

        conta_id = self.tabela.item(
            row,
            0,
        ).data(Qt.UserRole)

        return self.service.db.contas_pagar.find_one({
            "_id": ObjectId(conta_id)
        })

    def _novo(self):
        if ContaPagarDialog(self).exec():
            self.atualizar()

    def _editar(self):
        conta = self.conta_selecionada()
        if not conta:
            alerta(self, "Atenção", "Selecione uma conta.")
            return

        if ContaPagarDialog(self, conta).exec():
            self.atualizar()

    def _pagar(self):
        conta = self.conta_selecionada()
        if not conta:
            alerta(self, "Atenção", "Selecione uma conta.")
            return

        restante = (
            float(conta.get("valor", 0))
            - float(conta.get("valor_pago", 0))
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Registrar pagamento")
        form = QFormLayout(dialog)

        valor = QDoubleSpinBox()
        valor.setPrefix("R$ ")
        valor.setDecimals(2)
        valor.setMaximum(restante)
        valor.setValue(restante)

        conta_bancaria = QComboBox()
        conta_bancaria.addItem("(Caixa geral)", None)
        for item in self.service.listar_contas_bancarias():
            conta_bancaria.addItem(
                item.get("nome", ""),
                str(item["_id"]),
            )

        form.addRow("Valor:", valor)
        form.addRow("Conta:", conta_bancaria)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(dialog.reject)

        confirmar_btn = QPushButton("Confirmar")

        def executar():
            try:
                self.service.pagar_conta(
                    str(conta["_id"]),
                    valor.value(),
                    conta_bancaria.currentData(),
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

    def _excluir(self):
        conta = self.conta_selecionada()
        if not conta:
            alerta(self, "Atenção", "Selecione uma conta.")
            return

        if not confirmar(
            self,
            "Confirmar",
            f"Excluir '{conta.get('descricao', '')}'?",
        ):
            return

        try:
            self.service.excluir_conta_pagar(
                str(conta["_id"])
            )
            self.atualizar()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class AbaContasReceber(QWidget):
    def __init__(self):
        super().__init__()

        self.service = FinanceiroService()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        self.busca = QLineEdit()
        self.busca.setPlaceholderText(
            "Buscar conta, cliente ou categoria..."
        )
        self.busca.textChanged.connect(self.atualizar)

        self.status = QComboBox()
        self.status.addItems([
            "Todos",
            "Pendente",
            "Parcial",
            "Faturado",
            "Recebida",
        ])
        self.status.currentTextChanged.connect(self.atualizar)

        novo = QPushButton("+ Nova Conta")
        novo.clicked.connect(self._novo)

        editar = QPushButton("Editar")
        editar.setObjectName("btnSecundario")
        editar.clicked.connect(self._editar)

        receber = QPushButton("Registrar recebimento")
        receber.clicked.connect(self._receber)

        excluir = QPushButton("Excluir")
        excluir.setObjectName("btnPerigo")
        excluir.clicked.connect(self._excluir)

        topo.addWidget(self.busca, 1)
        topo.addWidget(self.status)
        topo.addWidget(novo)
        topo.addWidget(editar)
        topo.addWidget(receber)
        topo.addWidget(excluir)

        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 7)
        self.tabela.setHorizontalHeaderLabels([
            "Descrição",
            "Cliente",
            "Categoria",
            "Vencimento",
            "Valor",
            "Recebido",
            "Status",
        ])
        _configurar_tabela(self.tabela)
        self.tabela.doubleClicked.connect(self._editar)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        contas = self.service.listar_contas_receber(
            self.status.currentText(),
            self.busca.text(),
        )

        self.tabela.setRowCount(0)

        for conta in contas:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            item = QTableWidgetItem(
                conta.get("descricao", "")
            )
            item.setData(Qt.UserRole, str(conta["_id"]))

            valores = [
                item,
                QTableWidgetItem(
                    conta.get("cliente_nome", "")
                ),
                QTableWidgetItem(
                    conta.get("categoria", "")
                ),
                QTableWidgetItem(
                    fmt_data(conta.get("vencimento"))
                ),
                QTableWidgetItem(
                    fmt_moeda(conta.get("valor", 0))
                ),
                QTableWidgetItem(
                    fmt_moeda(
                        conta.get("valor_recebido", 0)
                    )
                ),
                QTableWidgetItem(
                    conta.get("status", "")
                ),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela.setItem(row, coluna, valor)

    def conta_selecionada(self):
        row = self.tabela.currentRow()
        if row < 0:
            return None

        conta_id = self.tabela.item(
            row,
            0,
        ).data(Qt.UserRole)

        return self.service.db.contas_receber.find_one({
            "_id": ObjectId(conta_id)
        })

    def _novo(self):
        if ContaReceberDialog(self).exec():
            self.atualizar()

    def _editar(self):
        conta = self.conta_selecionada()
        if not conta:
            alerta(self, "Atenção", "Selecione uma conta.")
            return

        if ContaReceberDialog(self, conta).exec():
            self.atualizar()

    def _receber(self):
        conta = self.conta_selecionada()
        if not conta:
            alerta(self, "Atenção", "Selecione uma conta.")
            return

        restante = (
            float(conta.get("valor", 0))
            - float(conta.get("valor_recebido", 0))
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Registrar recebimento")
        form = QFormLayout(dialog)

        valor = QDoubleSpinBox()
        valor.setPrefix("R$ ")
        valor.setDecimals(2)
        valor.setMaximum(restante)
        valor.setValue(restante)

        conta_bancaria = QComboBox()
        conta_bancaria.addItem("(Caixa geral)", None)
        for item in self.service.listar_contas_bancarias():
            conta_bancaria.addItem(
                item.get("nome", ""),
                str(item["_id"]),
            )

        form.addRow("Valor:", valor)
        form.addRow("Conta:", conta_bancaria)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(dialog.reject)

        confirmar_btn = QPushButton("Confirmar")

        def executar():
            try:
                self.service.receber_conta(
                    str(conta["_id"]),
                    valor.value(),
                    conta_bancaria.currentData(),
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

    def _excluir(self):
        conta = self.conta_selecionada()
        if not conta:
            alerta(self, "Atenção", "Selecione uma conta.")
            return

        if not confirmar(
            self,
            "Confirmar",
            f"Excluir '{conta.get('descricao', '')}'?",
        ):
            return

        try:
            self.service.excluir_conta_receber(
                str(conta["_id"])
            )
            self.atualizar()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class AbaFluxoCaixa(QWidget):
    def __init__(self):
        super().__init__()

        self.service = FinanceiroService()

        layout = QVBoxLayout(self)

        filtros = QHBoxLayout()

        self.inicio = QDateEdit()
        self.inicio.setCalendarPopup(True)
        self.inicio.setDate(
            QDate.currentDate().addMonths(-1)
        )

        self.fim = QDateEdit()
        self.fim.setCalendarPopup(True)
        self.fim.setDate(QDate.currentDate())

        atualizar = QPushButton("Atualizar")
        atualizar.setObjectName("btnSecundario")
        atualizar.clicked.connect(self.atualizar)

        novo = QPushButton("+ Novo Movimento")
        novo.clicked.connect(self._novo)

        filtros.addWidget(QLabel("Início:"))
        filtros.addWidget(self.inicio)
        filtros.addWidget(QLabel("Fim:"))
        filtros.addWidget(self.fim)
        filtros.addWidget(atualizar)
        filtros.addWidget(novo)
        filtros.addStretch()

        layout.addLayout(filtros)

        kpis = QHBoxLayout()

        self.lbl_entradas = QLabel("Entradas: R$ 0,00")
        self.lbl_saidas = QLabel("Saídas: R$ 0,00")
        self.lbl_saldo = QLabel("Saldo: R$ 0,00")

        for label in (
            self.lbl_entradas,
            self.lbl_saidas,
            self.lbl_saldo,
        ):
            label.setStyleSheet(
                "font-size:16px; font-weight:bold;"
            )
            kpis.addWidget(label)

        kpis.addStretch()
        layout.addLayout(kpis)

        self.tabela = QTableWidget(0, 7)
        self.tabela.setHorizontalHeaderLabels([
            "Data",
            "Tipo",
            "Descrição",
            "Categoria",
            "Centro de custo",
            "Conta",
            "Valor",
        ])
        _configurar_tabela(self.tabela)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        inicio = datetime.datetime.combine(
            self.inicio.date().toPython(),
            datetime.time.min,
        )
        fim = datetime.datetime.combine(
            self.fim.date().toPython(),
            datetime.time.max,
        )

        movimentos = self.service.listar_movimentos(
            inicio,
            fim,
        )
        resumo = self.service.resumo_fluxo(
            inicio,
            fim,
        )

        self.lbl_entradas.setText(
            f"Entradas: {fmt_moeda(resumo['entradas'])}"
        )
        self.lbl_saidas.setText(
            f"Saídas: {fmt_moeda(resumo['saidas'])}"
        )
        self.lbl_saldo.setText(
            f"Saldo: {fmt_moeda(resumo['saldo'])}"
        )

        self.tabela.setRowCount(0)

        for movimento in movimentos:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            valores = [
                fmt_data(movimento.get("data")),
                movimento.get("tipo", ""),
                movimento.get("descricao", ""),
                movimento.get("categoria", ""),
                movimento.get("centro_custo", ""),
                movimento.get("conta_bancaria_nome", ""),
                fmt_moeda(movimento.get("valor", 0)),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela.setItem(
                    row,
                    coluna,
                    QTableWidgetItem(str(valor)),
                )

    def _novo(self):
        if MovimentoCaixaDialog(self).exec():
            self.atualizar()


class AbaContasBancarias(QWidget):
    def __init__(self):
        super().__init__()

        self.service = FinanceiroService()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        novo = QPushButton("+ Nova Conta Bancária")
        novo.clicked.connect(self._novo)

        editar = QPushButton("Editar")
        editar.setObjectName("btnSecundario")
        editar.clicked.connect(self._editar)

        topo.addWidget(novo)
        topo.addWidget(editar)
        topo.addStretch()

        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 7)
        self.tabela.setHorizontalHeaderLabels([
            "Nome",
            "Banco",
            "Agência",
            "Conta",
            "Tipo",
            "Saldo",
            "Status",
        ])
        _configurar_tabela(self.tabela)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        contas = self.service.listar_contas_bancarias()

        self.tabela.setRowCount(0)

        for conta in contas:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            item = QTableWidgetItem(conta.get("nome", ""))
            item.setData(Qt.UserRole, str(conta["_id"]))

            valores = [
                item,
                QTableWidgetItem(conta.get("banco", "")),
                QTableWidgetItem(conta.get("agencia", "")),
                QTableWidgetItem(
                    conta.get("numero_conta", "")
                ),
                QTableWidgetItem(conta.get("tipo", "")),
                QTableWidgetItem(
                    fmt_moeda(conta.get("saldo_atual", 0))
                ),
                QTableWidgetItem(
                    "Ativa"
                    if conta.get("ativo", True)
                    else "Inativa"
                ),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela.setItem(row, coluna, valor)

    def conta_selecionada(self):
        row = self.tabela.currentRow()
        if row < 0:
            return None

        conta_id = self.tabela.item(
            row,
            0,
        ).data(Qt.UserRole)

        return self.service.db.contas_bancarias.find_one({
            "_id": ObjectId(conta_id)
        })

    def _novo(self):
        if ContaBancariaDialog(self).exec():
            self.atualizar()

    def _editar(self):
        conta = self.conta_selecionada()
        if not conta:
            alerta(
                self,
                "Atenção",
                "Selecione uma conta bancária.",
            )
            return

        if ContaBancariaDialog(self, conta).exec():
            self.atualizar()


class AbaCartoes(QWidget):
    def __init__(self):
        super().__init__()

        self.service = FinanceiroService()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        novo = QPushButton("+ Nova Operadora")
        novo.clicked.connect(self._novo)

        editar = QPushButton("Editar")
        editar.setObjectName("btnSecundario")
        editar.clicked.connect(self._editar)

        topo.addWidget(novo)
        topo.addWidget(editar)
        topo.addStretch()

        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 6)
        self.tabela.setHorizontalHeaderLabels([
            "Operadora",
            "Taxa débito",
            "Taxa crédito",
            "Prazo débito",
            "Prazo crédito",
            "Status",
        ])
        _configurar_tabela(self.tabela)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        operadoras = (
            self.service.listar_operadoras_cartao()
        )

        self.tabela.setRowCount(0)

        for operadora in operadoras:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            item = QTableWidgetItem(
                operadora.get("nome", "")
            )
            item.setData(
                Qt.UserRole,
                str(operadora["_id"]),
            )

            valores = [
                item,
                QTableWidgetItem(
                    f"{operadora.get('taxa_debito', 0):.2f}%"
                ),
                QTableWidgetItem(
                    f"{operadora.get('taxa_credito', 0):.2f}%"
                ),
                QTableWidgetItem(
                    f"{operadora.get('prazo_debito', 0)} dias"
                ),
                QTableWidgetItem(
                    f"{operadora.get('prazo_credito', 0)} dias"
                ),
                QTableWidgetItem(
                    "Ativa"
                    if operadora.get("ativo", True)
                    else "Inativa"
                ),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela.setItem(row, coluna, valor)

    def operadora_selecionada(self):
        row = self.tabela.currentRow()
        if row < 0:
            return None

        operadora_id = self.tabela.item(
            row,
            0,
        ).data(Qt.UserRole)

        return self.service.db.operadores_cartao.find_one({
            "_id": ObjectId(operadora_id)
        })

    def _novo(self):
        if OperadoraCartaoDialog(self).exec():
            self.atualizar()

    def _editar(self):
        operadora = self.operadora_selecionada()
        if not operadora:
            alerta(
                self,
                "Atenção",
                "Selecione uma operadora.",
            )
            return

        if OperadoraCartaoDialog(
            self,
            operadora,
        ).exec():
            self.atualizar()


class FinanceiroWidget(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        titulo = QLabel("Financeiro / Contas")
        titulo.setObjectName("tituloPagina")
        layout.addWidget(titulo)

        self.tabs = QTabWidget()

        self.aba_pagar = AbaContasPagar()
        self.aba_receber = AbaContasReceber()
        self.aba_fluxo = AbaFluxoCaixa()
        self.aba_bancos = AbaContasBancarias()
        self.aba_cartoes = AbaCartoes()

        self.tabs.addTab(
            self.aba_pagar,
            "Contas a Pagar"
        )
        self.tabs.addTab(
            self.aba_receber,
            "Contas a Receber"
        )
        self.tabs.addTab(
            self.aba_fluxo,
            "Fluxo de Caixa"
        )
        self.tabs.addTab(
            self.aba_bancos,
            "Contas Bancárias"
        )
        self.tabs.addTab(
            self.aba_cartoes,
            "Cartões / Operadoras"
        )

        layout.addWidget(self.tabs)

    def atualizar(self):
        self.aba_pagar.atualizar()
        self.aba_receber.atualizar()
        self.aba_fluxo.atualizar()
        self.aba_bancos.atualizar()
        self.aba_cartoes.atualizar()