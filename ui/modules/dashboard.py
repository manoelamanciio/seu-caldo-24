# -*- coding: utf-8 -*-
import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                                QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt

from db.database import get_db
from utils.helpers import fmt_moeda, fmt_data


def _card(titulo, valor, cor="#E8590C"):
    frame = QFrame()
    frame.setProperty("class", "card")
    frame.setStyleSheet("QFrame{background-color:#282A36; border-radius:10px;} ")
    lay = QVBoxLayout(frame)
    lbl_t = QLabel(titulo)
    lbl_t.setObjectName("kpiTitulo")
    lbl_v = QLabel(valor)
    lbl_v.setObjectName("kpiValor")
    lbl_v.setStyleSheet(f"color:{cor}; font-size:24px; font-weight:bold;")
    lay.addWidget(lbl_t)
    lay.addWidget(lbl_v)
    return frame


class DashboardWidget(QWidget):
    def __init__(self, usuario):
        super().__init__()
        self.usuario = usuario
        self.db = get_db()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self._montar()

    def _montar(self):
        titulo = QLabel("Visão Geral do Bar")
        titulo.setObjectName("tituloPagina")
        self.layout.addWidget(titulo)

        self.linha_kpis = QHBoxLayout()
        self.layout.addLayout(self.linha_kpis)

        sub = QLabel("Produtos com estoque baixo")
        sub.setStyleSheet("font-weight:bold; font-size:15px; margin-top:16px;")
        self.layout.addWidget(sub)

        self.tabela_estoque_baixo = QTableWidget(0, 4)
        self.tabela_estoque_baixo.setHorizontalHeaderLabels(["Produto", "Setor", "Estoque atual", "Estoque mínimo"])
        self.tabela_estoque_baixo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela_estoque_baixo.setEditTriggers(QTableWidget.NoEditTriggers)
        self.layout.addWidget(self.tabela_estoque_baixo)

        sub2 = QLabel("Contas a vencer nos próximos 7 dias")
        sub2.setStyleSheet("font-weight:bold; font-size:15px; margin-top:16px;")
        self.layout.addWidget(sub2)

        self.tabela_contas = QTableWidget(0, 3)
        self.tabela_contas.setHorizontalHeaderLabels(["Descrição", "Vencimento", "Valor"])
        self.tabela_contas.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela_contas.setEditTriggers(QTableWidget.NoEditTriggers)
        self.layout.addWidget(self.tabela_contas)

        self.atualizar()

    def atualizar(self):
        # limpa KPIs antigos
        while self.linha_kpis.count():
            item = self.linha_kpis.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        hoje = datetime.datetime.now()
        inicio_dia = datetime.datetime(hoje.year, hoje.month, hoje.day)

        total_vendas_hoje = self.db.vendas.aggregate([
            {"$match": {"data": {"$gte": inicio_dia}}},
            {"$group": {"_id": None, "total": {"$sum": "$total"}}}
        ])
        total_vendas_hoje = list(total_vendas_hoje)
        valor_vendas_hoje = total_vendas_hoje[0]["total"] if total_vendas_hoje else 0

        qtd_produtos = self.db.produtos.count_documents({})
        qtd_clientes = self.db.clientes.count_documents({})
        qtd_comandas_abertas = self.db.comandas.count_documents({"status": "Aberta"})

        a_receber = list(self.db.contas_receber.aggregate([
            {"$match": {"status": "Pendente"}},
            {"$group": {"_id": None, "total": {"$sum": "$valor"}}}
        ]))
        valor_receber = a_receber[0]["total"] if a_receber else 0

        a_pagar = list(self.db.contas_pagar.aggregate([
            {"$match": {"status": "Pendente"}},
            {"$group": {"_id": None, "total": {"$sum": "$valor"}}}
        ]))
        valor_pagar = a_pagar[0]["total"] if a_pagar else 0

        self.linha_kpis.addWidget(_card("Vendas hoje", fmt_moeda(valor_vendas_hoje), "#2ECC71"))
        self.linha_kpis.addWidget(_card("Comandas abertas", str(qtd_comandas_abertas), "#F1C40F"))
        self.linha_kpis.addWidget(_card("A Receber (correntistas)", fmt_moeda(valor_receber), "#3498DB"))
        self.linha_kpis.addWidget(_card("A Pagar", fmt_moeda(valor_pagar), "#E74C3C"))
        self.linha_kpis.addWidget(_card("Produtos cadastrados", str(qtd_produtos)))
        self.linha_kpis.addWidget(_card("Clientes cadastrados", str(qtd_clientes)))

        # Estoque baixo
        produtos_baixo = list(self.db.produtos.find(
            {"$expr": {"$lte": ["$estoque_atual", "$estoque_minimo"]}}
        ))
        self.tabela_estoque_baixo.setRowCount(0)
        for p in produtos_baixo:
            row = self.tabela_estoque_baixo.rowCount()
            self.tabela_estoque_baixo.insertRow(row)
            self.tabela_estoque_baixo.setItem(row, 0, QTableWidgetItem(p.get("nome", "")))
            self.tabela_estoque_baixo.setItem(row, 1, QTableWidgetItem(p.get("setor", "")))
            self.tabela_estoque_baixo.setItem(row, 2, QTableWidgetItem(str(p.get("estoque_atual", 0))))
            self.tabela_estoque_baixo.setItem(row, 3, QTableWidgetItem(str(p.get("estoque_minimo", 0))))

        # Contas a vencer
        limite = hoje + datetime.timedelta(days=7)
        contas = list(self.db.contas_pagar.find(
            {"status": "Pendente", "vencimento": {"$lte": limite}}
        ).sort("vencimento", 1))
        self.tabela_contas.setRowCount(0)
        for c in contas:
            row = self.tabela_contas.rowCount()
            self.tabela_contas.insertRow(row)
            self.tabela_contas.setItem(row, 0, QTableWidgetItem(c.get("descricao", "")))
            self.tabela_contas.setItem(row, 1, QTableWidgetItem(fmt_data(c.get("vencimento"))))
            self.tabela_contas.setItem(row, 2, QTableWidgetItem(fmt_moeda(c.get("valor", 0))))