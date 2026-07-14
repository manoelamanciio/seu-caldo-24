# -*- coding: utf-8 -*-
"""
Configurações gerais do sistema Seu Caldo 24
Desenvolvido por M.A Sistemas
"""

# --------- Conexão com o MongoDB ---------
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB_NAME = "seu_caldo_24_db"

# --------- Dados da empresa (usados em relatórios / cupons) ---------
EMPRESA = {
    "razao_social": "Seu Caldo 24",
    "nome_fantasia": "Seu Caldo 24",
    "cnpj": "00.000.000/0001-00",
    "endereco": "Rua Exemplo, 123 - Centro",
    "telefone": "(00) 0000-0000",
    "desenvolvido_por": "M.A Sistemas",
}

# --------- Parâmetros gerais ---------
MOEDA_SIMBOLO = "R$"
SETORES_ESTOQUE = ["Loja", "Cozinha", "Depósito"]
FORMAS_PAGAMENTO = ["Dinheiro", "Cartão Débito", "Cartão Crédito", "PIX", "Fiado (Correntista)"]
NIVEL_ESTOQUE_CRITICO_PADRAO = 5

# --------- Perfis de usuário ---------
PERFIS = ["Administrador", "Gerente", "Caixa/Atendente", "Cozinha", "Financeiro"]