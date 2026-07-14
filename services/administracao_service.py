# -*- coding: utf-8 -*-
"""
Regras de negócio do módulo Administração / Configurações.
Sistema Seu Caldo 24 - M.A Sistemas
"""

import datetime
import json
from pathlib import Path

import bcrypt
from bson import ObjectId, json_util

from db.database import get_db


COLECOES_BACKUP = [
    "usuarios",
    "produtos",
    "categorias",
    "fornecedores",
    "clientes",
    "movimentacoes_estoque",
    "fichas_tecnicas",
    "ordens_producao",
    "comandas",
    "vendas",
    "contas_pagar",
    "contas_receber",
    "caixa_movimentos",
    "faturas",
    "promocoes",
    "cotacoes",
    "kits",
    "auditoria",
    "contas_bancarias",
    "operadores_cartao",
    "recebimentos_cartao",
    "mesas",
    "deliveries",
    "encomendas",
    "premios_fidelidade",
    "resgates_fidelidade",
    "ordens_compra",
    "configuracoes",
    "contadores",
]


class AdministracaoService:
    def __init__(self):
        self.db = get_db()

    # ==========================================================
    # CONFIGURAÇÕES DA EMPRESA
    # ==========================================================

    def obter_configuracoes(self):
        configuracao = self.db.configuracoes.find_one({
            "_id": "empresa"
        })

        if configuracao:
            return configuracao

        return {
            "_id": "empresa",
            "razao_social": "Seu Caldo 24",
            "nome_fantasia": "Seu Caldo 24",
            "cnpj": "",
            "endereco": "",
            "cidade": "",
            "telefone": "",
            "email": "",
            "chave_pix": "",
            "rodape_relatorios": "Desenvolvido por M.A Sistemas",
            "pontos_por_real": 1,
            "backup_automatico": False,
            "hora_backup": "23:00",
        }

    def salvar_configuracoes(self, dados, usuario=None):
        agora = datetime.datetime.now()

        registro = {
            "_id": "empresa",
            "razao_social": (dados.get("razao_social") or "").strip(),
            "nome_fantasia": (dados.get("nome_fantasia") or "").strip(),
            "cnpj": (dados.get("cnpj") or "").strip(),
            "endereco": (dados.get("endereco") or "").strip(),
            "cidade": (dados.get("cidade") or "").strip(),
            "telefone": (dados.get("telefone") or "").strip(),
            "email": (dados.get("email") or "").strip(),
            "chave_pix": (dados.get("chave_pix") or "").strip(),
            "rodape_relatorios": (
                dados.get("rodape_relatorios") or ""
            ).strip(),
            "pontos_por_real": int(dados.get("pontos_por_real", 1)),
            "backup_automatico": bool(
                dados.get("backup_automatico", False)
            ),
            "hora_backup": (dados.get("hora_backup") or "23:00").strip(),
            "atualizado_em": agora,
        }

        if not registro["nome_fantasia"]:
            raise ValueError("Informe o nome fantasia.")

        self.db.configuracoes.replace_one(
            {"_id": "empresa"},
            registro,
            upsert=True,
        )

        self.registrar_auditoria(
            usuario,
            "Configurações atualizadas",
            "Dados da empresa e parâmetros gerais foram alterados.",
        )

    # ==========================================================
    # USUÁRIOS
    # ==========================================================

    def listar_usuarios(self):
        return list(
            self.db.usuarios.find().sort("nome", 1)
        )

    def buscar_usuario(self, usuario_id):
        return self.db.usuarios.find_one({
            "_id": ObjectId(str(usuario_id))
        })

    def salvar_usuario(self, dados, usuario_id=None, operador=None):
        nome = (dados.get("nome") or "").strip()
        login = (dados.get("login") or "").strip()
        senha = dados.get("senha") or ""
        perfil = (dados.get("perfil") or "").strip()

        if not nome:
            raise ValueError("Informe o nome do usuário.")

        if not login:
            raise ValueError("Informe o login.")

        if not perfil:
            raise ValueError("Informe o perfil.")

        duplicado = self.db.usuarios.find_one({"login": login})

        if duplicado and (
            not usuario_id
            or str(duplicado["_id"]) != str(usuario_id)
        ):
            raise ValueError("Este login já está em uso.")

        agora = datetime.datetime.now()

        registro = {
            "nome": nome,
            "login": login,
            "perfil": perfil,
            "ativo": bool(dados.get("ativo", True)),
            "permissoes": dados.get("permissoes", []),
            "atualizado_em": agora,
        }

        if usuario_id:
            if senha:
                registro["senha_hash"] = bcrypt.hashpw(
                    senha.encode("utf-8"),
                    bcrypt.gensalt(),
                )

            self.db.usuarios.update_one(
                {"_id": ObjectId(str(usuario_id))},
                {"$set": registro},
            )

            self.registrar_auditoria(
                operador,
                "Usuário editado",
                f"Usuário '{nome}' foi atualizado.",
            )
            return str(usuario_id)

        if not senha:
            raise ValueError("Informe a senha inicial.")

        registro["senha_hash"] = bcrypt.hashpw(
            senha.encode("utf-8"),
            bcrypt.gensalt(),
        )
        registro["criado_em"] = agora

        resultado = self.db.usuarios.insert_one(registro)

        self.registrar_auditoria(
            operador,
            "Usuário criado",
            f"Usuário '{nome}' foi cadastrado.",
        )

        return str(resultado.inserted_id)

    def alternar_usuario(self, usuario_id, operador=None):
        usuario = self.buscar_usuario(usuario_id)

        if not usuario:
            raise ValueError("Usuário não encontrado.")

        novo_status = not usuario.get("ativo", True)

        self.db.usuarios.update_one(
            {"_id": usuario["_id"]},
            {"$set": {
                "ativo": novo_status,
                "atualizado_em": datetime.datetime.now(),
            }},
        )

        self.registrar_auditoria(
            operador,
            "Status de usuário alterado",
            (
                f"Usuário '{usuario.get('nome', '')}' ficou "
                f"{'ativo' if novo_status else 'inativo'}."
            ),
        )

        return novo_status

    def alterar_senha(self, usuario_id, nova_senha, operador=None):
        if len(nova_senha) < 6:
            raise ValueError(
                "A senha deve ter pelo menos 6 caracteres."
            )

        usuario = self.buscar_usuario(usuario_id)

        if not usuario:
            raise ValueError("Usuário não encontrado.")

        senha_hash = bcrypt.hashpw(
            nova_senha.encode("utf-8"),
            bcrypt.gensalt(),
        )

        self.db.usuarios.update_one(
            {"_id": usuario["_id"]},
            {"$set": {
                "senha_hash": senha_hash,
                "atualizado_em": datetime.datetime.now(),
            }},
        )

        self.registrar_auditoria(
            operador,
            "Senha alterada",
            f"Senha de '{usuario.get('nome', '')}' foi alterada.",
        )

    # ==========================================================
    # AUDITORIA
    # ==========================================================

    def registrar_auditoria(
        self,
        usuario,
        acao,
        detalhes="",
        modulo="Administração",
    ):
        self.db.auditoria.insert_one({
            "usuario_id": (
                str(usuario.get("_id"))
                if usuario
                else None
            ),
            "usuario_nome": (
                usuario.get("nome")
                if usuario
                else "Sistema"
            ),
            "perfil": (
                usuario.get("perfil")
                if usuario
                else ""
            ),
            "modulo": modulo,
            "acao": acao,
            "detalhes": detalhes,
            "data": datetime.datetime.now(),
        })

    def listar_auditoria(self, termo="", limite=1000):
        filtro = {}
        termo = (termo or "").strip()

        if termo:
            filtro = {
                "$or": [
                    {"usuario_nome": {
                        "$regex": termo,
                        "$options": "i",
                    }},
                    {"modulo": {
                        "$regex": termo,
                        "$options": "i",
                    }},
                    {"acao": {
                        "$regex": termo,
                        "$options": "i",
                    }},
                    {"detalhes": {
                        "$regex": termo,
                        "$options": "i",
                    }},
                ]
            }

        return list(
            self.db.auditoria
            .find(filtro)
            .sort("data", -1)
            .limit(limite)
        )

    # ==========================================================
    # BACKUP E RESTAURAÇÃO
    # ==========================================================

    def criar_backup(self, pasta_destino, usuario=None):
        pasta = Path(pasta_destino)
        pasta.mkdir(parents=True, exist_ok=True)

        agora = datetime.datetime.now()
        nome_arquivo = (
            f"backup_seu_caldo_24_"
            f"{agora.strftime('%Y%m%d_%H%M%S')}.json"
        )
        caminho = pasta / nome_arquivo

        conteudo = {
            "sistema": "Seu Caldo 24",
            "empresa": "M.A Sistemas",
            "criado_em": agora,
            "banco": self.db.db.name,
            "colecoes": {},
        }

        for nome in COLECOES_BACKUP:
            conteudo["colecoes"][nome] = list(
                self.db.db[nome].find()
            )

        caminho.write_text(
            json_util.dumps(
                conteudo,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        self.registrar_auditoria(
            usuario,
            "Backup criado",
            f"Arquivo: {caminho}",
        )

        return str(caminho)

    def restaurar_backup(self, caminho_arquivo, usuario=None):
        caminho = Path(caminho_arquivo)

        if not caminho.exists():
            raise ValueError("Arquivo de backup não encontrado.")

        try:
            conteudo = json_util.loads(
                caminho.read_text(encoding="utf-8")
            )
        except Exception as exc:
            raise ValueError(
                f"Não foi possível ler o backup: {exc}"
            ) from exc

        colecoes = conteudo.get("colecoes")

        if not isinstance(colecoes, dict):
            raise ValueError("Formato de backup inválido.")

        for nome, documentos in colecoes.items():
            if nome not in COLECOES_BACKUP:
                continue

            colecao = self.db.db[nome]
            colecao.delete_many({})

            if documentos:
                colecao.insert_many(documentos)

        self.registrar_auditoria(
            usuario,
            "Backup restaurado",
            f"Arquivo restaurado: {caminho}",
        )

        return True