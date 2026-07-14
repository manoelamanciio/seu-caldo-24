# -*- coding: utf-8 -*-
"""
Módulo Produção / Cozinha.
Sistema Seu Caldo 24 - M.A Sistemas
"""

import datetime

from bson import ObjectId
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
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

from db.database import get_db
from services.producao_service import ProducaoService
from utils.helpers import alerta, confirmar, fmt_data, fmt_moeda, info


def _configurar_tabela(tabela):
    tabela.horizontalHeader().setSectionResizeMode(
        QHeaderView.Stretch
    )
    tabela.setEditTriggers(QTableWidget.NoEditTriggers)
    tabela.setSelectionBehavior(QTableWidget.SelectRows)
    tabela.setSelectionMode(QTableWidget.SingleSelection)


class FichaTecnicaDialog(QDialog):
    def __init__(self, parent=None, ficha=None):
        super().__init__(parent)

        self.db = get_db()
        self.service = ProducaoService()
        self.ficha = ficha
        self.ingredientes = []

        self.setWindowTitle(
            "Editar Ficha Técnica"
            if ficha
            else "Nova Ficha Técnica"
        )
        self.resize(760, 620)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.nome = QLineEdit()

        self.produto_final = QComboBox()
        for produto in self.db.produtos.find().sort("nome", 1):
            self.produto_final.addItem(
                produto.get("nome", ""),
                str(produto["_id"]),
            )

        self.rendimento = QDoubleSpinBox()
        self.rendimento.setRange(0.001, 999999)
        self.rendimento.setDecimals(3)
        self.rendimento.setValue(1)

        self.unidade_rendimento = QComboBox()
        self.unidade_rendimento.addItems([
            "UN",
            "KG",
            "L",
            "PCT",
            "CX",
        ])

        self.custo_mao_obra = QDoubleSpinBox()
        self.custo_mao_obra.setPrefix("R$ ")
        self.custo_mao_obra.setMaximum(999999)
        self.custo_mao_obra.setDecimals(2)
        self.custo_mao_obra.valueChanged.connect(
            self._recalcular
        )

        self.custo_operacional = QDoubleSpinBox()
        self.custo_operacional.setPrefix("R$ ")
        self.custo_operacional.setMaximum(999999)
        self.custo_operacional.setDecimals(2)
        self.custo_operacional.valueChanged.connect(
            self._recalcular
        )

        self.observacoes = QTextEdit()
        self.observacoes.setFixedHeight(70)

        form.addRow("Nome da ficha:", self.nome)
        form.addRow("Produto produzido:", self.produto_final)
        form.addRow("Rendimento:", self.rendimento)
        form.addRow("Unidade do rendimento:", self.unidade_rendimento)
        form.addRow("Custo de mão de obra:", self.custo_mao_obra)
        form.addRow("Custo operacional:", self.custo_operacional)
        form.addRow("Observações:", self.observacoes)

        layout.addLayout(form)

        linha_ingrediente = QHBoxLayout()

        self.produto_ingrediente = QComboBox()
        for produto in self.db.produtos.find().sort("nome", 1):
            self.produto_ingrediente.addItem(
                produto.get("nome", ""),
                str(produto["_id"]),
            )

        self.quantidade_ingrediente = QDoubleSpinBox()
        self.quantidade_ingrediente.setRange(0.001, 999999)
        self.quantidade_ingrediente.setDecimals(3)
        self.quantidade_ingrediente.setValue(1)

        btn_adicionar = QPushButton("Adicionar ingrediente")
        btn_adicionar.clicked.connect(
            self._adicionar_ingrediente
        )

        btn_remover = QPushButton("Remover selecionado")
        btn_remover.setObjectName("btnPerigo")
        btn_remover.clicked.connect(
            self._remover_ingrediente
        )

        linha_ingrediente.addWidget(QLabel("Ingrediente:"))
        linha_ingrediente.addWidget(
            self.produto_ingrediente,
            2,
        )
        linha_ingrediente.addWidget(QLabel("Quantidade:"))
        linha_ingrediente.addWidget(
            self.quantidade_ingrediente
        )
        linha_ingrediente.addWidget(btn_adicionar)
        linha_ingrediente.addWidget(btn_remover)

        layout.addLayout(linha_ingrediente)

        self.tabela = QTableWidget(0, 5)
        self.tabela.setHorizontalHeaderLabels([
            "Ingrediente",
            "Unidade",
            "Quantidade",
            "Custo unitário",
            "Custo total",
        ])
        _configurar_tabela(self.tabela)

        layout.addWidget(self.tabela)

        self.lbl_custo = QLabel("Custo total: R$ 0,00")
        self.lbl_custo.setStyleSheet(
            "font-size:16px; font-weight:bold;"
        )
        layout.addWidget(self.lbl_custo)

        botoes = QHBoxLayout()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.clicked.connect(self.reject)

        btn_salvar = QPushButton("Salvar")
        btn_salvar.clicked.connect(self._salvar)

        botoes.addStretch()
        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_salvar)

        layout.addLayout(botoes)

        if ficha:
            self._preencher(ficha)

    def _preencher(self, ficha):
        self.nome.setText(ficha.get("nome", ""))

        idx = self.produto_final.findData(
            ficha.get("produto_id")
        )
        if idx >= 0:
            self.produto_final.setCurrentIndex(idx)

        self.rendimento.setValue(
            float(ficha.get("rendimento", 1))
        )
        self.unidade_rendimento.setCurrentText(
            ficha.get("unidade_rendimento", "UN")
        )
        self.custo_mao_obra.setValue(
            float(ficha.get("custo_mao_obra", 0))
        )
        self.custo_operacional.setValue(
            float(ficha.get("custo_operacional", 0))
        )
        self.observacoes.setPlainText(
            ficha.get("observacoes", "")
        )

        self.ingredientes = list(
            ficha.get("ingredientes", [])
        )
        self._atualizar_tabela()

    def _adicionar_ingrediente(self):
        produto_id = self.produto_ingrediente.currentData()

        if not produto_id:
            return

        produto = self.db.produtos.find_one({
            "_id": ObjectId(produto_id)
        })

        quantidade = self.quantidade_ingrediente.value()

        item = {
            "produto_id": str(produto["_id"]),
            "produto_nome": produto.get("nome", ""),
            "unidade": produto.get("unidade", "UN"),
            "quantidade": quantidade,
            "custo_unitario": float(
                produto.get("custo", 0)
            ),
        }

        self.ingredientes.append(item)
        self._atualizar_tabela()

    def _remover_ingrediente(self):
        row = self.tabela.currentRow()

        if row < 0:
            alerta(
                self,
                "Atenção",
                "Selecione um ingrediente.",
            )
            return

        self.ingredientes.pop(row)
        self._atualizar_tabela()

    def _atualizar_tabela(self):
        self.tabela.setRowCount(0)

        for item in self.ingredientes:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            total = (
                float(item.get("quantidade", 0))
                * float(item.get("custo_unitario", 0))
            )

            valores = [
                item.get("produto_nome", ""),
                item.get("unidade", ""),
                item.get("quantidade", 0),
                fmt_moeda(item.get("custo_unitario", 0)),
                fmt_moeda(total),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela.setItem(
                    row,
                    coluna,
                    QTableWidgetItem(str(valor)),
                )

        self._recalcular()

    def _recalcular(self):
        custos = self.service.calcular_custo_ficha(
            self.ingredientes,
            self.custo_mao_obra.value(),
            self.custo_operacional.value(),
        )

        self.lbl_custo.setText(
            f"Custo total: {fmt_moeda(custos['custo_total'])}"
        )

    def _salvar(self):
        dados = {
            "nome": self.nome.text(),
            "produto_id": self.produto_final.currentData(),
            "ingredientes": self.ingredientes,
            "rendimento": self.rendimento.value(),
            "unidade_rendimento": (
                self.unidade_rendimento.currentText()
            ),
            "custo_mao_obra": self.custo_mao_obra.value(),
            "custo_operacional": (
                self.custo_operacional.value()
            ),
            "observacoes": self.observacoes.toPlainText(),
        }

        try:
            ficha_id = (
                str(self.ficha["_id"])
                if self.ficha
                else None
            )

            self.service.salvar_ficha(
                dados,
                ficha_id=ficha_id,
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class OrdemDialog(QDialog):
    def __init__(self, parent=None, usuario=None):
        super().__init__(parent)

        self.service = ProducaoService()
        self.usuario = usuario

        self.setWindowTitle("Nova Ordem de Produção")
        self.setMinimumWidth(460)

        layout = QFormLayout(self)

        self.ficha = QComboBox()
        for ficha in self.service.listar_fichas():
            self.ficha.addItem(
                ficha.get("nome", ""),
                str(ficha["_id"]),
            )

        self.quantidade = QDoubleSpinBox()
        self.quantidade.setRange(0.001, 999999)
        self.quantidade.setDecimals(3)
        self.quantidade.setValue(1)

        self.data_programada = QDateEdit()
        self.data_programada.setCalendarPopup(True)
        self.data_programada.setDate(
            QDate.currentDate()
        )

        self.observacoes = QTextEdit()
        self.observacoes.setFixedHeight(70)

        layout.addRow("Ficha técnica:", self.ficha)
        layout.addRow("Quantidade planejada:", self.quantidade)
        layout.addRow("Data programada:", self.data_programada)
        layout.addRow("Observações:", self.observacoes)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(self.reject)

        salvar = QPushButton("Criar ordem")
        salvar.clicked.connect(self._salvar)

        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)

        layout.addRow(botoes)

    def _salvar(self):
        if not self.ficha.currentData():
            alerta(
                self,
                "Atenção",
                "Cadastre uma ficha técnica antes.",
            )
            return

        data = self.data_programada.date().toPython()
        data_hora = datetime.datetime.combine(
            data,
            datetime.time(8, 0),
        )

        try:
            _, numero = self.service.criar_ordem(
                self.ficha.currentData(),
                self.quantidade.value(),
                data_hora,
                usuario=self.usuario,
                observacoes=self.observacoes.toPlainText(),
            )

            info(
                self,
                "Ordem criada",
                f"Ordem nº {numero} criada com sucesso.",
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class FinalizarOrdemDialog(QDialog):
    def __init__(self, parent=None, ordem=None):
        super().__init__(parent)

        self.service = ProducaoService()
        self.ordem = ordem

        self.setWindowTitle("Finalizar Ordem de Produção")
        self.setMinimumWidth(420)

        layout = QFormLayout(self)

        self.quantidade_produzida = QDoubleSpinBox()
        self.quantidade_produzida.setRange(0.001, 999999)
        self.quantidade_produzida.setDecimals(3)
        self.quantidade_produzida.setValue(
            float(ordem.get("quantidade_planejada", 1))
        )

        self.perda = QDoubleSpinBox()
        self.perda.setRange(0, 999999)
        self.perda.setDecimals(3)

        self.observacoes = QTextEdit()
        self.observacoes.setFixedHeight(70)

        layout.addRow(
            "Produto:",
            QLabel(ordem.get("produto_nome", "")),
        )
        layout.addRow(
            "Quantidade produzida:",
            self.quantidade_produzida,
        )
        layout.addRow("Perda:", self.perda)
        layout.addRow("Observações:", self.observacoes)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(self.reject)

        finalizar = QPushButton("Finalizar")
        finalizar.clicked.connect(self._finalizar)

        botoes.addWidget(cancelar)
        botoes.addWidget(finalizar)

        layout.addRow(botoes)

    def _finalizar(self):
        try:
            self.service.finalizar_ordem(
                str(self.ordem["_id"]),
                self.quantidade_produzida.value(),
                self.perda.value(),
                self.observacoes.toPlainText(),
            )
            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class AbaFichasTecnicas(QWidget):
    def __init__(self):
        super().__init__()

        self.service = ProducaoService()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        self.busca = QLineEdit()
        self.busca.setPlaceholderText(
            "Buscar ficha técnica..."
        )
        self.busca.textChanged.connect(self.atualizar)

        novo = QPushButton("+ Nova Ficha")
        novo.clicked.connect(self._novo)

        editar = QPushButton("Editar")
        editar.setObjectName("btnSecundario")
        editar.clicked.connect(self._editar)

        excluir = QPushButton("Excluir")
        excluir.setObjectName("btnPerigo")
        excluir.clicked.connect(self._excluir)

        topo.addWidget(self.busca, 1)
        topo.addWidget(novo)
        topo.addWidget(editar)
        topo.addWidget(excluir)

        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 7)
        self.tabela.setHorizontalHeaderLabels([
            "Ficha",
            "Produto final",
            "Rendimento",
            "Unidade",
            "Custo ingredientes",
            "Custo total",
            "Custo unitário",
        ])
        _configurar_tabela(self.tabela)
        self.tabela.doubleClicked.connect(self._editar)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        fichas = self.service.listar_fichas(
            self.busca.text()
        )

        self.tabela.setRowCount(0)

        for ficha in fichas:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            item_ficha = QTableWidgetItem(
                ficha.get("nome", "")
            )
            item_ficha.setData(
                Qt.UserRole,
                str(ficha["_id"]),
            )

            valores = [
                item_ficha,
                QTableWidgetItem(
                    ficha.get("produto_nome", "")
                ),
                QTableWidgetItem(
                    str(ficha.get("rendimento", 0))
                ),
                QTableWidgetItem(
                    ficha.get("unidade_rendimento", "")
                ),
                QTableWidgetItem(
                    fmt_moeda(
                        ficha.get("custo_ingredientes", 0)
                    )
                ),
                QTableWidgetItem(
                    fmt_moeda(ficha.get("custo_total", 0))
                ),
                QTableWidgetItem(
                    fmt_moeda(
                        ficha.get("custo_unitario_producao", 0)
                    )
                ),
            ]

            for coluna, item in enumerate(valores):
                self.tabela.setItem(
                    row,
                    coluna,
                    item,
                )

    def ficha_selecionada(self):
        row = self.tabela.currentRow()

        if row < 0:
            return None

        ficha_id = self.tabela.item(
            row,
            0,
        ).data(Qt.UserRole)

        return self.service.buscar_ficha(ficha_id)

    def _novo(self):
        if FichaTecnicaDialog(self).exec():
            self.atualizar()

    def _editar(self):
        ficha = self.ficha_selecionada()

        if not ficha:
            alerta(
                self,
                "Atenção",
                "Selecione uma ficha técnica.",
            )
            return

        if FichaTecnicaDialog(self, ficha).exec():
            self.atualizar()

    def _excluir(self):
        ficha = self.ficha_selecionada()

        if not ficha:
            alerta(
                self,
                "Atenção",
                "Selecione uma ficha técnica.",
            )
            return

        if not confirmar(
            self,
            "Confirmar",
            f"Excluir a ficha '{ficha.get('nome', '')}'?",
        ):
            return

        try:
            self.service.excluir_ficha(
                str(ficha["_id"])
            )
            self.atualizar()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class AbaOrdensProducao(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario
        self.service = ProducaoService()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        nova = QPushButton("+ Nova Ordem")
        nova.clicked.connect(self._nova)

        iniciar = QPushButton("Iniciar")
        iniciar.clicked.connect(self._iniciar)

        finalizar = QPushButton("Finalizar")
        finalizar.clicked.connect(self._finalizar)

        cancelar = QPushButton("Cancelar ordem")
        cancelar.setObjectName("btnPerigo")
        cancelar.clicked.connect(self._cancelar)

        self.filtro_status = QComboBox()
        self.filtro_status.addItems([
            "Todos",
            "Planejada",
            "Em Produção",
            "Finalizada",
            "Cancelada",
        ])
        self.filtro_status.currentTextChanged.connect(
            self.atualizar
        )

        topo.addWidget(nova)
        topo.addWidget(iniciar)
        topo.addWidget(finalizar)
        topo.addWidget(cancelar)
        topo.addStretch()
        topo.addWidget(QLabel("Status:"))
        topo.addWidget(self.filtro_status)

        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels([
            "Número",
            "Ficha",
            "Produto",
            "Planejado",
            "Produzido",
            "Unidade",
            "Data programada",
            "Status",
        ])
        _configurar_tabela(self.tabela)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        status = self.filtro_status.currentText()
        if status == "Todos":
            status = None

        ordens = self.service.listar_ordens(status)

        self.tabela.setRowCount(0)

        for ordem in ordens:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            item_numero = QTableWidgetItem(
                str(ordem.get("numero", ""))
            )
            item_numero.setData(
                Qt.UserRole,
                str(ordem["_id"]),
            )

            valores = [
                item_numero,
                QTableWidgetItem(
                    ordem.get("ficha_nome", "")
                ),
                QTableWidgetItem(
                    ordem.get("produto_nome", "")
                ),
                QTableWidgetItem(
                    str(ordem.get("quantidade_planejada", 0))
                ),
                QTableWidgetItem(
                    str(ordem.get("quantidade_produzida", 0))
                ),
                QTableWidgetItem(
                    ordem.get("unidade", "")
                ),
                QTableWidgetItem(
                    fmt_data(ordem.get("data_programada"))
                ),
                QTableWidgetItem(
                    ordem.get("status", "")
                ),
            ]

            for coluna, item in enumerate(valores):
                self.tabela.setItem(
                    row,
                    coluna,
                    item,
                )

    def ordem_selecionada(self):
        row = self.tabela.currentRow()

        if row < 0:
            return None

        ordem_id = self.tabela.item(
            row,
            0,
        ).data(Qt.UserRole)

        return self.service.db.ordens_producao.find_one({
            "_id": ObjectId(ordem_id)
        })

    def _nova(self):
        if OrdemDialog(
            self,
            usuario=self.usuario,
        ).exec():
            self.atualizar()

    def _iniciar(self):
        ordem = self.ordem_selecionada()

        if not ordem:
            alerta(
                self,
                "Atenção",
                "Selecione uma ordem.",
            )
            return

        try:
            self.service.iniciar_ordem(
                str(ordem["_id"])
            )
            info(
                self,
                "Produção iniciada",
                "Ingredientes baixados do estoque.",
            )
            self.atualizar()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))

    def _finalizar(self):
        ordem = self.ordem_selecionada()

        if not ordem:
            alerta(
                self,
                "Atenção",
                "Selecione uma ordem.",
            )
            return

        if FinalizarOrdemDialog(
            self,
            ordem,
        ).exec():
            info(
                self,
                "Produção finalizada",
                "Produto final adicionado ao estoque.",
            )
            self.atualizar()

    def _cancelar(self):
        ordem = self.ordem_selecionada()

        if not ordem:
            alerta(
                self,
                "Atenção",
                "Selecione uma ordem.",
            )
            return

        if not confirmar(
            self,
            "Confirmar",
            "Cancelar esta ordem de produção?",
        ):
            return

        try:
            self.service.cancelar_ordem(
                str(ordem["_id"])
            )
            self.atualizar()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class AbaAgenda(QWidget):
    def __init__(self):
        super().__init__()

        self.service = ProducaoService()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        self.data = QDateEdit()
        self.data.setCalendarPopup(True)
        self.data.setDate(QDate.currentDate())
        self.data.dateChanged.connect(self.atualizar)

        topo.addWidget(QLabel("Data:"))
        topo.addWidget(self.data)
        topo.addStretch()

        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 6)
        self.tabela.setHorizontalHeaderLabels([
            "Número",
            "Produto",
            "Quantidade",
            "Unidade",
            "Status",
            "Observações",
        ])
        _configurar_tabela(self.tabela)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        data = self.data.date().toPython()
        inicio = datetime.datetime.combine(
            data,
            datetime.time.min,
        )
        fim = datetime.datetime.combine(
            data,
            datetime.time.max,
        )

        ordens = list(
            self.service.db.ordens_producao
            .find({
                "data_programada": {
                    "$gte": inicio,
                    "$lte": fim,
                }
            })
            .sort("numero", 1)
        )

        self.tabela.setRowCount(0)

        for ordem in ordens:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            valores = [
                ordem.get("numero", ""),
                ordem.get("produto_nome", ""),
                ordem.get("quantidade_planejada", 0),
                ordem.get("unidade", ""),
                ordem.get("status", ""),
                ordem.get("observacoes", ""),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela.setItem(
                    row,
                    coluna,
                    QTableWidgetItem(str(valor)),
                )


class ProducaoWidget(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        titulo = QLabel("Produção / Cozinha")
        titulo.setObjectName("tituloPagina")

        layout.addWidget(titulo)

        self.tabs = QTabWidget()

        self.aba_fichas = AbaFichasTecnicas()
        self.aba_ordens = AbaOrdensProducao(usuario)
        self.aba_agenda = AbaAgenda()

        self.tabs.addTab(
            self.aba_fichas,
            "Fichas Técnicas"
        )
        self.tabs.addTab(
            self.aba_ordens,
            "Ordens de Produção"
        )
        self.tabs.addTab(
            self.aba_agenda,
            "Agenda"
        )

        layout.addWidget(self.tabs)

    def atualizar(self):
        self.aba_fichas.atualizar()
        self.aba_ordens.atualizar()
        self.aba_agenda.atualizar