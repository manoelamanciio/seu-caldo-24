# -*- coding: utf-8 -*-
"""
Serviço de relatórios do sistema Seu Caldo 24.
Desenvolvido por M.A Sistemas.
"""

import datetime
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from db.database import get_db


def _money(value):
    return float(
        Decimal(str(value or 0)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )


class RelatoriosService:
    def __init__(self):
        self.db = get_db()

    def _filtro_periodo(self, campo, inicio=None, fim=None):
        filtro = {}

        if inicio or fim:
            filtro[campo] = {}

            if inicio:
                filtro[campo]["$gte"] = inicio

            if fim:
                filtro[campo]["$lte"] = fim

        return filtro

    # ==========================================================
    # RESUMO DE VENDAS
    # ==========================================================

    def resumo_vendas(self, inicio=None, fim=None):
        filtro = self._filtro_periodo("data", inicio, fim)
        vendas = list(self.db.vendas.find(filtro))

        faturamento = _money(
            sum(float(venda.get("total", 0)) for venda in vendas)
        )
        quantidade = len(vendas)
        ticket_medio = _money(
            faturamento / quantidade if quantidade else 0
        )

        formas_pagamento = defaultdict(float)

        for venda in vendas:
            forma = venda.get("forma_pagamento", "Não informado")
            formas_pagamento[forma] += float(venda.get("total", 0))

        return {
            "faturamento": faturamento,
            "quantidade_vendas": quantidade,
            "ticket_medio": ticket_medio,
            "formas_pagamento": {
                chave: _money(valor)
                for chave, valor in formas_pagamento.items()
            },
        }

    # ==========================================================
    # PRODUTOS MAIS VENDIDOS / RENTABILIDADE
    # ==========================================================

    def produtos_mais_vendidos(self, inicio=None, fim=None):
        filtro = self._filtro_periodo("data", inicio, fim)

        pipeline = []

        if filtro:
            pipeline.append({"$match": filtro})

        pipeline.extend([
            {"$unwind": "$itens"},
            {
                "$group": {
                    "_id": "$itens.produto_id",
                    "produto_nome": {
                        "$first": "$itens.produto_nome"
                    },
                    "quantidade": {
                        "$sum": "$itens.quantidade"
                    },
                    "faturamento": {
                        "$sum": "$itens.total"
                    },
                }
            },
            {"$sort": {"quantidade": -1}},
        ])

        resultado = list(self.db.vendas.aggregate(pipeline))

        dados = []

        for item in resultado:
            produto = None

            if item.get("_id"):
                try:
                    from bson import ObjectId
                    produto = self.db.produtos.find_one({
                        "_id": ObjectId(str(item["_id"]))
                    })
                except Exception:
                    produto = None

            custo = float(
                produto.get("custo", 0)
                if produto
                else 0
            )
            quantidade = float(item.get("quantidade", 0))
            faturamento = _money(item.get("faturamento", 0))
            custo_total = _money(custo * quantidade)
            lucro = _money(faturamento - custo_total)
            margem = (
                (lucro / faturamento) * 100
                if faturamento > 0
                else 0
            )

            dados.append({
                "produto_nome": item.get(
                    "produto_nome",
                    "Produto sem nome",
                ),
                "quantidade": quantidade,
                "faturamento": faturamento,
                "custo_total": custo_total,
                "lucro": lucro,
                "margem": round(margem, 2),
            })

        return dados

    def curva_abc(self, inicio=None, fim=None):
        produtos = self.produtos_mais_vendidos(inicio, fim)
        produtos = sorted(
            produtos,
            key=lambda item: item["faturamento"],
            reverse=True,
        )

        total = sum(item["faturamento"] for item in produtos)
        acumulado = 0
        resultado = []

        for produto in produtos:
            percentual = (
                produto["faturamento"] / total * 100
                if total > 0
                else 0
            )
            acumulado += percentual

            if acumulado <= 80:
                classe = "A"
            elif acumulado <= 95:
                classe = "B"
            else:
                classe = "C"

            resultado.append({
                **produto,
                "percentual": round(percentual, 2),
                "percentual_acumulado": round(acumulado, 2),
                "classe": classe,
            })

        return resultado

    # ==========================================================
    # ESTOQUE
    # ==========================================================

    def estoque_baixo(self):
        return list(
            self.db.produtos.find({
                "$expr": {
                    "$lte": [
                        "$estoque_atual",
                        "$estoque_minimo",
                    ]
                }
            }).sort("nome", 1)
        )

    def movimentacoes_estoque(self, inicio=None, fim=None):
        filtro = self._filtro_periodo("data", inicio, fim)

        return list(
            self.db.movimentacoes_estoque
            .find(filtro)
            .sort("data", -1)
        )

    # ==========================================================
    # FINANCEIRO
    # ==========================================================

    def resumo_financeiro(self, inicio=None, fim=None):
        filtro = self._filtro_periodo("data", inicio, fim)
        movimentos = list(self.db.caixa_movimentos.find(filtro))

        entradas = _money(sum(
            float(item.get("valor", 0))
            for item in movimentos
            if item.get("tipo") == "Entrada"
        ))

        saidas = _money(sum(
            float(item.get("valor", 0))
            for item in movimentos
            if item.get("tipo") == "Saída"
        ))

        return {
            "entradas": entradas,
            "saidas": saidas,
            "saldo": _money(entradas - saidas),
        }

    def contas_pagar(self):
        return list(
            self.db.contas_pagar
            .find()
            .sort("vencimento", 1)
        )

    def contas_receber(self):
        return list(
            self.db.contas_receber
            .find()
            .sort("vencimento", 1)
        )

    # ==========================================================
    # PRODUÇÃO
    # ==========================================================

    def producao(self, inicio=None, fim=None):
        filtro = self._filtro_periodo(
            "data_programada",
            inicio,
            fim,
        )

        return list(
            self.db.ordens_producao
            .find(filtro)
            .sort("data_programada", -1)
        )

    # ==========================================================
    # CLIENTES
    # ==========================================================

    def ranking_clientes(self, inicio=None, fim=None):
        filtro = self._filtro_periodo("data", inicio, fim)

        pipeline = []

        if filtro:
            pipeline.append({"$match": filtro})

        pipeline.extend([
            {
                "$match": {
                    "cliente_id": {"$ne": None}
                }
            },
            {
                "$group": {
                    "_id": "$cliente_id",
                    "cliente_nome": {
                        "$first": "$cliente_nome"
                    },
                    "quantidade_vendas": {
                        "$sum": 1
                    },
                    "total": {
                        "$sum": "$total"
                    },
                }
            },
            {"$sort": {"total": -1}},
        ])

        return list(self.db.vendas.aggregate(pipeline))