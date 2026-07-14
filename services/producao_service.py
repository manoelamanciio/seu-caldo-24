# -*- coding: utf-8 -*-
"""
Regras de negócio do módulo Produção / Cozinha.
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


class ProducaoService:
    def __init__(self):
        self.db = get_db()

    # ==========================================================
    # FICHAS TÉCNICAS
    # ==========================================================

    def listar_fichas(self, termo=""):
        filtro = {}
        termo = (termo or "").strip()

        if termo:
            filtro = {
                "$or": [
                    {"nome": {"$regex": termo, "$options": "i"}},
                    {"produto_nome": {"$regex": termo, "$options": "i"}},
                ]
            }

        return list(
            self.db.fichas_tecnicas
            .find(filtro)
            .sort("nome", 1)
        )

    def buscar_ficha(self, ficha_id):
        if not ficha_id:
            return None

        return self.db.fichas_tecnicas.find_one({
            "_id": ObjectId(str(ficha_id))
        })

    def calcular_custo_ficha(
        self,
        ingredientes,
        custo_mao_obra=0,
        custo_operacional=0,
    ):
        custo_ingredientes = 0.0

        for item in ingredientes:
            quantidade = float(item.get("quantidade", 0))
            custo_unitario = float(
                item.get("custo_unitario", 0)
            )
            custo_ingredientes += quantidade * custo_unitario

        total = (
            custo_ingredientes
            + float(custo_mao_obra or 0)
            + float(custo_operacional or 0)
        )

        return {
            "custo_ingredientes": _money(custo_ingredientes),
            "custo_mao_obra": _money(custo_mao_obra),
            "custo_operacional": _money(custo_operacional),
            "custo_total": _money(total),
        }

    def salvar_ficha(self, dados, ficha_id=None):
        nome = (dados.get("nome") or "").strip()
        produto_id = dados.get("produto_id")
        ingredientes = dados.get("ingredientes") or []
        rendimento = float(dados.get("rendimento", 0))

        if not nome:
            raise ValueError("Informe o nome da ficha técnica.")

        if not produto_id:
            raise ValueError(
                "Selecione o produto produzido."
            )

        if not ingredientes:
            raise ValueError(
                "Adicione ao menos um ingrediente."
            )

        if rendimento <= 0:
            raise ValueError(
                "O rendimento deve ser maior que zero."
            )

        custos = self.calcular_custo_ficha(
            ingredientes,
            dados.get("custo_mao_obra", 0),
            dados.get("custo_operacional", 0),
        )

        produto = self.db.produtos.find_one({
            "_id": ObjectId(str(produto_id))
        })

        if not produto:
            raise ValueError(
                "Produto produzido não encontrado."
            )

        agora = datetime.datetime.now()

        registro = {
            "nome": nome,
            "produto_id": str(produto["_id"]),
            "produto_nome": produto.get("nome", ""),
            "ingredientes": ingredientes,
            "rendimento": rendimento,
            "unidade_rendimento": dados.get(
                "unidade_rendimento",
                produto.get("unidade", "UN"),
            ),
            "observacoes": (
                dados.get("observacoes") or ""
            ).strip(),
            **custos,
            "custo_unitario_producao": _money(
                custos["custo_total"] / rendimento
            ),
            "atualizado_em": agora,
        }

        if ficha_id:
            self.db.fichas_tecnicas.update_one(
                {"_id": ObjectId(str(ficha_id))},
                {"$set": registro},
            )
            return str(ficha_id)

        registro["criado_em"] = agora

        resultado = self.db.fichas_tecnicas.insert_one(
            registro
        )
        return str(resultado.inserted_id)

    def excluir_ficha(self, ficha_id):
        possui_ordem = (
            self.db.ordens_producao.count_documents({
                "ficha_id": str(ficha_id)
            }) > 0
        )

        if possui_ordem:
            raise ValueError(
                "Esta ficha possui ordens de produção e "
                "não pode ser excluída."
            )

        self.db.fichas_tecnicas.delete_one({
            "_id": ObjectId(str(ficha_id))
        })

    # ==========================================================
    # ORDENS DE PRODUÇÃO
    # ==========================================================

    def listar_ordens(self, status=None):
        filtro = {}
        if status:
            filtro["status"] = status

        return list(
            self.db.ordens_producao
            .find(filtro)
            .sort("data_programada", -1)
        )

    def criar_ordem(
        self,
        ficha_id,
        quantidade_planejada,
        data_programada,
        usuario=None,
        observacoes="",
    ):
        ficha = self.buscar_ficha(ficha_id)

        if not ficha:
            raise ValueError(
                "Ficha técnica não encontrada."
            )

        quantidade_planejada = float(
            quantidade_planejada
        )

        if quantidade_planejada <= 0:
            raise ValueError(
                "A quantidade planejada deve ser maior que zero."
            )

        fator = (
            quantidade_planejada
            / float(ficha.get("rendimento", 1))
        )

        ingredientes_planejados = []

        for item in ficha.get("ingredientes", []):
            ingredientes_planejados.append({
                **item,
                "quantidade_necessaria": round(
                    float(item.get("quantidade", 0))
                    * fator,
                    4,
                ),
            })

        numero = self.db.proximo_numero("ordem_producao")

        ordem = {
            "numero": numero,
            "ficha_id": str(ficha["_id"]),
            "ficha_nome": ficha.get("nome", ""),
            "produto_id": ficha.get("produto_id"),
            "produto_nome": ficha.get("produto_nome", ""),
            "quantidade_planejada": quantidade_planejada,
            "quantidade_produzida": 0.0,
            "unidade": ficha.get(
                "unidade_rendimento",
                "UN",
            ),
            "ingredientes_planejados": ingredientes_planejados,
            "status": "Planejada",
            "data_programada": data_programada,
            "iniciada_em": None,
            "finalizada_em": None,
            "observacoes": observacoes.strip(),
            "usuario_id": (
                str(usuario.get("_id"))
                if usuario
                else None
            ),
            "usuario_nome": (
                usuario.get("nome")
                if usuario
                else None
            ),
            "criado_em": datetime.datetime.now(),
        }

        resultado = self.db.ordens_producao.insert_one(
            ordem
        )

        return str(resultado.inserted_id), numero

    def validar_estoque_para_ordem(self, ordem_id):
        ordem = self.db.ordens_producao.find_one({
            "_id": ObjectId(str(ordem_id))
        })

        if not ordem:
            raise ValueError(
                "Ordem de produção não encontrada."
            )

        faltantes = []

        for item in ordem.get(
            "ingredientes_planejados",
            [],
        ):
            produto = self.db.produtos.find_one({
                "_id": ObjectId(
                    str(item["produto_id"])
                )
            })

            estoque = float(
                produto.get("estoque_atual", 0)
                if produto
                else 0
            )
            necessario = float(
                item.get("quantidade_necessaria", 0)
            )

            if estoque < necessario:
                faltantes.append({
                    "produto_nome": item.get(
                        "produto_nome",
                        "",
                    ),
                    "necessario": necessario,
                    "disponivel": estoque,
                })

        return faltantes

    def iniciar_ordem(self, ordem_id):
        ordem = self.db.ordens_producao.find_one({
            "_id": ObjectId(str(ordem_id))
        })

        if not ordem:
            raise ValueError(
                "Ordem de produção não encontrada."
            )

        if ordem.get("status") != "Planejada":
            raise ValueError(
                "Somente ordens planejadas podem ser iniciadas."
            )

        faltantes = self.validar_estoque_para_ordem(
            ordem_id
        )

        if faltantes:
            detalhes = "\n".join(
                (
                    f"- {item['produto_nome']}: "
                    f"necessário {item['necessario']}, "
                    f"disponível {item['disponivel']}"
                )
                for item in faltantes
            )
            raise ValueError(
                "Estoque insuficiente:\n" + detalhes
            )

        agora = datetime.datetime.now()

        for item in ordem.get(
            "ingredientes_planejados",
            [],
        ):
            produto_id = ObjectId(
                str(item["produto_id"])
            )
            quantidade = float(
                item.get("quantidade_necessaria", 0)
            )

            produto = self.db.produtos.find_one({
                "_id": produto_id
            })

            estoque_anterior = float(
                produto.get("estoque_atual", 0)
            )
            estoque_posterior = (
                estoque_anterior - quantidade
            )

            self.db.produtos.update_one(
                {"_id": produto_id},
                {"$set": {
                    "estoque_atual": estoque_posterior,
                    "atualizado_em": agora,
                }},
            )

            self.db.movimentacoes_estoque.insert_one({
                "produto_id": str(produto_id),
                "produto_nome": produto.get("nome", ""),
                "tipo": "Saída para produção",
                "setor": produto.get("setor", ""),
                "quantidade": quantidade,
                "estoque_anterior": estoque_anterior,
                "estoque_posterior": estoque_posterior,
                "motivo": (
                    f"Ordem de produção nº "
                    f"{ordem.get('numero')}"
                ),
                "data": agora,
            })

        self.db.ordens_producao.update_one(
            {"_id": ordem["_id"]},
            {"$set": {
                "status": "Em Produção",
                "iniciada_em": agora,
            }},
        )

    def finalizar_ordem(
        self,
        ordem_id,
        quantidade_produzida,
        perda=0,
        observacoes="",
    ):
        ordem = self.db.ordens_producao.find_one({
            "_id": ObjectId(str(ordem_id))
        })

        if not ordem:
            raise ValueError(
                "Ordem de produção não encontrada."
            )

        if ordem.get("status") != "Em Produção":
            raise ValueError(
                "Somente ordens em produção podem ser finalizadas."
            )

        quantidade_produzida = float(
            quantidade_produzida
        )
        perda = float(perda or 0)

        if quantidade_produzida <= 0:
            raise ValueError(
                "A quantidade produzida deve ser maior que zero."
            )

        produto_id = ObjectId(
            str(ordem["produto_id"])
        )
        produto = self.db.produtos.find_one({
            "_id": produto_id
        })

        if not produto:
            raise ValueError(
                "Produto final não encontrado."
            )

        agora = datetime.datetime.now()

        estoque_anterior = float(
            produto.get("estoque_atual", 0)
        )
        estoque_posterior = (
            estoque_anterior + quantidade_produzida
        )

        self.db.produtos.update_one(
            {"_id": produto_id},
            {"$set": {
                "estoque_atual": estoque_posterior,
                "atualizado_em": agora,
            }},
        )

        self.db.movimentacoes_estoque.insert_one({
            "produto_id": str(produto_id),
            "produto_nome": produto.get("nome", ""),
            "tipo": "Entrada de produção",
            "setor": produto.get("setor", ""),
            "quantidade": quantidade_produzida,
            "estoque_anterior": estoque_anterior,
            "estoque_posterior": estoque_posterior,
            "motivo": (
                f"Finalização da ordem nº "
                f"{ordem.get('numero')}"
            ),
            "data": agora,
        })

        if perda > 0:
            self.db.movimentacoes_estoque.insert_one({
                "produto_id": str(produto_id),
                "produto_nome": produto.get("nome", ""),
                "tipo": "Perda de produção",
                "setor": produto.get("setor", ""),
                "quantidade": perda,
                "motivo": (
                    f"Perda registrada na ordem nº "
                    f"{ordem.get('numero')}"
                ),
                "data": agora,
            })

        self.db.ordens_producao.update_one(
            {"_id": ordem["_id"]},
            {"$set": {
                "status": "Finalizada",
                "quantidade_produzida": quantidade_produzida,
                "perda": perda,
                "finalizada_em": agora,
                "observacoes_finalizacao": observacoes.strip(),
            }},
        )

    def cancelar_ordem(self, ordem_id):
        ordem = self.db.ordens_producao.find_one({
            "_id": ObjectId(str(ordem_id))
        })

        if not ordem:
            raise ValueError(
                "Ordem de produção não encontrada."
            )

        if ordem.get("status") == "Finalizada":
            raise ValueError(
                "Uma ordem finalizada não pode ser cancelada."
            )

        if ordem.get("status") == "Em Produção":
            raise ValueError(
                "Ordens em produção devem ser concluídas "
                "ou ajustadas manualmente."
            )

        self.db.ordens_producao.update_one(
            {"_id": ordem["_id"]},
            {"$set": {
                "status": "Cancelada",
                "cancelada_em": datetime.datetime.now(),
            }},
        )

    # ==========================================================
    # INDICADORES
    # ==========================================================

    def resumo(self):
        return {
            "fichas": self.db.fichas_tecnicas.count_documents({}),
            "planejadas": self.db.ordens_producao.count_documents({
                "status": "Planejada"
            }),
            "em_producao": self.db.ordens_producao.count_documents({
                "status": "Em Produção"
            }),
            "finalizadas": self.db.ordens_producao.count_documents({
                "status": "Finalizada"
            }),
        }