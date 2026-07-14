# -*- coding: utf-8 -*-
"""
Regras de negócio do módulo PDV / Atendimento.
Sistema Seu Caldo 24 - M.A Sistemas
"""

import datetime
from decimal import Decimal, ROUND_HALF_UP

from bson import ObjectId

from db.database import get_db
from services.clientes_service import ClientesService
from services.financeiro_service import FinanceiroService


def _money(value):
    return float(
        Decimal(str(value or 0)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )


class PdvService:
    def __init__(self):
        self.db = get_db()
        self.clientes_service = ClientesService()
        self.financeiro_service = FinanceiroService()

    # ==========================================================
    # MESAS / COMANDAS
    # ==========================================================

    def listar_comandas(self, status=None):
        filtro = {}
        if status:
            filtro["status"] = status

        return list(
            self.db.comandas
            .find(filtro)
            .sort("aberta_em", -1)
        )

    def buscar_comanda(self, comanda_id):
        if not comanda_id:
            return None

        return self.db.comandas.find_one({
            "_id": ObjectId(str(comanda_id))
        })

    def abrir_comanda(
        self,
        tipo_atendimento,
        referencia="",
        cliente_id=None,
        usuario=None,
    ):
        tipo_atendimento = (tipo_atendimento or "").strip()

        if tipo_atendimento not in ("Salão", "Balcão", "Delivery"):
            raise ValueError("Tipo de atendimento inválido.")

        cliente_nome = ""
        if cliente_id:
            cliente = self.db.clientes.find_one({
                "_id": ObjectId(str(cliente_id))
            })
            if not cliente:
                raise ValueError("Cliente não encontrado.")
            cliente_nome = cliente.get("nome_razao", "")

        numero = self.db.proximo_numero("comanda")

        registro = {
            "numero": numero,
            "tipo_atendimento": tipo_atendimento,
            "referencia": referencia.strip(),
            "cliente_id": str(cliente_id) if cliente_id else None,
            "cliente_nome": cliente_nome,
            "itens": [],
            "subtotal": 0.0,
            "desconto": 0.0,
            "acrescimo": 0.0,
            "total": 0.0,
            "status": "Aberta",
            "usuario_id": str(usuario.get("_id")) if usuario else None,
            "usuario_nome": usuario.get("nome") if usuario else None,
            "aberta_em": datetime.datetime.now(),
            "fechada_em": None,
        }

        resultado = self.db.comandas.insert_one(registro)
        return str(resultado.inserted_id), numero

    def adicionar_item(self, comanda_id, produto_id, quantidade=1):
        comanda = self.buscar_comanda(comanda_id)

        if not comanda:
            raise ValueError("Comanda não encontrada.")

        if comanda.get("status") != "Aberta":
            raise ValueError("A comanda não está aberta.")

        quantidade = float(quantidade)

        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")

        produto = self.db.produtos.find_one({
            "_id": ObjectId(str(produto_id))
        })

        if not produto:
            raise ValueError("Produto não encontrado.")

        estoque = float(produto.get("estoque_atual", 0))
        if quantidade > estoque:
            raise ValueError("Estoque insuficiente para este produto.")

        preco = _money(produto.get("preco_venda", 0))
        item_existente = None

        for item in comanda.get("itens", []):
            if item.get("produto_id") == str(produto["_id"]):
                item_existente = item
                break

        itens = list(comanda.get("itens", []))

        if item_existente:
            nova_qtd = float(item_existente.get("quantidade", 0)) + quantidade

            if nova_qtd > estoque:
                raise ValueError("Estoque insuficiente para esta quantidade.")

            for item in itens:
                if item.get("produto_id") == str(produto["_id"]):
                    item["quantidade"] = nova_qtd
                    item["total"] = _money(nova_qtd * preco)
        else:
            itens.append({
                "produto_id": str(produto["_id"]),
                "produto_nome": produto.get("nome", ""),
                "quantidade": quantidade,
                "preco_unit": preco,
                "total": _money(quantidade * preco),
            })

        self._atualizar_totais_comanda(comanda["_id"], itens)

    def remover_item(self, comanda_id, indice):
        comanda = self.buscar_comanda(comanda_id)

        if not comanda:
            raise ValueError("Comanda não encontrada.")

        itens = list(comanda.get("itens", []))

        if indice < 0 or indice >= len(itens):
            raise ValueError("Item inválido.")

        itens.pop(indice)
        self._atualizar_totais_comanda(comanda["_id"], itens)

    def aplicar_ajustes(self, comanda_id, desconto=0, acrescimo=0):
        comanda = self.buscar_comanda(comanda_id)

        if not comanda:
            raise ValueError("Comanda não encontrada.")

        desconto = _money(desconto)
        acrescimo = _money(acrescimo)

        if desconto < 0 or acrescimo < 0:
            raise ValueError("Desconto e acréscimo não podem ser negativos.")

        subtotal = _money(
            sum(item.get("total", 0) for item in comanda.get("itens", []))
        )
        total = _money(max(subtotal - desconto + acrescimo, 0))

        self.db.comandas.update_one(
            {"_id": comanda["_id"]},
            {"$set": {
                "subtotal": subtotal,
                "desconto": desconto,
                "acrescimo": acrescimo,
                "total": total,
            }},
        )

    def _atualizar_totais_comanda(self, comanda_object_id, itens):
        comanda = self.db.comandas.find_one({"_id": comanda_object_id})

        subtotal = _money(sum(item.get("total", 0) for item in itens))
        desconto = _money(comanda.get("desconto", 0))
        acrescimo = _money(comanda.get("acrescimo", 0))
        total = _money(max(subtotal - desconto + acrescimo, 0))

        self.db.comandas.update_one(
            {"_id": comanda_object_id},
            {"$set": {
                "itens": itens,
                "subtotal": subtotal,
                "total": total,
            }},
        )

    def cancelar_comanda(self, comanda_id, motivo=""):
        comanda = self.buscar_comanda(comanda_id)

        if not comanda:
            raise ValueError("Comanda não encontrada.")

        if comanda.get("status") != "Aberta":
            raise ValueError("Somente comandas abertas podem ser canceladas.")

        self.db.comandas.update_one(
            {"_id": comanda["_id"]},
            {"$set": {
                "status": "Cancelada",
                "motivo_cancelamento": motivo.strip(),
                "cancelada_em": datetime.datetime.now(),
            }},
        )

    # ==========================================================
    # FECHAMENTO / VENDA
    # ==========================================================

    def fechar_comanda(
        self,
        comanda_id,
        forma_pagamento,
        conta_bancaria_id=None,
    ):
        comanda = self.buscar_comanda(comanda_id)

        if not comanda:
            raise ValueError("Comanda não encontrada.")

        if comanda.get("status") != "Aberta":
            raise ValueError("A comanda não está aberta.")

        itens = comanda.get("itens", [])

        if not itens:
            raise ValueError("A comanda não possui itens.")

        forma_pagamento = (forma_pagamento or "").strip()

        permitidas = [
            "Dinheiro",
            "PIX",
            "Cartão Débito",
            "Cartão Crédito",
            "Correntista",
        ]

        if forma_pagamento not in permitidas:
            raise ValueError("Forma de pagamento inválida.")

        total = _money(comanda.get("total", 0))

        if forma_pagamento == "Correntista":
            cliente_id = comanda.get("cliente_id")

            if not cliente_id:
                raise ValueError(
                    "Selecione um cliente para pagamento correntista."
                )

            self.clientes_service.lancar_consumo(
                cliente_id,
                total,
                descricao=f"Comanda nº {comanda.get('numero')}",
                origem="PDV",
            )

        agora = datetime.datetime.now()

        # Valida todo o estoque antes de baixar.
        for item in itens:
            produto = self.db.produtos.find_one({
                "_id": ObjectId(item["produto_id"])
            })

            if not produto:
                raise ValueError(
                    f"Produto '{item.get('produto_nome', '')}' não encontrado."
                )

            if float(produto.get("estoque_atual", 0)) < float(item["quantidade"]):
                raise ValueError(
                    f"Estoque insuficiente para '{item.get('produto_nome', '')}'."
                )

        # Baixa o estoque.
        for item in itens:
            produto_id = ObjectId(item["produto_id"])
            produto = self.db.produtos.find_one({"_id": produto_id})
            anterior = float(produto.get("estoque_atual", 0))
            posterior = anterior - float(item["quantidade"])

            self.db.produtos.update_one(
                {"_id": produto_id},
                {"$set": {
                    "estoque_atual": posterior,
                    "atualizado_em": agora,
                }},
            )

            self.db.movimentacoes_estoque.insert_one({
                "produto_id": str(produto_id),
                "produto_nome": item.get("produto_nome", ""),
                "tipo": "Saída por venda",
                "setor": produto.get("setor", ""),
                "quantidade": float(item["quantidade"]),
                "estoque_anterior": anterior,
                "estoque_posterior": posterior,
                "motivo": f"Comanda nº {comanda.get('numero')}",
                "data": agora,
            })

        numero_venda = self.db.proximo_numero("venda")

        venda = {
            "numero": numero_venda,
            "comanda_id": str(comanda["_id"]),
            "comanda_numero": comanda.get("numero"),
            "tipo_atendimento": comanda.get("tipo_atendimento"),
            "referencia": comanda.get("referencia", ""),
            "cliente_id": comanda.get("cliente_id"),
            "cliente_nome": comanda.get("cliente_nome", ""),
            "itens": itens,
            "subtotal": _money(comanda.get("subtotal", 0)),
            "desconto": _money(comanda.get("desconto", 0)),
            "acrescimo": _money(comanda.get("acrescimo", 0)),
            "total": total,
            "forma_pagamento": forma_pagamento,
            "usuario_id": comanda.get("usuario_id"),
            "usuario_nome": comanda.get("usuario_nome"),
            "data": agora,
        }

        self.db.vendas.insert_one(venda)

        if forma_pagamento != "Correntista":
            self.financeiro_service.registrar_movimento_caixa(
                tipo="Entrada",
                descricao=f"Venda PDV nº {numero_venda}",
                valor=total,
                categoria="Vendas",
                centro_custo="Loja",
                conta_bancaria_id=conta_bancaria_id,
                origem="PDV",
                documento_id=str(comanda["_id"]),
                data=agora,
            )

        self.db.comandas.update_one(
            {"_id": comanda["_id"]},
            {"$set": {
                "status": "Fechada",
                "forma_pagamento": forma_pagamento,
                "fechada_em": agora,
                "venda_numero": numero_venda,
            }},
        )

        return numero_venda

    def listar_vendas(self):
        return list(
            self.db.vendas
            .find()
            .sort("data", -1)
            .limit(500)
        )