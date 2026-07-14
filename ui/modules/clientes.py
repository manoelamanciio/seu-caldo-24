# -*- coding: utf-8 -*-
"""
Módulo Clientes / Fidelidade.
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
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from services.clientes_service import ClientesService
from utils.helpers import alerta, confirmar, fmt_data, fmt_moeda, info


def _configurar_tabela(tabela):
    tabela.horizontalHeader().setSectionResizeMode(
        QHeaderView.Stretch
    )
    tabela.setEditTriggers(QTableWidget.NoEditTriggers)
    tabela.setSelectionBehavior(QTableWidget.SelectRows)
    tabela.setSelectionMode(QTableWidget.SingleSelection)


class ClienteDialog(QDialog):
    def __init__(self, parent=None, cliente=None):
        super().__init__(parent)

        self.service = ClientesService()
        self.cliente = cliente

        self.setWindowTitle(
            "Editar Cliente" if cliente else "Novo Cliente"
        )
        self.setMinimumWidth(520)

        layout = QFormLayout(self)

        self.tipo_pessoa = QComboBox()
        self.tipo_pessoa.addItem("Pessoa Física", "PF")
        self.tipo_pessoa.addItem("Pessoa Jurídica", "PJ")

        self.nome_razao = QLineEdit()
        self.nome_fantasia = QLineEdit()
        self.cpf_cnpj = QLineEdit()
        self.telefone = QLineEdit()
        self.email = QLineEdit()
        self.endereco = QLineEdit()
        self.cidade = QLineEdit()

        self.correntista = QCheckBox(
            "Habilitar compras como correntista"
        )

        self.limite_credito = QDoubleSpinBox()
        self.limite_credito.setPrefix("R$ ")
        self.limite_credito.setDecimals(2)
        self.limite_credito.setMaximum(9999999)

        self.dia_fechamento = QSpinBox()
        self.dia_fechamento.setRange(1, 31)
        self.dia_fechamento.setValue(30)

        self.ativo = QCheckBox("Cadastro ativo")
        self.ativo.setChecked(True)

        self.observacoes = QTextEdit()
        self.observacoes.setFixedHeight(80)

        layout.addRow("Tipo de pessoa:", self.tipo_pessoa)
        layout.addRow("Nome / Razão social:", self.nome_razao)
        layout.addRow("Nome fantasia:", self.nome_fantasia)
        layout.addRow("CPF / CNPJ:", self.cpf_cnpj)
        layout.addRow("Telefone:", self.telefone)
        layout.addRow("E-mail:", self.email)
        layout.addRow("Endereço:", self.endereco)
        layout.addRow("Cidade:", self.cidade)
        layout.addRow("Correntista:", self.correntista)
        layout.addRow("Limite de crédito:", self.limite_credito)
        layout.addRow("Dia de fechamento:", self.dia_fechamento)
        layout.addRow("Status:", self.ativo)
        layout.addRow("Observações:", self.observacoes)

        botoes = QHBoxLayout()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.clicked.connect(self.reject)

        btn_salvar = QPushButton("Salvar")
        btn_salvar.clicked.connect(self._salvar)

        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_salvar)

        layout.addRow(botoes)

        if cliente:
            self._preencher(cliente)

    def _preencher(self, cliente):
        idx = self.tipo_pessoa.findData(
            cliente.get("tipo_pessoa", "PF")
        )
        self.tipo_pessoa.setCurrentIndex(max(idx, 0))

        self.nome_razao.setText(
            cliente.get("nome_razao", "")
        )
        self.nome_fantasia.setText(
            cliente.get("nome_fantasia", "")
        )
        self.cpf_cnpj.setText(cliente.get("cpf_cnpj", ""))
        self.telefone.setText(cliente.get("telefone", ""))
        self.email.setText(cliente.get("email", ""))
        self.endereco.setText(cliente.get("endereco", ""))
        self.cidade.setText(cliente.get("cidade", ""))

        self.correntista.setChecked(
            cliente.get("correntista", False)
        )
        self.limite_credito.setValue(
            float(cliente.get("limite_credito", 0))
        )
        self.dia_fechamento.setValue(
            int(cliente.get("dia_fechamento", 30))
        )
        self.ativo.setChecked(cliente.get("ativo", True))
        self.observacoes.setPlainText(
            cliente.get("observacoes", "")
        )

    def _salvar(self):
        dados = {
            "tipo_pessoa": self.tipo_pessoa.currentData(),
            "nome_razao": self.nome_razao.text(),
            "nome_fantasia": self.nome_fantasia.text(),
            "cpf_cnpj": self.cpf_cnpj.text(),
            "telefone": self.telefone.text(),
            "email": self.email.text(),
            "endereco": self.endereco.text(),
            "cidade": self.cidade.text(),
            "correntista": self.correntista.isChecked(),
            "limite_credito": self.limite_credito.value(),
            "dia_fechamento": self.dia_fechamento.value(),
            "ativo": self.ativo.isChecked(),
            "observacoes": self.observacoes.toPlainText(),
        }

        try:
            cliente_id = (
                str(self.cliente["_id"])
                if self.cliente
                else None
            )
            self.service.salvar_cliente(
                dados,
                cliente_id=cliente_id,
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class ConsumoDialog(QDialog):
    def __init__(self, parent=None, cliente=None):
        super().__init__(parent)

        self.service = ClientesService()
        self.cliente = cliente

        self.setWindowTitle("Lançar consumo correntista")
        self.setMinimumWidth(420)

        layout = QFormLayout(self)

        cliente_nome = QLabel(
            cliente.get("nome_razao", "")
        )
        cliente_nome.setStyleSheet("font-weight: bold;")

        credito = self.service.credito_disponivel(
            str(cliente["_id"])
        )
        lbl_credito = QLabel(fmt_moeda(credito))

        self.valor = QDoubleSpinBox()
        self.valor.setPrefix("R$ ")
        self.valor.setDecimals(2)
        self.valor.setMaximum(999999)

        self.descricao = QLineEdit()
        self.descricao.setPlaceholderText(
            "Ex.: Consumo do dia, encomenda, comanda..."
        )

        layout.addRow("Cliente:", cliente_nome)
        layout.addRow("Crédito disponível:", lbl_credito)
        layout.addRow("Valor:", self.valor)
        layout.addRow("Descrição:", self.descricao)

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
            self.service.lancar_consumo(
                str(self.cliente["_id"]),
                self.valor.value(),
                self.descricao.text(),
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class PontosDialog(QDialog):
    def __init__(self, parent=None, cliente=None):
        super().__init__(parent)

        self.service = ClientesService()
        self.cliente = cliente

        self.setWindowTitle("Adicionar pontos")
        self.setMinimumWidth(380)

        layout = QFormLayout(self)

        self.pontos = QSpinBox()
        self.pontos.setRange(1, 999999)

        self.motivo = QLineEdit()
        self.motivo.setPlaceholderText(
            "Ex.: Campanha, ajuste, compra promocional"
        )

        layout.addRow(
            "Cliente:",
            QLabel(cliente.get("nome_razao", "")),
        )
        layout.addRow("Pontos:", self.pontos)
        layout.addRow("Motivo:", self.motivo)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(self.reject)

        salvar = QPushButton("Adicionar")
        salvar.clicked.connect(self._salvar)

        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)

        layout.addRow(botoes)

    def _salvar(self):
        try:
            self.service.adicionar_pontos(
                str(self.cliente["_id"]),
                self.pontos.value(),
                self.motivo.text(),
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class PremioDialog(QDialog):
    def __init__(self, parent=None, premio=None):
        super().__init__(parent)

        self.service = ClientesService()
        self.premio = premio

        self.setWindowTitle(
            "Editar Prêmio" if premio else "Novo Prêmio"
        )
        self.setMinimumWidth(420)

        layout = QFormLayout(self)

        self.nome = QLineEdit()
        self.descricao = QLineEdit()

        self.pontos = QSpinBox()
        self.pontos.setRange(1, 999999)

        self.ativo = QCheckBox("Prêmio ativo")
        self.ativo.setChecked(True)

        layout.addRow("Nome:", self.nome)
        layout.addRow("Descrição:", self.descricao)
        layout.addRow("Pontos necessários:", self.pontos)
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

        if premio:
            self.nome.setText(premio.get("nome", ""))
            self.descricao.setText(
                premio.get("descricao", "")
            )
            self.pontos.setValue(
                int(premio.get("pontos_necessarios", 1))
            )
            self.ativo.setChecked(
                premio.get("ativo", True)
            )

    def _salvar(self):
        try:
            premio_id = (
                str(self.premio["_id"])
                if self.premio
                else None
            )

            self.service.salvar_premio(
                {
                    "nome": self.nome.text(),
                    "descricao": self.descricao.text(),
                    "pontos_necessarios": self.pontos.value(),
                    "ativo": self.ativo.isChecked(),
                },
                premio_id=premio_id,
            )

            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class AbaClientes(QWidget):
    def __init__(self):
        super().__init__()

        self.service = ClientesService()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        self.busca = QLineEdit()
        self.busca.setPlaceholderText(
            "Buscar por nome, CPF/CNPJ, telefone ou e-mail..."
        )
        self.busca.textChanged.connect(self.atualizar)

        novo = QPushButton("+ Novo Cliente")
        novo.clicked.connect(self._novo)

        editar = QPushButton("Editar")
        editar.setObjectName("btnSecundario")
        editar.clicked.connect(self._editar)

        ativar = QPushButton("Ativar / Desativar")
        ativar.setObjectName("btnSecundario")
        ativar.clicked.connect(self._alternar_ativo)

        excluir = QPushButton("Excluir")
        excluir.setObjectName("btnPerigo")
        excluir.clicked.connect(self._excluir)

        topo.addWidget(self.busca, 1)
        topo.addWidget(novo)
        topo.addWidget(editar)
        topo.addWidget(ativar)
        topo.addWidget(excluir)

        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 9)
        self.tabela.setHorizontalHeaderLabels([
            "Nome / Razão",
            "Tipo",
            "CPF / CNPJ",
            "Telefone",
            "Correntista",
            "Limite",
            "Saldo",
            "Pontos",
            "Status",
        ])
        _configurar_tabela(self.tabela)
        self.tabela.doubleClicked.connect(self._editar)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        clientes = self.service.listar_clientes(
            self.busca.text()
        )

        self.tabela.setRowCount(0)

        for cliente in clientes:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            item_nome = QTableWidgetItem(
                cliente.get("nome_razao", "")
            )
            item_nome.setData(
                Qt.UserRole,
                str(cliente["_id"]),
            )

            status = "Ativo"
            if not cliente.get("ativo", True):
                status = "Inativo"
            elif cliente.get("bloqueado", False):
                status = "Bloqueado"

            valores = [
                item_nome,
                QTableWidgetItem(
                    cliente.get("tipo_pessoa", "PF")
                ),
                QTableWidgetItem(
                    cliente.get("cpf_cnpj", "")
                ),
                QTableWidgetItem(
                    cliente.get("telefone", "")
                ),
                QTableWidgetItem(
                    "Sim"
                    if cliente.get("correntista", False)
                    else "Não"
                ),
                QTableWidgetItem(
                    fmt_moeda(
                        cliente.get("limite_credito", 0)
                    )
                ),
                QTableWidgetItem(
                    fmt_moeda(
                        cliente.get("saldo_correntista", 0)
                    )
                ),
                QTableWidgetItem(
                    str(cliente.get("pontos", 0))
                ),
                QTableWidgetItem(status),
            ]

            for coluna, item in enumerate(valores):
                self.tabela.setItem(row, coluna, item)

    def cliente_selecionado(self):
        row = self.tabela.currentRow()

        if row < 0:
            return None

        cliente_id = self.tabela.item(
            row,
            0,
        ).data(Qt.UserRole)

        return self.service.buscar_cliente(cliente_id)

    def _novo(self):
        if ClienteDialog(self).exec():
            self.atualizar()

    def _editar(self):
        cliente = self.cliente_selecionado()

        if not cliente:
            alerta(
                self,
                "Atenção",
                "Selecione um cliente.",
            )
            return

        if ClienteDialog(self, cliente).exec():
            self.atualizar()

    def _alternar_ativo(self):
        cliente = self.cliente_selecionado()

        if not cliente:
            alerta(
                self,
                "Atenção",
                "Selecione um cliente.",
            )
            return

        self.service.alternar_ativo(
            str(cliente["_id"])
        )
        self.atualizar()

    def _excluir(self):
        cliente = self.cliente_selecionado()

        if not cliente:
            alerta(
                self,
                "Atenção",
                "Selecione um cliente.",
            )
            return

        if not confirmar(
            self,
            "Confirmar",
            f"Excluir o cliente '{cliente.get('nome_razao', '')}'?",
        ):
            return

        try:
            self.service.excluir_cliente(
                str(cliente["_id"])
            )
            self.atualizar()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class AbaCorrentistas(QWidget):
    def __init__(self):
        super().__init__()

        self.service = ClientesService()

        layout = QVBoxLayout(self)

        botoes = QHBoxLayout()

        consumo = QPushButton("Lançar consumo")
        consumo.clicked.connect(self._lancar_consumo)

        fatura = QPushButton("Gerar fatura")
        fatura.clicked.connect(self._gerar_fatura)

        pagamento = QPushButton("Registrar pagamento")
        pagamento.setObjectName("btnSecundario")
        pagamento.clicked.connect(self._registrar_pagamento)

        bloqueio = QPushButton("Bloquear / Desbloquear")
        bloqueio.setObjectName("btnSecundario")
        bloqueio.clicked.connect(self._bloquear_desbloquear)

        verificar = QPushButton("Verificar atrasos")
        verificar.setObjectName("btnSecundario")
        verificar.clicked.connect(self._verificar_atrasos)

        botoes.addWidget(consumo)
        botoes.addWidget(fatura)
        botoes.addWidget(pagamento)
        botoes.addWidget(bloqueio)
        botoes.addWidget(verificar)
        botoes.addStretch()

        layout.addLayout(botoes)

        layout.addWidget(QLabel("Clientes correntistas"))

        self.tabela_clientes = QTableWidget(0, 7)
        self.tabela_clientes.setHorizontalHeaderLabels([
            "Cliente",
            "Limite",
            "Saldo",
            "Disponível",
            "Fechamento",
            "Bloqueio",
            "Status",
        ])
        _configurar_tabela(self.tabela_clientes)

        layout.addWidget(self.tabela_clientes)

        layout.addWidget(QLabel("Faturas"))

        self.tabela_faturas = QTableWidget(0, 6)
        self.tabela_faturas.setHorizontalHeaderLabels([
            "Número",
            "Cliente",
            "Emissão",
            "Vencimento",
            "Valor",
            "Status",
        ])
        _configurar_tabela(self.tabela_faturas)

        layout.addWidget(self.tabela_faturas)

        self.atualizar()

    def atualizar(self):
        clientes = [
            c for c in self.service.listar_clientes()
            if c.get("correntista", False)
        ]

        self.tabela_clientes.setRowCount(0)

        for cliente in clientes:
            row = self.tabela_clientes.rowCount()
            self.tabela_clientes.insertRow(row)

            item_cliente = QTableWidgetItem(
                cliente.get("nome_razao", "")
            )
            item_cliente.setData(
                Qt.UserRole,
                str(cliente["_id"]),
            )

            limite = cliente.get("limite_credito", 0)
            saldo = cliente.get("saldo_correntista", 0)
            disponivel = max(float(limite) - float(saldo), 0)

            valores = [
                item_cliente,
                QTableWidgetItem(fmt_moeda(limite)),
                QTableWidgetItem(fmt_moeda(saldo)),
                QTableWidgetItem(fmt_moeda(disponivel)),
                QTableWidgetItem(
                    str(cliente.get("dia_fechamento", 30))
                ),
                QTableWidgetItem(
                    cliente.get("motivo_bloqueio", "")
                ),
                QTableWidgetItem(
                    "Bloqueado"
                    if cliente.get("bloqueado", False)
                    else "Liberado"
                ),
            ]

            for coluna, item in enumerate(valores):
                self.tabela_clientes.setItem(
                    row,
                    coluna,
                    item,
                )

        faturas = self.service.listar_faturas()

        self.tabela_faturas.setRowCount(0)

        for fatura in faturas:
            row = self.tabela_faturas.rowCount()
            self.tabela_faturas.insertRow(row)

            item_numero = QTableWidgetItem(
                str(fatura.get("numero", ""))
            )
            item_numero.setData(
                Qt.UserRole,
                str(fatura["_id"]),
            )

            valores = [
                item_numero,
                QTableWidgetItem(
                    fatura.get("cliente_nome", "")
                ),
                QTableWidgetItem(
                    fmt_data(fatura.get("emissao"))
                ),
                QTableWidgetItem(
                    fmt_data(fatura.get("vencimento"))
                ),
                QTableWidgetItem(
                    fmt_moeda(fatura.get("valor", 0))
                ),
                QTableWidgetItem(
                    fatura.get("status", "")
                ),
            ]

            for coluna, item in enumerate(valores):
                self.tabela_faturas.setItem(
                    row,
                    coluna,
                    item,
                )

    def cliente_selecionado(self):
        row = self.tabela_clientes.currentRow()

        if row < 0:
            return None

        cliente_id = self.tabela_clientes.item(
            row,
            0,
        ).data(Qt.UserRole)

        return self.service.buscar_cliente(cliente_id)

    def _lancar_consumo(self):
        cliente = self.cliente_selecionado()

        if not cliente:
            alerta(
                self,
                "Atenção",
                "Selecione um correntista.",
            )
            return

        if ConsumoDialog(self, cliente).exec():
            self.atualizar()

    def _gerar_fatura(self):
        cliente = self.cliente_selecionado()

        if not cliente:
            alerta(
                self,
                "Atenção",
                "Selecione um correntista.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Gerar fatura")

        form = QFormLayout(dialog)

        vencimento = QDateEdit()
        vencimento.setCalendarPopup(True)
        vencimento.setDate(
            QDate.currentDate().addDays(10)
        )

        form.addRow(
            "Cliente:",
            QLabel(cliente.get("nome_razao", "")),
        )
        form.addRow("Vencimento:", vencimento)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(dialog.reject)

        gerar = QPushButton("Gerar")

        def executar():
            data = vencimento.date().toPython()
            data_hora = datetime.datetime.combine(
                data,
                datetime.time(23, 59, 59),
            )

            try:
                numero = self.service.gerar_fatura(
                    str(cliente["_id"]),
                    data_hora,
                )
                info(
                    dialog,
                    "Fatura gerada",
                    f"Fatura nº {numero} gerada com sucesso.",
                )
                dialog.accept()
            except ValueError as exc:
                alerta(dialog, "Atenção", str(exc))

        gerar.clicked.connect(executar)

        botoes.addWidget(cancelar)
        botoes.addWidget(gerar)

        form.addRow(botoes)

        if dialog.exec():
            self.atualizar()

    def _registrar_pagamento(self):
        row = self.tabela_faturas.currentRow()

        if row < 0:
            alerta(
                self,
                "Atenção",
                "Selecione uma fatura.",
            )
            return

        fatura_id = self.tabela_faturas.item(
            row,
            0,
        ).data(Qt.UserRole)

        if not confirmar(
            self,
            "Confirmar pagamento",
            "Registrar esta fatura como paga?",
        ):
            return

        try:
            self.service.registrar_pagamento_fatura(
                fatura_id
            )
            self.atualizar()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))

    def _bloquear_desbloquear(self):
        cliente = self.cliente_selecionado()

        if not cliente:
            alerta(
                self,
                "Atenção",
                "Selecione um correntista.",
            )
            return

        if cliente.get("bloqueado", False):
            self.service.desbloquear_cliente(
                str(cliente["_id"])
            )
        else:
            self.service.bloquear_cliente(
                str(cliente["_id"]),
                "Bloqueio administrativo",
            )

        self.atualizar()

    def _verificar_atrasos(self):
        quantidade = (
            self.service.verificar_bloqueios_por_atraso()
        )

        info(
            self,
            "Verificação concluída",
            f"{quantidade} cliente(s) bloqueado(s) por atraso.",
        )
        self.atualizar()


class AbaFidelidade(QWidget):
    def __init__(self):
        super().__init__()

        self.service = ClientesService()

        layout = QVBoxLayout(self)

        botoes = QHBoxLayout()

        pontos = QPushButton("Adicionar pontos")
        pontos.clicked.connect(self._adicionar_pontos)

        novo_premio = QPushButton("+ Novo Prêmio")
        novo_premio.clicked.connect(self._novo_premio)

        editar_premio = QPushButton("Editar Prêmio")
        editar_premio.setObjectName("btnSecundario")
        editar_premio.clicked.connect(self._editar_premio)

        resgatar = QPushButton("Resgatar prêmio")
        resgatar.clicked.connect(self._resgatar_premio)

        botoes.addWidget(pontos)
        botoes.addWidget(novo_premio)
        botoes.addWidget(editar_premio)
        botoes.addWidget(resgatar)
        botoes.addStretch()

        layout.addLayout(botoes)

        layout.addWidget(QLabel("Clientes e pontos"))

        self.tabela_clientes = QTableWidget(0, 4)
        self.tabela_clientes.setHorizontalHeaderLabels([
            "Cliente",
            "CPF / CNPJ",
            "Pontos",
            "Status",
        ])
        _configurar_tabela(self.tabela_clientes)

        layout.addWidget(self.tabela_clientes)

        layout.addWidget(QLabel("Prêmios disponíveis"))

        self.tabela_premios = QTableWidget(0, 4)
        self.tabela_premios.setHorizontalHeaderLabels([
            "Prêmio",
            "Descrição",
            "Pontos necessários",
            "Status",
        ])
        _configurar_tabela(self.tabela_premios)

        layout.addWidget(self.tabela_premios)

        self.atualizar()

    def atualizar(self):
        clientes = self.service.listar_clientes()

        self.tabela_clientes.setRowCount(0)

        for cliente in clientes:
            row = self.tabela_clientes.rowCount()
            self.tabela_clientes.insertRow(row)

            item_cliente = QTableWidgetItem(
                cliente.get("nome_razao", "")
            )
            item_cliente.setData(
                Qt.UserRole,
                str(cliente["_id"]),
            )

            valores = [
                item_cliente,
                QTableWidgetItem(
                    cliente.get("cpf_cnpj", "")
                ),
                QTableWidgetItem(
                    str(cliente.get("pontos", 0))
                ),
                QTableWidgetItem(
                    "Ativo"
                    if cliente.get("ativo", True)
                    else "Inativo"
                ),
            ]

            for coluna, item in enumerate(valores):
                self.tabela_clientes.setItem(
                    row,
                    coluna,
                    item,
                )

        premios = self.service.listar_premios()

        self.tabela_premios.setRowCount(0)

        for premio in premios:
            row = self.tabela_premios.rowCount()
            self.tabela_premios.insertRow(row)

            item_premio = QTableWidgetItem(
                premio.get("nome", "")
            )
            item_premio.setData(
                Qt.UserRole,
                str(premio["_id"]),
            )

            valores = [
                item_premio,
                QTableWidgetItem(
                    premio.get("descricao", "")
                ),
                QTableWidgetItem(
                    str(premio.get("pontos_necessarios", 0))
                ),
                QTableWidgetItem(
                    "Ativo"
                    if premio.get("ativo", True)
                    else "Inativo"
                ),
            ]

            for coluna, item in enumerate(valores):
                self.tabela_premios.setItem(
                    row,
                    coluna,
                    item,
                )

    def cliente_selecionado(self):
        row = self.tabela_clientes.currentRow()

        if row < 0:
            return None

        cliente_id = self.tabela_clientes.item(
            row,
            0,
        ).data(Qt.UserRole)

        return self.service.buscar_cliente(cliente_id)

    def premio_selecionado(self):
        row = self.tabela_premios.currentRow()

        if row < 0:
            return None

        premio_id = self.tabela_premios.item(
            row,
            0,
        ).data(Qt.UserRole)

        return self.service.db.premios_fidelidade.find_one({
            "_id": ObjectId(premio_id)
        })

    def _adicionar_pontos(self):
        cliente = self.cliente_selecionado()

        if not cliente:
            alerta(
                self,
                "Atenção",
                "Selecione um cliente.",
            )
            return

        if PontosDialog(self, cliente).exec():
            self.atualizar()

    def _novo_premio(self):
        if PremioDialog(self).exec():
            self.atualizar()

    def _editar_premio(self):
        premio = self.premio_selecionado()

        if not premio:
            alerta(
                self,
                "Atenção",
                "Selecione um prêmio.",
            )
            return

        if PremioDialog(self, premio).exec():
            self.atualizar()

    def _resgatar_premio(self):
        cliente = self.cliente_selecionado()
        premio = self.premio_selecionado()

        if not cliente or not premio:
            alerta(
                self,
                "Atenção",
                "Selecione um cliente e um prêmio.",
            )
            return

        if not confirmar(
            self,
            "Confirmar resgate",
            (
                f"Resgatar '{premio.get('nome', '')}' para "
                f"{cliente.get('nome_razao', '')}?"
            ),
        ):
            return

        try:
            self.service.resgatar_premio(
                str(cliente["_id"]),
                str(premio["_id"]),
            )
            info(
                self,
                "Resgate realizado",
                "Prêmio resgatado com sucesso.",
            )
            self.atualizar()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class AbaHistorico(QWidget):
    def __init__(self):
        super().__init__()

        self.service = ClientesService()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        self.cliente_combo = QComboBox()
        self.cliente_combo.currentIndexChanged.connect(
            self.atualizar
        )

        atualizar = QPushButton("Atualizar")
        atualizar.setObjectName("btnSecundario")
        atualizar.clicked.connect(self.atualizar)

        topo.addWidget(QLabel("Cliente:"))
        topo.addWidget(self.cliente_combo, 1)
        topo.addWidget(atualizar)

        layout.addLayout(topo)

        self.tabs = QTabWidget()

        self.tabela_consumos = QTableWidget(0, 4)
        self.tabela_consumos.setHorizontalHeaderLabels([
            "Data",
            "Descrição",
            "Valor",
            "Status",
        ])
        _configurar_tabela(self.tabela_consumos)

        self.tabela_faturas = QTableWidget(0, 5)
        self.tabela_faturas.setHorizontalHeaderLabels([
            "Número",
            "Emissão",
            "Vencimento",
            "Valor",
            "Status",
        ])
        _configurar_tabela(self.tabela_faturas)

        self.tabela_resgates = QTableWidget(0, 3)
        self.tabela_resgates.setHorizontalHeaderLabels([
            "Data",
            "Prêmio",
            "Pontos utilizados",
        ])
        _configurar_tabela(self.tabela_resgates)

        self.tabs.addTab(self.tabela_consumos, "Consumos")
        self.tabs.addTab(self.tabela_faturas, "Faturas")
        self.tabs.addTab(self.tabela_resgates, "Resgates")

        layout.addWidget(self.tabs)

        self._carregar_clientes()
        self.atualizar()

    def _carregar_clientes(self):
        atual = self.cliente_combo.currentData()

        self.cliente_combo.blockSignals(True)
        self.cliente_combo.clear()

        for cliente in self.service.listar_clientes():
            self.cliente_combo.addItem(
                cliente.get("nome_razao", ""),
                str(cliente["_id"]),
            )

        if atual:
            indice = self.cliente_combo.findData(atual)
            if indice >= 0:
                self.cliente_combo.setCurrentIndex(indice)

        self.cliente_combo.blockSignals(False)

    def atualizar(self):
        cliente_id = self.cliente_combo.currentData()

        if not cliente_id:
            self.tabela_consumos.setRowCount(0)
            self.tabela_faturas.setRowCount(0)
            self.tabela_resgates.setRowCount(0)
            return

        historico = self.service.historico_cliente(
            cliente_id
        )

        self.tabela_consumos.setRowCount(0)

        for consumo in historico["consumos"]:
            row = self.tabela_consumos.rowCount()
            self.tabela_consumos.insertRow(row)

            valores = [
                fmt_data(consumo.get("data")),
                consumo.get("descricao", ""),
                fmt_moeda(consumo.get("valor", 0)),
                consumo.get("status", ""),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela_consumos.setItem(
                    row,
                    coluna,
                    QTableWidgetItem(str(valor)),
                )

        self.tabela_faturas.setRowCount(0)

        for fatura in historico["faturas"]:
            row = self.tabela_faturas.rowCount()
            self.tabela_faturas.insertRow(row)

            valores = [
                fatura.get("numero", ""),
                fmt_data(fatura.get("emissao")),
                fmt_data(fatura.get("vencimento")),
                fmt_moeda(fatura.get("valor", 0)),
                fatura.get("status", ""),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela_faturas.setItem(
                    row,
                    coluna,
                    QTableWidgetItem(str(valor)),
                )

        self.tabela_resgates.setRowCount(0)

        for resgate in historico["resgates"]:
            row = self.tabela_resgates.rowCount()
            self.tabela_resgates.insertRow(row)

            valores = [
                fmt_data(resgate.get("data")),
                resgate.get("premio_nome", ""),
                resgate.get("pontos_utilizados", 0),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela_resgates.setItem(
                    row,
                    coluna,
                    QTableWidgetItem(str(valor)),
                )


class ClientesWidget(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        titulo = QLabel("Clientes / Fidelidade")
        titulo.setObjectName("tituloPagina")

        layout.addWidget(titulo)

        self.tabs = QTabWidget()

        self.aba_clientes = AbaClientes()
        self.aba_correntistas = AbaCorrentistas()
        self.aba_fidelidade = AbaFidelidade()
        self.aba_historico = AbaHistorico()

        self.tabs.addTab(
            self.aba_clientes,
            "Clientes"
        )
        self.tabs.addTab(
            self.aba_correntistas,
            "Correntistas / Faturas"
        )
        self.tabs.addTab(
            self.aba_fidelidade,
            "Clube de Fidelidade"
        )
        self.tabs.addTab(
            self.aba_historico,
            "Histórico"
        )

        layout.addWidget(self.tabs)

    def atualizar(self):
        self.aba_clientes.atualizar()
        self.aba_correntistas.atualizar()
        self.aba_fidelidade.atualizar()
        self.aba_historico._carregar_clientes()
        self.aba_historico.atualizar()
