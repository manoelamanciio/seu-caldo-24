# -*- coding: utf-8 -*-
"""
Regras de negócio do módulo Clientes / Fidelidade.
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


class ClientesService:
    def __init__(self):
        self.db = get_db()

    # ==========================================================
    # CLIENTES
    # ==========================================================

    def listar_clientes(self, termo=""):
        filtro = {}

        termo = (termo or "").strip()
        if termo:
            filtro = {
                "$or": [
                    {"nome_razao": {"$regex": termo, "$options": "i"}},
                    {"nome_fantasia": {"$regex": termo, "$options": "i"}},
                    {"cpf_cnpj": {"$regex": termo, "$options": "i"}},
                    {"telefone": {"$regex": termo, "$options": "i"}},
                    {"email": {"$regex": termo, "$options": "i"}},
                ]
            }

        return list(
            self.db.clientes
            .find(filtro)
            .sort("nome_razao", 1)
        )

    def buscar_cliente(self, cliente_id):
        if not cliente_id:
            return None

        return self.db.clientes.find_one({
            "_id": ObjectId(str(cliente_id))
        })

    def salvar_cliente(self, dados, cliente_id=None):
        nome = (dados.get("nome_razao") or "").strip()
        documento = (dados.get("cpf_cnpj") or "").strip()

        if not nome:
            raise ValueError("Informe o nome ou razão social.")

        if documento:
            duplicado = self.db.clientes.find_one({
                "cpf_cnpj": documento
            })

            if duplicado and (
                not cliente_id
                or str(duplicado["_id"]) != str(cliente_id)
            ):
                raise ValueError(
                    "Já existe um cliente com este CPF/CNPJ."
                )

        agora = datetime.datetime.now()

        registro = {
            "tipo_pessoa": dados.get("tipo_pessoa", "PF"),
            "nome_razao": nome,
            "nome_fantasia": (
                dados.get("nome_fantasia") or ""
            ).strip(),
            "cpf_cnpj": documento,
            "telefone": (
                dados.get("telefone") or ""
            ).strip(),
            "email": (
                dados.get("email") or ""
            ).strip(),
            "endereco": (
                dados.get("endereco") or ""
            ).strip(),
            "cidade": (
                dados.get("cidade") or ""
            ).strip(),
            "observacoes": (
                dados.get("observacoes") or ""
            ).strip(),
            "correntista": bool(
                dados.get("correntista", False)
            ),
            "limite_credito": _money(
                dados.get("limite_credito", 0)
            ),
            "dia_fechamento": int(
                dados.get("dia_fechamento", 30)
            ),
            "ativo": bool(dados.get("ativo", True)),
            "atualizado_em": agora,
        }

        if cliente_id:
            self.db.clientes.update_one(
                {"_id": ObjectId(str(cliente_id))},
                {"$set": registro},
            )
            return str(cliente_id)

        registro.update({
            "saldo_correntista": 0.0,
            "pontos": 0,
            "bloqueado": False,
            "motivo_bloqueio": "",
            "criado_em": agora,
        })

        resultado = self.db.clientes.insert_one(registro)
        return str(resultado.inserted_id)

    def excluir_cliente(self, cliente_id):
        cliente = self.buscar_cliente(cliente_id)

        if not cliente:
            raise ValueError("Cliente não encontrado.")

        possui_faturas = (
            self.db.faturas.count_documents({
                "cliente_id": str(cliente["_id"])
            }) > 0
        )

        possui_vendas = (
            self.db.vendas.count_documents({
                "cliente_id": str(cliente["_id"])
            }) > 0
        )

        if possui_faturas or possui_vendas:
            raise ValueError(
                "Este cliente possui histórico financeiro ou de vendas. "
                "Desative o cadastro em vez de excluí-lo."
            )

        self.db.clientes.delete_one({
            "_id": cliente["_id"]
        })

    def alternar_ativo(self, cliente_id):
        cliente = self.buscar_cliente(cliente_id)

        if not cliente:
            raise ValueError("Cliente não encontrado.")

        novo_status = not cliente.get("ativo", True)

        self.db.clientes.update_one(
            {"_id": cliente["_id"]},
            {"$set": {
                "ativo": novo_status,
                "atualizado_em": datetime.datetime.now(),
            }},
        )

        return novo_status

    # ==========================================================
    # CORRENTISTA / CRÉDITO
    # ==========================================================

    def credito_disponivel(self, cliente_id):
        cliente = self.buscar_cliente(cliente_id)

        if not cliente:
            return 0.0

        limite = _money(cliente.get("limite_credito", 0))
        saldo = _money(cliente.get("saldo_correntista", 0))

        return max(_money(limite - saldo), 0.0)

    def validar_compra_correntista(self, cliente_id, valor):
        cliente = self.buscar_cliente(cliente_id)

        if not cliente:
            raise ValueError("Cliente não encontrado.")

        if not cliente.get("ativo", True):
            raise ValueError("Cliente inativo.")

        if not cliente.get("correntista", False):
            raise ValueError(
                "Cliente não está habilitado como correntista."
            )

        if cliente.get("bloqueado", False):
            motivo = cliente.get(
                "motivo_bloqueio",
                "Cliente bloqueado.",
            )
            raise ValueError(motivo)

        valor = _money(valor)
        disponivel = self.credito_disponivel(cliente_id)

        if valor > disponivel:
            raise ValueError(
                f"Limite insuficiente. Disponível: R$ {disponivel:.2f}"
            )

        return True

    def lancar_consumo(self, cliente_id, valor, descricao="", origem="Manual"):
        self.validar_compra_correntista(cliente_id, valor)

        cliente = self.buscar_cliente(cliente_id)
        valor = _money(valor)

        numero = self.db.proximo_numero("consumo_correntista")

        lancamento = {
            "numero": numero,
            "cliente_id": str(cliente["_id"]),
            "cliente_nome": cliente.get("nome_razao", ""),
            "descricao": descricao.strip() or "Consumo correntista",
            "valor": valor,
            "origem": origem,
            "status": "Pendente",
            "data": datetime.datetime.now(),
        }

        self.db.contas_receber.insert_one(lancamento)

        self.db.clientes.update_one(
            {"_id": cliente["_id"]},
            {
                "$inc": {"saldo_correntista": valor},
                "$set": {"atualizado_em": datetime.datetime.now()},
            },
        )

        return numero

    def bloquear_cliente(self, cliente_id, motivo):
        cliente = self.buscar_cliente(cliente_id)

        if not cliente:
            raise ValueError("Cliente não encontrado.")

        self.db.clientes.update_one(
            {"_id": cliente["_id"]},
            {"$set": {
                "bloqueado": True,
                "motivo_bloqueio": motivo.strip()
                or "Bloqueio administrativo",
                "atualizado_em": datetime.datetime.now(),
            }},
        )

    def desbloquear_cliente(self, cliente_id):
        cliente = self.buscar_cliente(cliente_id)

        if not cliente:
            raise ValueError("Cliente não encontrado.")

        self.db.clientes.update_one(
            {"_id": cliente["_id"]},
            {"$set": {
                "bloqueado": False,
                "motivo_bloqueio": "",
                "atualizado_em": datetime.datetime.now(),
            }},
        )

    def verificar_bloqueios_por_atraso(self):
        hoje = datetime.datetime.now()

        atrasados = list(
            self.db.faturas.find({
                "status": "Pendente",
                "vencimento": {"$lt": hoje},
            })
        )

        clientes_bloqueados = set()

        for fatura in atrasados:
            cliente_id = fatura.get("cliente_id")
            if not cliente_id:
                continue

            clientes_bloqueados.add(cliente_id)

            self.db.clientes.update_one(
                {"_id": ObjectId(cliente_id)},
                {"$set": {
                    "bloqueado": True,
                    "motivo_bloqueio": (
                        "Bloqueio automático por fatura vencida."
                    ),
                    "atualizado_em": hoje,
                }},
            )

        return len(clientes_bloqueados)

    # ==========================================================
    # FATURAS
    # ==========================================================

    def gerar_fatura(self, cliente_id, vencimento):
        cliente = self.buscar_cliente(cliente_id)

        if not cliente:
            raise ValueError("Cliente não encontrado.")

        consumos = list(
            self.db.contas_receber.find({
                "cliente_id": str(cliente["_id"]),
                "status": "Pendente",
                "fatura_id": {"$exists": False},
            }).sort("data", 1)
        )

        if not consumos:
            raise ValueError(
                "Não há consumos pendentes para faturar."
            )

        total = _money(
            sum(_money(item.get("valor", 0)) for item in consumos)
        )

        numero = self.db.proximo_numero("fatura")

        fatura = {
            "numero": numero,
            "cliente_id": str(cliente["_id"]),
            "cliente_nome": cliente.get("nome_razao", ""),
            "itens": [
                {
                    "consumo_id": str(item["_id"]),
                    "descricao": item.get("descricao", ""),
                    "data": item.get("data"),
                    "valor": _money(item.get("valor", 0)),
                }
                for item in consumos
            ],
            "valor": total,
            "status": "Pendente",
            "emissao": datetime.datetime.now(),
            "vencimento": vencimento,
            "pago_em": None,
        }

        resultado = self.db.faturas.insert_one(fatura)
        fatura_id = str(resultado.inserted_id)

        ids = [item["_id"] for item in consumos]

        self.db.contas_receber.update_many(
            {"_id": {"$in": ids}},
            {"$set": {
                "fatura_id": fatura_id,
                "status": "Faturado",
            }},
        )

        return numero

    def listar_faturas(self, cliente_id=None):
        filtro = {}

        if cliente_id:
            filtro["cliente_id"] = str(cliente_id)

        return list(
            self.db.faturas
            .find(filtro)
            .sort("emissao", -1)
        )

    def registrar_pagamento_fatura(self, fatura_id):
        fatura = self.db.faturas.find_one({
            "_id": ObjectId(str(fatura_id))
        })

        if not fatura:
            raise ValueError("Fatura não encontrada.")

        if fatura.get("status") == "Paga":
            raise ValueError("Esta fatura já está paga.")

        agora = datetime.datetime.now()

        self.db.faturas.update_one(
            {"_id": fatura["_id"]},
            {"$set": {
                "status": "Paga",
                "pago_em": agora,
            }},
        )

        self.db.clientes.update_one(
            {"_id": ObjectId(fatura["cliente_id"])},
            {
                "$inc": {
                    "saldo_correntista": -_money(
                        fatura.get("valor", 0)
                    )
                },
                "$set": {
                    "bloqueado": False,
                    "motivo_bloqueio": "",
                    "atualizado_em": agora,
                },
            },
        )

    # ==========================================================
    # FIDELIDADE
    # ==========================================================

    def adicionar_pontos(self, cliente_id, pontos, motivo=""):
        pontos = int(pontos)

        if pontos <= 0:
            raise ValueError(
                "A quantidade de pontos deve ser maior que zero."
            )

        cliente = self.buscar_cliente(cliente_id)

        if not cliente:
            raise ValueError("Cliente não encontrado.")

        self.db.clientes.update_one(
            {"_id": cliente["_id"]},
            {
                "$inc": {"pontos": pontos},
                "$set": {"atualizado_em": datetime.datetime.now()},
            },
        )

        self.db.auditoria.insert_one({
            "tipo": "Pontos adicionados",
            "cliente_id": str(cliente["_id"]),
            "cliente_nome": cliente.get("nome_razao", ""),
            "pontos": pontos,
            "motivo": motivo.strip(),
            "data": datetime.datetime.now(),
        })

    def listar_premios(self, somente_ativos=False):
        filtro = {"ativo": True} if somente_ativos else {}

        return list(
            self.db.premios_fidelidade
            .find(filtro)
            .sort("pontos_necessarios", 1)
        )

    def salvar_premio(self, dados, premio_id=None):
        nome = (dados.get("nome") or "").strip()
        pontos = int(dados.get("pontos_necessarios", 0))

        if not nome:
            raise ValueError("Informe o nome do prêmio.")

        if pontos <= 0:
            raise ValueError(
                "Informe uma quantidade válida de pontos."
            )

        registro = {
            "nome": nome,
            "descricao": (
                dados.get("descricao") or ""
            ).strip(),
            "pontos_necessarios": pontos,
            "ativo": bool(dados.get("ativo", True)),
            "atualizado_em": datetime.datetime.now(),
        }

        if premio_id:
            self.db.premios_fidelidade.update_one(
                {"_id": ObjectId(str(premio_id))},
                {"$set": registro},
            )
            return str(premio_id)

        registro["criado_em"] = datetime.datetime.now()

        resultado = self.db.premios_fidelidade.insert_one(
            registro
        )
        return str(resultado.inserted_id)

    def resgatar_premio(self, cliente_id, premio_id):
        cliente = self.buscar_cliente(cliente_id)

        if not cliente:
            raise ValueError("Cliente não encontrado.")

        premio = self.db.premios_fidelidade.find_one({
            "_id": ObjectId(str(premio_id)),
            "ativo": True,
        })

        if not premio:
            raise ValueError(
                "Prêmio não encontrado ou inativo."
            )

        pontos_atuais = int(cliente.get("pontos", 0))
        pontos_necessarios = int(
            premio.get("pontos_necessarios", 0)
        )

        if pontos_atuais < pontos_necessarios:
            raise ValueError(
                "O cliente não possui pontos suficientes."
            )

        agora = datetime.datetime.now()

        self.db.clientes.update_one(
            {"_id": cliente["_id"]},
            {
                "$inc": {"pontos": -pontos_necessarios},
                "$set": {"atualizado_em": agora},
            },
        )

        self.db.resgates_fidelidade.insert_one({
            "cliente_id": str(cliente["_id"]),
            "cliente_nome": cliente.get("nome_razao", ""),
            "premio_id": str(premio["_id"]),
            "premio_nome": premio.get("nome", ""),
            "pontos_utilizados": pontos_necessarios,
            "data": agora,
        })

    def historico_cliente(self, cliente_id):
        cliente_id = str(cliente_id)

        consumos = list(
            self.db.contas_receber
            .find({"cliente_id": cliente_id})
            .sort("data", -1)
            .limit(100)
        )

        faturas = list(
            self.db.faturas
            .find({"cliente_id": cliente_id})
            .sort("emissao", -1)
            .limit(100)
        )

        resgates = list(
            self.db.resgates_fidelidade
            .find({"cliente_id": cliente_id})
            .sort("data", -1)
            .limit(100)
        )

        return {
            "consumos": consumos,
            "faturas": faturas,
            "resgates": resgates,
        }