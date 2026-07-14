# -*- coding: utf-8 -*-
"""
Regras de negócio do módulo Financeiro.
Sistema Seu Caldo 24 - M.A Sistemas
"""

import datetime
from decimal import Decimal, ROUND_HALF_UP

from bson import ObjectId

from db.database import get_db


def _money(value):
    return float(
        Decimal(str(value or 0)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )


class FinanceiroService:
    def __init__(self):
        self.db = get_db()

    # ==========================================================
    # CONTAS A PAGAR
    # ==========================================================

    def listar_contas_pagar(self, status=None, termo=""):
        filtro = {}

        if status and status != "Todos":
            filtro["status"] = status

        termo = (termo or "").strip()
        if termo:
            filtro["$or"] = [
                {"descricao": {"$regex": termo, "$options": "i"}},
                {"fornecedor_nome": {"$regex": termo, "$options": "i"}},
                {"categoria": {"$regex": termo, "$options": "i"}},
                {"centro_custo": {"$regex": termo, "$options": "i"}},
            ]

        return list(
            self.db.contas_pagar
            .find(filtro)
            .sort("vencimento", 1)
        )

    def salvar_conta_pagar(self, dados, conta_id=None):
        descricao = (dados.get("descricao") or "").strip()
        valor = _money(dados.get("valor", 0))
        vencimento = dados.get("vencimento")

        if not descricao:
            raise ValueError("Informe a descrição da conta.")

        if valor <= 0:
            raise ValueError("O valor deve ser maior que zero.")

        if not vencimento:
            raise ValueError("Informe o vencimento.")

        agora = datetime.datetime.now()

        registro = {
            "descricao": descricao,
            "fornecedor_id": dados.get("fornecedor_id"),
            "fornecedor_nome": (
                dados.get("fornecedor_nome") or ""
            ).strip(),
            "categoria": (
                dados.get("categoria") or ""
            ).strip(),
            "centro_custo": (
                dados.get("centro_custo") or ""
            ).strip(),
            "valor": valor,
            "valor_pago": _money(dados.get("valor_pago", 0)),
            "vencimento": vencimento,
            "status": dados.get("status", "Pendente"),
            "forma_pagamento": (
                dados.get("forma_pagamento") or ""
            ).strip(),
            "observacoes": (
                dados.get("observacoes") or ""
            ).strip(),
            "atualizado_em": agora,
        }

        if conta_id:
            self.db.contas_pagar.update_one(
                {"_id": ObjectId(str(conta_id))},
                {"$set": registro},
            )
            return str(conta_id)

        registro["criado_em"] = agora
        resultado = self.db.contas_pagar.insert_one(registro)
        return str(resultado.inserted_id)

    def pagar_conta(self, conta_id, valor_pago=None, conta_bancaria_id=None):
        conta = self.db.contas_pagar.find_one({
            "_id": ObjectId(str(conta_id))
        })

        if not conta:
            raise ValueError("Conta a pagar não encontrada.")

        if conta.get("status") == "Paga":
            raise ValueError("Esta conta já está paga.")

        valor_total = _money(conta.get("valor", 0))
        valor_pago_anterior = _money(conta.get("valor_pago", 0))
        valor_pagamento = _money(
            valor_pago if valor_pago is not None
            else valor_total - valor_pago_anterior
        )

        if valor_pagamento <= 0:
            raise ValueError("Informe um valor de pagamento válido.")

        novo_total_pago = _money(
            valor_pago_anterior + valor_pagamento
        )

        if novo_total_pago > valor_total:
            raise ValueError(
                "O pagamento não pode ultrapassar o valor da conta."
            )

        status = (
            "Paga"
            if novo_total_pago >= valor_total
            else "Parcial"
        )

        agora = datetime.datetime.now()

        self.db.contas_pagar.update_one(
            {"_id": conta["_id"]},
            {"$set": {
                "valor_pago": novo_total_pago,
                "status": status,
                "pago_em": agora if status == "Paga" else None,
                "atualizado_em": agora,
            }},
        )

        self.registrar_movimento_caixa(
            tipo="Saída",
            descricao=f"Pagamento: {conta.get('descricao', '')}",
            valor=valor_pagamento,
            categoria=conta.get("categoria", "Contas a pagar"),
            centro_custo=conta.get("centro_custo", ""),
            conta_bancaria_id=conta_bancaria_id,
            origem="Conta a pagar",
            documento_id=str(conta["_id"]),
        )

    def excluir_conta_pagar(self, conta_id):
        conta = self.db.contas_pagar.find_one({
            "_id": ObjectId(str(conta_id))
        })

        if not conta:
            raise ValueError("Conta a pagar não encontrada.")

        if conta.get("valor_pago", 0) > 0:
            raise ValueError(
                "Não é possível excluir uma conta com pagamento registrado."
            )

        self.db.contas_pagar.delete_one({"_id": conta["_id"]})

    # ==========================================================
    # CONTAS A RECEBER
    # ==========================================================

    def listar_contas_receber(self, status=None, termo=""):
        filtro = {}

        if status and status != "Todos":
            filtro["status"] = status

        termo = (termo or "").strip()
        if termo:
            filtro["$or"] = [
                {"descricao": {"$regex": termo, "$options": "i"}},
                {"cliente_nome": {"$regex": termo, "$options": "i"}},
                {"categoria": {"$regex": termo, "$options": "i"}},
            ]

        return list(
            self.db.contas_receber
            .find(filtro)
            .sort("vencimento", 1)
        )

    def salvar_conta_receber(self, dados, conta_id=None):
        descricao = (dados.get("descricao") or "").strip()
        valor = _money(dados.get("valor", 0))
        vencimento = dados.get("vencimento")

        if not descricao:
            raise ValueError("Informe a descrição da conta.")

        if valor <= 0:
            raise ValueError("O valor deve ser maior que zero.")

        if not vencimento:
            raise ValueError("Informe o vencimento.")

        agora = datetime.datetime.now()

        registro = {
            "descricao": descricao,
            "cliente_id": dados.get("cliente_id"),
            "cliente_nome": (
                dados.get("cliente_nome") or ""
            ).strip(),
            "categoria": (
                dados.get("categoria") or ""
            ).strip(),
            "valor": valor,
            "valor_recebido": _money(
                dados.get("valor_recebido", 0)
            ),
            "vencimento": vencimento,
            "status": dados.get("status", "Pendente"),
            "forma_recebimento": (
                dados.get("forma_recebimento") or ""
            ).strip(),
            "observacoes": (
                dados.get("observacoes") or ""
            ).strip(),
            "atualizado_em": agora,
        }

        if conta_id:
            self.db.contas_receber.update_one(
                {"_id": ObjectId(str(conta_id))},
                {"$set": registro},
            )
            return str(conta_id)

        registro["criado_em"] = agora
        resultado = self.db.contas_receber.insert_one(registro)
        return str(resultado.inserted_id)

    def receber_conta(self, conta_id, valor_recebido=None, conta_bancaria_id=None):
        conta = self.db.contas_receber.find_one({
            "_id": ObjectId(str(conta_id))
        })

        if not conta:
            raise ValueError("Conta a receber não encontrada.")

        if conta.get("status") == "Recebida":
            raise ValueError("Esta conta já foi recebida.")

        valor_total = _money(conta.get("valor", 0))
        recebido_anterior = _money(conta.get("valor_recebido", 0))
        recebimento = _money(
            valor_recebido if valor_recebido is not None
            else valor_total - recebido_anterior
        )

        if recebimento <= 0:
            raise ValueError("Informe um valor de recebimento válido.")

        novo_total = _money(recebido_anterior + recebimento)

        if novo_total > valor_total:
            raise ValueError(
                "O recebimento não pode ultrapassar o valor da conta."
            )

        status = (
            "Recebida"
            if novo_total >= valor_total
            else "Parcial"
        )

        agora = datetime.datetime.now()

        self.db.contas_receber.update_one(
            {"_id": conta["_id"]},
            {"$set": {
                "valor_recebido": novo_total,
                "status": status,
                "recebido_em": agora if status == "Recebida" else None,
                "atualizado_em": agora,
            }},
        )

        self.registrar_movimento_caixa(
            tipo="Entrada",
            descricao=f"Recebimento: {conta.get('descricao', '')}",
            valor=recebimento,
            categoria=conta.get("categoria", "Contas a receber"),
            conta_bancaria_id=conta_bancaria_id,
            origem="Conta a receber",
            documento_id=str(conta["_id"]),
        )

    def excluir_conta_receber(self, conta_id):
        conta = self.db.contas_receber.find_one({
            "_id": ObjectId(str(conta_id))
        })

        if not conta:
            raise ValueError("Conta a receber não encontrada.")

        if conta.get("valor_recebido", 0) > 0:
            raise ValueError(
                "Não é possível excluir uma conta com recebimento registrado."
            )

        self.db.contas_receber.delete_one({"_id": conta["_id"]})

    # ==========================================================
    # CAIXA / FLUXO
    # ==========================================================

    def registrar_movimento_caixa(
        self,
        tipo,
        descricao,
        valor,
        categoria="",
        centro_custo="",
        conta_bancaria_id=None,
        origem="Manual",
        documento_id=None,
        data=None,
    ):
        tipo = (tipo or "").strip()
        descricao = (descricao or "").strip()
        valor = _money(valor)

        if tipo not in ("Entrada", "Saída"):
            raise ValueError("Tipo de movimento inválido.")

        if not descricao:
            raise ValueError("Informe a descrição do movimento.")

        if valor <= 0:
            raise ValueError("O valor deve ser maior que zero.")

        agora = data or datetime.datetime.now()

        conta_nome = ""
        if conta_bancaria_id:
            conta = self.db.contas_bancarias.find_one({
                "_id": ObjectId(str(conta_bancaria_id))
            })

            if not conta:
                raise ValueError("Conta bancária não encontrada.")

            conta_nome = conta.get("nome", "")

            incremento = valor if tipo == "Entrada" else -valor
            self.db.contas_bancarias.update_one(
                {"_id": conta["_id"]},
                {
                    "$inc": {"saldo_atual": incremento},
                    "$set": {"atualizado_em": agora},
                },
            )

        resultado = self.db.caixa_movimentos.insert_one({
            "tipo": tipo,
            "descricao": descricao,
            "valor": valor,
            "categoria": categoria.strip(),
            "centro_custo": centro_custo.strip(),
            "conta_bancaria_id": (
                str(conta_bancaria_id)
                if conta_bancaria_id
                else None
            ),
            "conta_bancaria_nome": conta_nome,
            "origem": origem,
            "documento_id": documento_id,
            "data": agora,
        })

        return str(resultado.inserted_id)

    def listar_movimentos(self, inicio=None, fim=None):
        filtro = {}

        if inicio or fim:
            filtro["data"] = {}
            if inicio:
                filtro["data"]["$gte"] = inicio
            if fim:
                filtro["data"]["$lte"] = fim

        return list(
            self.db.caixa_movimentos
            .find(filtro)
            .sort("data", -1)
        )

    def resumo_fluxo(self, inicio=None, fim=None):
        movimentos = self.listar_movimentos(inicio, fim)

        entradas = _money(sum(
            item.get("valor", 0)
            for item in movimentos
            if item.get("tipo") == "Entrada"
        ))

        saidas = _money(sum(
            item.get("valor", 0)
            for item in movimentos
            if item.get("tipo") == "Saída"
        ))

        return {
            "entradas": entradas,
            "saidas": saidas,
            "saldo": _money(entradas - saidas),
        }

    # ==========================================================
    # CONTAS BANCÁRIAS
    # ==========================================================

    def listar_contas_bancarias(self):
        return list(
            self.db.contas_bancarias
            .find()
            .sort("nome", 1)
        )

    def salvar_conta_bancaria(self, dados, conta_id=None):
        nome = (dados.get("nome") or "").strip()

        if not nome:
            raise ValueError("Informe o nome da conta.")

        agora = datetime.datetime.now()

        registro = {
            "nome": nome,
            "banco": (dados.get("banco") or "").strip(),
            "agencia": (dados.get("agencia") or "").strip(),
            "numero_conta": (
                dados.get("numero_conta") or ""
            ).strip(),
            "tipo": (dados.get("tipo") or "Conta Corrente").strip(),
            "saldo_atual": _money(dados.get("saldo_atual", 0)),
            "ativo": bool(dados.get("ativo", True)),
            "atualizado_em": agora,
        }

        if conta_id:
            self.db.contas_bancarias.update_one(
                {"_id": ObjectId(str(conta_id))},
                {"$set": registro},
            )
            return str(conta_id)

        registro["criado_em"] = agora
        resultado = self.db.contas_bancarias.insert_one(registro)
        return str(resultado.inserted_id)

    # ==========================================================
    # CARTÕES
    # ==========================================================

    def listar_operadoras_cartao(self):
        return list(
            self.db.operadores_cartao
            .find()
            .sort("nome", 1)
        )

    def salvar_operadora_cartao(self, dados, operadora_id=None):
        nome = (dados.get("nome") or "").strip()

        if not nome:
            raise ValueError("Informe o nome da operadora.")

        registro = {
            "nome": nome,
            "taxa_debito": _money(dados.get("taxa_debito", 0)),
            "taxa_credito": _money(dados.get("taxa_credito", 0)),
            "prazo_debito": int(dados.get("prazo_debito", 1)),
            "prazo_credito": int(dados.get("prazo_credito", 30)),
            "ativo": bool(dados.get("ativo", True)),
            "atualizado_em": datetime.datetime.now(),
        }

        if operadora_id:
            self.db.operadores_cartao.update_one(
                {"_id": ObjectId(str(operadora_id))},
                {"$set": registro},
            )
            return str(operadora_id)

        registro["criado_em"] = datetime.datetime.now()
        resultado = self.db.operadores_cartao.insert_one(registro)
        return str(resultado.inserted_id)

    # ==========================================================
    # DASHBOARD
    # ==========================================================

    def resumo_geral(self):
        hoje = datetime.datetime.now()
        inicio_mes = datetime.datetime(
            hoje.year,
            hoje.month,
            1,
        )

        fluxo = self.resumo_fluxo(
            inicio=inicio_mes,
            fim=hoje,
        )

        a_pagar = list(
            self.db.contas_pagar.aggregate([
                {
                    "$match": {
                        "status": {"$in": ["Pendente", "Parcial"]}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": "$valor"},
                        "pago": {"$sum": "$valor_pago"},
                    }
                },
            ])
        )

        a_receber = list(
            self.db.contas_receber.aggregate([
                {
                    "$match": {
                        "status": {"$in": ["Pendente", "Parcial", "Faturado"]}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": "$valor"},
                        "recebido": {"$sum": "$valor_recebido"},
                    }
                },
            ])
        )

        total_pagar = 0.0
        if a_pagar:
            total_pagar = _money(
                a_pagar[0].get("total", 0)
                - a_pagar[0].get("pago", 0)
            )

        total_receber = 0.0
        if a_receber:
            total_receber = _money(
                a_receber[0].get("total", 0)
                - a_receber[0].get("recebido", 0)
            )

        return {
            **fluxo,
            "a_pagar": total_pagar,
            "a_receber": total_receber,
        }