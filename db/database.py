# -*- coding: utf-8 -*-
"""
Camada de acesso ao MongoDB.
Centraliza a conexão e expõe as coleções usadas pelo sistema.
"""

import sys
import datetime
import bcrypt

from pymongo import MongoClient, ASCENDING
from pymongo.errors import ServerSelectionTimeoutError

sys.path.append("..")

from config import MONGO_URI, MONGO_DB_NAME


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        try:
            self.client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=4000
            )
            self.client.server_info()
            self.db = self.client[MONGO_DB_NAME]
            self.online = True
        except ServerSelectionTimeoutError:
            self.client = None
            self.db = None
            self.online = False

    # ==========================================================
    # COLEÇÕES
    # ==========================================================

    @property
    def usuarios(self):
        return self.db["usuarios"]

    @property
    def produtos(self):
        return self.db["produtos"]

    @property
    def categorias(self):
        return self.db["categorias"]

    @property
    def fornecedores(self):
        return self.db["fornecedores"]

    @property
    def clientes(self):
        return self.db["clientes"]

    @property
    def movimentacoes_estoque(self):
        return self.db["movimentacoes_estoque"]

    @property
    def fichas_tecnicas(self):
        return self.db["fichas_tecnicas"]

    @property
    def ordens_producao(self):
        return self.db["ordens_producao"]

    @property
    def comandas(self):
        return self.db["comandas"]

    @property
    def vendas(self):
        return self.db["vendas"]

    @property
    def contas_pagar(self):
        return self.db["contas_pagar"]

    @property
    def contas_receber(self):
        return self.db["contas_receber"]

    @property
    def caixa_movimentos(self):
        return self.db["caixa_movimentos"]

    @property
    def faturas(self):
        return self.db["faturas"]

    @property
    def promocoes(self):
        return self.db["promocoes"]

    @property
    def cotacoes(self):
        return self.db["cotacoes"]

    @property
    def kits(self):
        return self.db["kits"]

    @property
    def auditoria(self):
        return self.db["auditoria"]

    @property
    def contas_bancarias(self):
        return self.db["contas_bancarias"]

    @property
    def operadores_cartao(self):
        return self.db["operadores_cartao"]

    @property
    def recebimentos_cartao(self):
        return self.db["recebimentos_cartao"]

    @property
    def mesas(self):
        return self.db["mesas"]

    @property
    def deliveries(self):
        return self.db["deliveries"]

    @property
    def encomendas(self):
        return self.db["encomendas"]

    @property
    def premios_fidelidade(self):
        return self.db["premios_fidelidade"]

    @property
    def resgates_fidelidade(self):
        return self.db["resgates_fidelidade"]

    @property
    def ordens_compra(self):
        return self.db["ordens_compra"]

    @property
    def configuracoes(self):
        return self.db["configuracoes"]

    @property
    def contador(self):
        return self.db["contadores"]

    # ==========================================================
    # CONTADOR SEQUENCIAL
    # ==========================================================

    def proximo_numero(self, chave):
        doc = self.contador.find_one_and_update(
            {"_id": chave},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True,
        )

        return doc["seq"]

    # ==========================================================
    # ÍNDICES
    # ==========================================================

    def criar_indices(self):
        # Produtos
        self.produtos.create_index([("nome", ASCENDING)])
        self.produtos.create_index(
            [("codigo_barras", ASCENDING)],
            unique=False
        )
        self.produtos.create_index([("categoria", ASCENDING)])
        self.produtos.create_index([("setor", ASCENDING)])

        # Clientes
        self.clientes.create_index([("cpf_cnpj", ASCENDING)])

        # Fornecedores
        self.fornecedores.create_index([("cnpj", ASCENDING)])

        # Usuários
        self.usuarios.create_index(
            [("login", ASCENDING)],
            unique=True
        )

        # Movimentações de estoque
        self.movimentacoes_estoque.create_index(
            [("produto_id", ASCENDING)]
        )
        self.movimentacoes_estoque.create_index(
            [("data", ASCENDING)]
        )

    def seed_inicial(self):

        if self.usuarios.count_documents({}) == 0:

            senha_hash = bcrypt.hashpw(
                "admin123".encode(),
                bcrypt.gensalt()
            )

            self.usuarios.insert_one({
                "nome": "Administrador",
                "login": "admin",
                "senha_hash": senha_hash,
                "perfil": "Administrador",
                "ativo": True,
                "criado_em": datetime.datetime.now(),
            })

        if self.categorias.count_documents({}) == 0:

            self.categorias.insert_many([
                {
                    "nome": "Bebidas",
                    "setor_padrao": "Loja"
                },
                {
                    "nome": "Caldos",
                    "setor_padrao": "Cozinha"
                },
                {
                    "nome": "Porções",
                    "setor_padrao": "Cozinha"
                },
                {
                    "nome": "Descartáveis",
                    "setor_padrao": "Depósito"
                },
                {
                    "nome": "Insumos",
                    "setor_padrao": "Depósito"
                },
            ])


def get_db() -> Database:
    return Database()