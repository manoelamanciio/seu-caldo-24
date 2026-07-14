# -*- coding: utf-8 -*-

import datetime
from bson import ObjectId

from db.database import get_db


class EstoqueService:
    def __init__(self):
        self.db = get_db()

    def listar_produtos(self, termo=""):
        filtro = {}

        if termo:
            filtro = {
                "$or": [
                    {"nome": {"$regex": termo, "$options": "i"}},
                    {"codigo_barras": {"$regex": termo, "$options": "i"}},
                    {"categoria": {"$regex": termo, "$options": "i"}},
                ]
            }

        return list(self.db.produtos.find(filtro).sort("nome", 1))

    def buscar_produto(self, produto_id):
        if not produto_id:
            return None

        return self.db.produtos.find_one({
            "_id": ObjectId(produto_id)
        })

    def salvar_produto(self, dados, produto_id=None):
        agora = datetime.datetime.now()

        dados["atualizado_em"] = agora

        if produto_id:
            self.db.produtos.update_one(
                {"_id": ObjectId(produto_id)},
                {"$set": dados}
            )
            return produto_id

        dados["criado_em"] = agora
        resultado = self.db.produtos.insert_one(dados)
        return str(resultado.inserted_id)

    def excluir_produto(self, produto_id):
        produto = self.buscar_produto(produto_id)

        if not produto:
            raise ValueError("Produto não encontrado.")

        movimentacoes = self.db.movimentacoes_estoque.count_documents({
            "produto_id": str(produto["_id"])
        })

        if movimentacoes > 0:
            raise ValueError(
                "Este produto possui movimentações e não pode ser excluído."
            )

        return self.db.produtos.delete_one({
            "_id": produto["_id"]
        })

    def movimentar(
        self,
        produto_id,
        tipo,
        quantidade,
        motivo="",
        setor_destino=None,
        usuario=None,
    ):
        produto = self.buscar_produto(produto_id)

        if not produto:
            raise ValueError("Produto não encontrado.")

        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")

        estoque_atual = float(produto.get("estoque_atual", 0))
        setor_origem = produto.get("setor", "")
        setor_final = setor_origem
        novo_estoque = estoque_atual

        if tipo == "Entrada":
            novo_estoque += quantidade

        elif tipo in ("Saída", "Perda/Quebra"):
            if quantidade > estoque_atual:
                raise ValueError(
                    "Quantidade maior que o estoque disponível."
                )

            novo_estoque -= quantidade

        elif tipo == "Transferência entre setores":
            if not setor_destino:
                raise ValueError("Informe o setor de destino.")

            if setor_destino == setor_origem:
                raise ValueError(
                    "O setor de destino deve ser diferente do setor atual."
                )

            setor_final = setor_destino

        elif tipo == "Ajuste positivo":
            novo_estoque += quantidade

        elif tipo == "Ajuste negativo":
            if quantidade > estoque_atual:
                raise ValueError(
                    "O ajuste deixaria o estoque negativo."
                )

            novo_estoque -= quantidade

        else:
            raise ValueError("Tipo de movimentação inválido.")

        self.db.produtos.update_one(
            {"_id": produto["_id"]},
            {
                "$set": {
                    "estoque_atual": novo_estoque,
                    "setor": setor_final,
                    "atualizado_em": datetime.datetime.now(),
                }
            }
        )

        movimento = {
            "produto_id": str(produto["_id"]),
            "produto_nome": produto.get("nome", ""),
            "tipo": tipo,
            "setor_origem": setor_origem,
            "setor_destino": setor_final,
            "setor": setor_final,
            "quantidade": quantidade,
            "estoque_anterior": estoque_atual,
            "estoque_posterior": novo_estoque,
            "motivo": motivo,
            "usuario_id": str(usuario.get("_id")) if usuario else None,
            "usuario_nome": usuario.get("nome") if usuario else None,
            "data": datetime.datetime.now(),
        }

        resultado = self.db.movimentacoes_estoque.insert_one(movimento)
        return str(resultado.inserted_id)

    def produtos_com_estoque_baixo(self):
        return list(self.db.produtos.find({
            "$expr": {
                "$lte": [
                    "$estoque_atual",
                    "$estoque_minimo",
                ]
            }
        }).sort("nome", 1))

    def historico_produto(self, produto_id, limite=200):
        return list(
            self.db.movimentacoes_estoque
            .find({"produto_id": str(produto_id)})
            .sort("data", -1)
            .limit(limite)
        )

    def gerar_planejamento_compras(self):
        produtos = self.produtos_com_estoque_baixo()
        planejamento = []

        for produto in produtos:
            atual = float(produto.get("estoque_atual", 0))
            minimo = float(produto.get("estoque_minimo", 0))
            estoque_ideal = float(
                produto.get("estoque_ideal", minimo * 2)
            )

            quantidade_sugerida = max(estoque_ideal - atual, 0)

            planejamento.append({
                "produto_id": str(produto["_id"]),
                "produto_nome": produto.get("nome", ""),
                "fornecedor_id": produto.get("fornecedor_id"),
                "estoque_atual": atual,
                "estoque_minimo": minimo,
                "estoque_ideal": estoque_ideal,
                "quantidade_sugerida": quantidade_sugerida,
                "custo_unitario": float(produto.get("custo", 0)),
                "custo_estimado": (
                    quantidade_sugerida *
                    float(produto.get("custo", 0))
                ),
            })

        return planejamento