# -*- coding: utf-8 -*-
import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                                QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
                                QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox,
                                QSpinBox, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from lxml import etree

from db.database import get_db
from config import SETORES_ESTOQUE
from utils.helpers import fmt_moeda, alerta, info, confirmar, exportar_para_excel


# ======================================================================
# DIALOG: Cadastro / edição de produto
# ======================================================================
class ProdutoDialog(QDialog):
    def __init__(self, parent=None, produto=None):
        super().__init__(parent)
        self.db = get_db()
        self.produto = produto
        self.setWindowTitle("Editar Produto" if produto else "Novo Produto")
        self.setMinimumWidth(420)

        layout = QFormLayout(self)

        self.nome = QLineEdit(produto["nome"] if produto else "")
        self.codigo_barras = QLineEdit(produto.get("codigo_barras", "") if produto else "")

        self.categoria = QComboBox()
        cats = [c["nome"] for c in self.db.categorias.find()]
        self.categoria.addItems(cats)
        if produto and produto.get("categoria") in cats:
            self.categoria.setCurrentText(produto["categoria"])

        self.setor = QComboBox()
        self.setor.addItems(SETORES_ESTOQUE)
        if produto:
            self.setor.setCurrentText(produto.get("setor", SETORES_ESTOQUE[0]))

        self.unidade = QComboBox()
        self.unidade.addItems(["UN", "KG", "L", "CX", "PCT", "FD"])
        if produto:
            self.unidade.setCurrentText(produto.get("unidade", "UN"))

        self.custo = QDoubleSpinBox()
        self.custo.setPrefix("R$ ")
        self.custo.setMaximum(999999)
        self.custo.setDecimals(2)
        self.custo.setValue(produto.get("custo", 0) if produto else 0)
        self.custo.valueChanged.connect(self._recalcular_preco)

        self.margem = QDoubleSpinBox()
        self.margem.setSuffix(" %")
        self.margem.setMaximum(1000)
        self.margem.setValue(produto.get("margem", 100) if produto else 100)
        self.margem.valueChanged.connect(self._recalcular_preco)

        self.preco_venda = QDoubleSpinBox()
        self.preco_venda.setPrefix("R$ ")
        self.preco_venda.setMaximum(999999)
        self.preco_venda.setDecimals(2)
        self.preco_venda.setReadOnly(True)
        self.preco_venda.setButtonSymbols(QDoubleSpinBox.NoButtons)

        self.estoque_atual = QDoubleSpinBox()
        self.estoque_atual.setMaximum(999999)
        self.estoque_atual.setValue(produto.get("estoque_atual", 0) if produto else 0)

        self.estoque_minimo = QDoubleSpinBox()
        self.estoque_minimo.setMaximum(999999)
        self.estoque_minimo.setValue(produto.get("estoque_minimo", 5) if produto else 5)

        self.fornecedor = QComboBox()
        self.fornecedor.addItem("(Nenhum)", None)
        for f in self.db.fornecedores.find():
            self.fornecedor.addItem(f["nome"], str(f["_id"]))
        if produto and produto.get("fornecedor_id"):
            idx = self.fornecedor.findData(produto["fornecedor_id"])
            if idx >= 0:
                self.fornecedor.setCurrentIndex(idx)

        layout.addRow("Nome do produto:", self.nome)
        layout.addRow("Código de barras:", self.codigo_barras)
        layout.addRow("Categoria:", self.categoria)
        layout.addRow("Setor:", self.setor)
        layout.addRow("Unidade:", self.unidade)
        layout.addRow("Custo unitário:", self.custo)
        layout.addRow("Margem de lucro:", self.margem)
        layout.addRow("Preço de venda (calc.):", self.preco_venda)
        layout.addRow("Estoque atual:", self.estoque_atual)
        layout.addRow("Estoque mínimo:", self.estoque_minimo)
        layout.addRow("Fornecedor:", self.fornecedor)

        botoes = QHBoxLayout()
        btn_salvar = QPushButton("Salvar")
        btn_salvar.clicked.connect(self._salvar)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_salvar)
        layout.addRow(botoes)

        self._recalcular_preco()

    def _recalcular_preco(self):
        preco = self.custo.value() * (1 + self.margem.value() / 100)
        self.preco_venda.setValue(preco)

    def _salvar(self):
        if not self.nome.text().strip():
            alerta(self, "Atenção", "Informe o nome do produto.")
            return

        dados = {
            "nome": self.nome.text().strip(),
            "codigo_barras": self.codigo_barras.text().strip(),
            "categoria": self.categoria.currentText(),
            "setor": self.setor.currentText(),
            "unidade": self.unidade.currentText(),
            "custo": self.custo.value(),
            "margem": self.margem.value(),
            "preco_venda": self.preco_venda.value(),
            "estoque_atual": self.estoque_atual.value(),
            "estoque_minimo": self.estoque_minimo.value(),
            "fornecedor_id": self.fornecedor.currentData(),
            "atualizado_em": datetime.datetime.now(),
        }

        if self.produto:
            self.db.produtos.update_one({"_id": self.produto["_id"]}, {"$set": dados})
        else:
            dados["criado_em"] = datetime.datetime.now()
            self.db.produtos.insert_one(dados)

        self.accept()

# ======================================================================
# DIALOG: Cadastro / edição de categoria
# ======================================================================
class CategoriaDialog(QDialog):
    def __init__(self, parent=None, categoria=None):
        super().__init__(parent)

        self.db = get_db()
        self.categoria = categoria

        self.setWindowTitle(
            "Editar Categoria" if categoria else "Nova Categoria"
        )
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.nome = QLineEdit(
            categoria.get("nome", "") if categoria else ""
        )
        self.nome.setPlaceholderText("Ex.: Bebidas, Caldos, Insumos")

        self.setor_padrao = QComboBox()
        self.setor_padrao.addItems(SETORES_ESTOQUE)

        if categoria:
            setor_atual = categoria.get(
                "setor_padrao",
                SETORES_ESTOQUE[0]
            )
            self.setor_padrao.setCurrentText(setor_atual)

        self.descricao = QLineEdit(
            categoria.get("descricao", "") if categoria else ""
        )
        self.descricao.setPlaceholderText(
            "Descrição opcional da categoria"
        )

        layout.addRow("Nome da categoria:", self.nome)
        layout.addRow("Setor padrão:", self.setor_padrao)
        layout.addRow("Descrição:", self.descricao)

        botoes = QHBoxLayout()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.clicked.connect(self.reject)

        btn_salvar = QPushButton("Salvar")
        btn_salvar.clicked.connect(self._salvar)

        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_salvar)

        layout.addRow(botoes)

    def _salvar(self):
        nome = self.nome.text().strip()

        if not nome:
            alerta(
                self,
                "Atenção",
                "Informe o nome da categoria."
            )
            return

        filtro_duplicado = {
            "nome": {
                "$regex": f"^{nome}$",
                "$options": "i"
            }
        }

        categoria_existente = self.db.categorias.find_one(
            filtro_duplicado
        )

        if categoria_existente:
            categoria_em_edicao = (
                self.categoria
                and categoria_existente["_id"]
                == self.categoria["_id"]
            )

            if not categoria_em_edicao:
                alerta(
                    self,
                    "Categoria duplicada",
                    "Já existe uma categoria com esse nome."
                )
                return

        dados = {
            "nome": nome,
            "setor_padrao": self.setor_padrao.currentText(),
            "descricao": self.descricao.text().strip(),
            "atualizado_em": datetime.datetime.now(),
        }

        if self.categoria:
            nome_anterior = self.categoria.get("nome", "")

            self.db.categorias.update_one(
                {"_id": self.categoria["_id"]},
                {"$set": dados}
            )

            if nome_anterior != nome:
                self.db.produtos.update_many(
                    {"categoria": nome_anterior},
                    {"$set": {"categoria": nome}}
                )
        else:
            dados["criado_em"] = datetime.datetime.now()
            self.db.categorias.insert_one(dados)

        self.accept()


# ======================================================================
# ABA: Categorias
# ======================================================================
class AbaCategorias(QWidget):
    def __init__(self):
        super().__init__()

        self.db = get_db()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        self.busca = QLineEdit()
        self.busca.setPlaceholderText(
            "Buscar categoria pelo nome..."
        )
        self.busca.textChanged.connect(self.atualizar)

        btn_novo = QPushButton("+ Nova Categoria")
        btn_novo.clicked.connect(self._novo)

        btn_editar = QPushButton("Editar")
        btn_editar.setObjectName("btnSecundario")
        btn_editar.clicked.connect(self._editar)

        btn_excluir = QPushButton("Excluir")
        btn_excluir.setObjectName("btnPerigo")
        btn_excluir.clicked.connect(self._excluir)

        topo.addWidget(self.busca, 1)
        topo.addWidget(btn_novo)
        topo.addWidget(btn_editar)
        topo.addWidget(btn_excluir)

        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 4)
        self.tabela.setHorizontalHeaderLabels([
            "Categoria",
            "Setor padrão",
            "Descrição",
            "Produtos vinculados",
        ])

        self.tabela.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.tabela.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self.tabela.setSelectionBehavior(
            QTableWidget.SelectRows
        )
        self.tabela.setSelectionMode(
            QTableWidget.SingleSelection
        )
        self.tabela.doubleClicked.connect(self._editar)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        termo = self.busca.text().strip()

        filtro = {}

        if termo:
            filtro = {
                "nome": {
                    "$regex": termo,
                    "$options": "i"
                }
            }

        categorias = list(
            self.db.categorias.find(filtro).sort("nome", 1)
        )

        self.tabela.setRowCount(0)

        for categoria in categorias:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            nome = categoria.get("nome", "")

            quantidade_produtos = (
                self.db.produtos.count_documents({
                    "categoria": nome
                })
            )

            item_nome = QTableWidgetItem(nome)
            item_nome.setData(
                Qt.UserRole,
                str(categoria["_id"])
            )

            self.tabela.setItem(row, 0, item_nome)
            self.tabela.setItem(
                row,
                1,
                QTableWidgetItem(
                    categoria.get("setor_padrao", "")
                )
            )
            self.tabela.setItem(
                row,
                2,
                QTableWidgetItem(
                    categoria.get("descricao", "")
                )
            )
            self.tabela.setItem(
                row,
                3,
                QTableWidgetItem(str(quantidade_produtos))
            )

    def _categoria_selecionada(self):
        row = self.tabela.currentRow()

        if row < 0:
            return None

        item = self.tabela.item(row, 0)

        if not item:
            return None

        categoria_id = item.data(Qt.UserRole)

        if not categoria_id:
            return None

        from bson import ObjectId

        return self.db.categorias.find_one({
            "_id": ObjectId(categoria_id)
        })

    def _novo(self):
        dialog = CategoriaDialog(self)

        if dialog.exec():
            self.atualizar()

    def _editar(self):
        categoria = self._categoria_selecionada()

        if not categoria:
            alerta(
                self,
                "Atenção",
                "Selecione uma categoria na tabela."
            )
            return

        dialog = CategoriaDialog(
            self,
            categoria
        )

        if dialog.exec():
            self.atualizar()

    def _excluir(self):
        categoria = self._categoria_selecionada()

        if not categoria:
            alerta(
                self,
                "Atenção",
                "Selecione uma categoria na tabela."
            )
            return

        nome = categoria.get("nome", "")

        quantidade_produtos = (
            self.db.produtos.count_documents({
                "categoria": nome
            })
        )

        if quantidade_produtos > 0:
            alerta(
                self,
                "Categoria em uso",
                (
                    f"A categoria '{nome}' possui "
                    f"{quantidade_produtos} produto(s) vinculado(s).\n\n"
                    "Altere a categoria dos produtos antes de excluí-la."
                )
            )
            return

        resposta = confirmar(
            self,
            "Confirmar exclusão",
            f"Deseja excluir a categoria '{nome}'?"
        )

        if resposta:
            self.db.categorias.delete_one({
                "_id": categoria["_id"]
            })

            self.atualizar()

# ======================================================================
# ABA: Produtos
# ======================================================================
class AbaProdutos(QWidget):
    def __init__(self):
        super().__init__()
        self.db = get_db()
        layout = QVBoxLayout(self)

        topo = QHBoxLayout()
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar produto por nome ou código de barras...")
        self.busca.textChanged.connect(self.atualizar)
        btn_novo = QPushButton("+ Novo Produto")
        btn_novo.clicked.connect(self._novo)
        btn_editar = QPushButton("Editar")
        btn_editar.setObjectName("btnSecundario")
        btn_editar.clicked.connect(self._editar)
        btn_excluir = QPushButton("Excluir")
        btn_excluir.setObjectName("btnPerigo")
        btn_excluir.clicked.connect(self._excluir)

        topo.addWidget(self.busca)
        topo.addWidget(btn_novo)
        topo.addWidget(btn_editar)
        topo.addWidget(btn_excluir)
        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels(
            ["Nome", "Categoria", "Setor", "Unid.", "Custo", "Preço Venda", "Estoque", "Mínimo"])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        termo = self.busca.text().strip()
        filtro = {}
        if termo:
            filtro = {"$or": [
                {"nome": {"$regex": termo, "$options": "i"}},
                {"codigo_barras": {"$regex": termo, "$options": "i"}},
            ]}
        produtos = list(self.db.produtos.find(filtro).sort("nome", 1))
        self.tabela.setRowCount(0)
        for p in produtos:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            self.tabela.setItem(row, 0, QTableWidgetItem(p.get("nome", "")))
            self.tabela.setItem(row, 1, QTableWidgetItem(p.get("categoria", "")))
            self.tabela.setItem(row, 2, QTableWidgetItem(p.get("setor", "")))
            self.tabela.setItem(row, 3, QTableWidgetItem(p.get("unidade", "")))
            self.tabela.setItem(row, 4, QTableWidgetItem(fmt_moeda(p.get("custo", 0))))
            self.tabela.setItem(row, 5, QTableWidgetItem(fmt_moeda(p.get("preco_venda", 0))))
            item_estoque = QTableWidgetItem(str(p.get("estoque_atual", 0)))
            if p.get("estoque_atual", 0) <= p.get("estoque_minimo", 0):
                item_estoque.setForeground(Qt.red)
            self.tabela.setItem(row, 6, item_estoque)
            self.tabela.setItem(row, 7, QTableWidgetItem(str(p.get("estoque_minimo", 0))))
            self.tabela.item(row, 0).setData(Qt.UserRole, str(p["_id"]))

    def _produto_selecionado(self):
        row = self.tabela.currentRow()
        if row < 0:
            return None
        pid = self.tabela.item(row, 0).data(Qt.UserRole)
        from bson import ObjectId
        return self.db.produtos.find_one({"_id": ObjectId(pid)})

    def _novo(self):
        dlg = ProdutoDialog(self)
        if dlg.exec():
            self.atualizar()

    def _editar(self):
        produto = self._produto_selecionado()
        if not produto:
            alerta(self, "Atenção", "Selecione um produto na tabela.")
            return
        dlg = ProdutoDialog(self, produto)
        if dlg.exec():
            self.atualizar()

    def _excluir(self):
        produto = self._produto_selecionado()
        if not produto:
            alerta(self, "Atenção", "Selecione um produto na tabela.")
            return
        if confirmar(self, "Confirmar exclusão", f"Excluir o produto '{produto['nome']}'?"):
            self.db.produtos.delete_one({"_id": produto["_id"]})
            self.atualizar()


# ======================================================================
# ABA: Movimentação de estoque (entrada/saída manual e transferência)
# ======================================================================
class AbaMovimentacao(QWidget):
    def __init__(self):
        super().__init__()
        self.db = get_db()
        layout = QVBoxLayout(self)

        form = QHBoxLayout()
        self.produto_combo = QComboBox()
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["Entrada", "Saída", "Transferência entre setores", "Perda/Quebra"])
        self.tipo_combo.currentTextChanged.connect(self._toggle_setor_destino)

        self.setor_destino = QComboBox()
        self.setor_destino.addItems(SETORES_ESTOQUE)
        self.setor_destino.setEnabled(False)

        self.quantidade = QDoubleSpinBox()
        self.quantidade.setMaximum(999999)
        self.quantidade.setValue(1)

        self.motivo = QLineEdit()
        self.motivo.setPlaceholderText("Motivo / observação")

        btn_registrar = QPushButton("Registrar movimentação")
        btn_registrar.clicked.connect(self._registrar)

        form.addWidget(QLabel("Produto:"))
        form.addWidget(self.produto_combo, 2)
        form.addWidget(QLabel("Tipo:"))
        form.addWidget(self.tipo_combo)
        form.addWidget(QLabel("Setor destino:"))
        form.addWidget(self.setor_destino)
        form.addWidget(QLabel("Qtd:"))
        form.addWidget(self.quantidade)
        form.addWidget(self.motivo, 2)
        form.addWidget(btn_registrar)
        layout.addLayout(form)

        # Importação de XML de Nota Fiscal
        linha_xml = QHBoxLayout()
        lbl_xml = QLabel("Entrada de mercadoria por XML de Nota Fiscal (NF-e):")
        btn_xml = QPushButton("📄 Importar XML")
        btn_xml.setObjectName("btnSecundario")
        btn_xml.clicked.connect(self._importar_xml)
        linha_xml.addWidget(lbl_xml)
        linha_xml.addWidget(btn_xml)
        linha_xml.addStretch()
        layout.addLayout(linha_xml)

        self.tabela = QTableWidget(0, 6)
        self.tabela.setHorizontalHeaderLabels(["Data", "Produto", "Tipo", "Setor", "Quantidade", "Motivo"])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)

        self._carregar_produtos()
        self.atualizar()

    def _toggle_setor_destino(self, texto):
        self.setor_destino.setEnabled(texto == "Transferência entre setores")

    def _carregar_produtos(self):
        self.produto_combo.clear()
        for p in self.db.produtos.find().sort("nome", 1):
            self.produto_combo.addItem(f"{p['nome']} ({p.get('setor','')})", str(p["_id"]))

    def _registrar(self):
        from bson import ObjectId
        pid = self.produto_combo.currentData()
        if not pid:
            alerta(self, "Atenção", "Cadastre ao menos um produto antes de movimentar estoque.")
            return
        produto = self.db.produtos.find_one({"_id": ObjectId(pid)})
        tipo = self.tipo_combo.currentText()
        qtd = self.quantidade.value()

        novo_estoque = produto.get("estoque_atual", 0)
        setor_final = produto.get("setor")

        if tipo == "Entrada":
            novo_estoque += qtd
        elif tipo in ("Saída", "Perda/Quebra"):
            if qtd > novo_estoque:
                alerta(self, "Atenção", "Quantidade maior que o estoque disponível.")
                return
            novo_estoque -= qtd
        elif tipo == "Transferência entre setores":
            setor_final = self.setor_destino.currentText()

        self.db.produtos.update_one({"_id": produto["_id"]},
                                     {"$set": {"estoque_atual": novo_estoque, "setor": setor_final}})

        self.db.movimentacoes_estoque.insert_one({
            "produto_id": str(produto["_id"]),
            "produto_nome": produto["nome"],
            "tipo": tipo,
            "setor": setor_final,
            "quantidade": qtd,
            "motivo": self.motivo.text().strip(),
            "data": datetime.datetime.now(),
        })
        self.motivo.clear()
        self._carregar_produtos()
        self.atualizar()
        info(self, "Sucesso", "Movimentação registrada com sucesso.")

    def _importar_xml(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Selecionar XML da NF-e", "", "XML (*.xml)")
        if not caminho:
            return
        try:
            tree = etree.parse(caminho)
            ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
            itens = tree.findall(".//nfe:det", ns)
            if not itens:
                # tenta sem namespace (alguns XMLs simplificados)
                itens = tree.findall(".//det")
                ns = {}

            importados = 0
            for det in itens:
                prod = det.find("nfe:prod", ns) if ns else det.find("prod")
                if prod is None:
                    continue
                nome = prod.findtext("nfe:xProd" if ns else "xProd", default="Produto sem nome", namespaces=ns)
                qtd = float(prod.findtext("nfe:qCom" if ns else "qCom", default="0", namespaces=ns) or 0)
                valor_unit = float(prod.findtext("nfe:vUnCom" if ns else "vUnCom", default="0", namespaces=ns) or 0)
                codigo = prod.findtext("nfe:cEAN" if ns else "cEAN", default="", namespaces=ns) or ""

                existente = self.db.produtos.find_one({"nome": nome})
                if existente:
                    self.db.produtos.update_one(
                        {"_id": existente["_id"]},
                        {"$inc": {"estoque_atual": qtd}, "$set": {"custo": valor_unit}}
                    )
                    produto_id = existente["_id"]
                else:
                    novo = {
                        "nome": nome, "codigo_barras": codigo, "categoria": "Insumos",
                        "setor": "Depósito", "unidade": "UN", "custo": valor_unit,
                        "margem": 100, "preco_venda": valor_unit * 2,
                        "estoque_atual": qtd, "estoque_minimo": 5, "fornecedor_id": None,
                        "criado_em": datetime.datetime.now(),
                    }
                    produto_id = self.db.produtos.insert_one(novo).inserted_id

                self.db.movimentacoes_estoque.insert_one({
                    "produto_id": str(produto_id), "produto_nome": nome, "tipo": "Entrada (XML NF-e)",
                    "setor": "Depósito", "quantidade": qtd, "motivo": f"Importação XML: {caminho.split('/')[-1]}",
                    "data": datetime.datetime.now(),
                })
                importados += 1

            self._carregar_produtos()
            self.atualizar()
            info(self, "Importação concluída", f"{importados} item(ns) importado(s) da nota fiscal com sucesso.")
        except Exception as e:
            alerta(self, "Erro ao importar XML", f"Não foi possível ler o arquivo XML:\n{e}")

    def atualizar(self):
        movs = list(self.db.movimentacoes_estoque.find().sort("data", -1).limit(200))
        self.tabela.setRowCount(0)
        for m in movs:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            self.tabela.setItem(row, 0, QTableWidgetItem(m["data"].strftime("%d/%m/%Y %H:%M")))
            self.tabela.setItem(row, 1, QTableWidgetItem(m.get("produto_nome", "")))
            self.tabela.setItem(row, 2, QTableWidgetItem(m.get("tipo", "")))
            self.tabela.setItem(row, 3, QTableWidgetItem(m.get("setor", "")))
            self.tabela.setItem(row, 4, QTableWidgetItem(str(m.get("quantidade", 0))))
            self.tabela.setItem(row, 5, QTableWidgetItem(m.get("motivo", "")))


# ======================================================================
# DIALOG: Fornecedor
# ======================================================================
class FornecedorDialog(QDialog):
    def __init__(self, parent=None, fornecedor=None):
        super().__init__(parent)
        self.db = get_db()
        self.fornecedor = fornecedor
        self.setWindowTitle("Editar Fornecedor" if fornecedor else "Novo Fornecedor")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)

        self.nome = QLineEdit(fornecedor["nome"] if fornecedor else "")
        self.cnpj = QLineEdit(fornecedor.get("cnpj", "") if fornecedor else "")
        self.telefone = QLineEdit(fornecedor.get("telefone", "") if fornecedor else "")
        self.email = QLineEdit(fornecedor.get("email", "") if fornecedor else "")
        self.contato = QLineEdit(fornecedor.get("contato", "") if fornecedor else "")

        layout.addRow("Nome / Razão Social:", self.nome)
        layout.addRow("CNPJ:", self.cnpj)
        layout.addRow("Telefone:", self.telefone)
        layout.addRow("E-mail:", self.email)
        layout.addRow("Pessoa de contato:", self.contato)

        botoes = QHBoxLayout()
        btn_salvar = QPushButton("Salvar")
        btn_salvar.clicked.connect(self._salvar)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_salvar)
        layout.addRow(botoes)

    def _salvar(self):
        if not self.nome.text().strip():
            alerta(self, "Atenção", "Informe o nome do fornecedor.")
            return
        dados = {
            "nome": self.nome.text().strip(),
            "cnpj": self.cnpj.text().strip(),
            "telefone": self.telefone.text().strip(),
            "email": self.email.text().strip(),
            "contato": self.contato.text().strip(),
        }
        if self.fornecedor:
            self.db.fornecedores.update_one({"_id": self.fornecedor["_id"]}, {"$set": dados})
        else:
            self.db.fornecedores.insert_one(dados)
        self.accept()


class AbaFornecedores(QWidget):
    def __init__(self):
        super().__init__()
        self.db = get_db()
        layout = QVBoxLayout(self)

        topo = QHBoxLayout()
        btn_novo = QPushButton("+ Novo Fornecedor")
        btn_novo.clicked.connect(self._novo)
        btn_editar = QPushButton("Editar")
        btn_editar.setObjectName("btnSecundario")
        btn_editar.clicked.connect(self._editar)
        btn_excluir = QPushButton("Excluir")
        btn_excluir.setObjectName("btnPerigo")
        btn_excluir.clicked.connect(self._excluir)
        topo.addWidget(btn_novo)
        topo.addWidget(btn_editar)
        topo.addWidget(btn_excluir)
        topo.addStretch()
        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 5)
        self.tabela.setHorizontalHeaderLabels(["Nome", "CNPJ", "Telefone", "E-mail", "Contato"])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)
        self.atualizar()

    def atualizar(self):
        fornecedores = list(self.db.fornecedores.find().sort("nome", 1))
        self.tabela.setRowCount(0)
        for f in fornecedores:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            self.tabela.setItem(row, 0, QTableWidgetItem(f.get("nome", "")))
            self.tabela.setItem(row, 1, QTableWidgetItem(f.get("cnpj", "")))
            self.tabela.setItem(row, 2, QTableWidgetItem(f.get("telefone", "")))
            self.tabela.setItem(row, 3, QTableWidgetItem(f.get("email", "")))
            self.tabela.setItem(row, 4, QTableWidgetItem(f.get("contato", "")))
            self.tabela.item(row, 0).setData(Qt.UserRole, str(f["_id"]))

    def _selecionado(self):
        row = self.tabela.currentRow()
        if row < 0:
            return None
        from bson import ObjectId
        fid = self.tabela.item(row, 0).data(Qt.UserRole)
        return self.db.fornecedores.find_one({"_id": ObjectId(fid)})

    def _novo(self):
        if FornecedorDialog(self).exec():
            self.atualizar()

    def _editar(self):
        f = self._selecionado()
        if not f:
            alerta(self, "Atenção", "Selecione um fornecedor.")
            return
        if FornecedorDialog(self, f).exec():
            self.atualizar()

    def _excluir(self):
        f = self._selecionado()
        if not f:
            alerta(self, "Atenção", "Selecione um fornecedor.")
            return
        if confirmar(self, "Confirmar", f"Excluir fornecedor '{f['nome']}'?"):
            self.db.fornecedores.delete_one({"_id": f["_id"]})
            self.atualizar()


# ======================================================================
# ABA: Curva ABC e Rentabilidade
# ======================================================================
class AbaCurvaABC(QWidget):
    def __init__(self):
        super().__init__()
        self.db = get_db()
        layout = QVBoxLayout(self)

        topo = QHBoxLayout()
        titulo = QLabel("Curva ABC e Rentabilidade por Produto (baseado no histórico de vendas)")
        titulo.setStyleSheet("font-weight:bold; font-size:14px;")
        btn_atualizar = QPushButton("🔄 Recalcular")
        btn_atualizar.clicked.connect(self.atualizar)
        btn_exportar = QPushButton("Exportar Excel")
        btn_exportar.setObjectName("btnSecundario")
        btn_exportar.clicked.connect(self._exportar)
        topo.addWidget(titulo)
        topo.addStretch()
        topo.addWidget(btn_atualizar)
        topo.addWidget(btn_exportar)
        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 7)
        self.tabela.setHorizontalHeaderLabels(
            ["Produto", "Qtd. Vendida", "Faturamento", "% do Total", "% Acumulado", "Classe", "Margem Un."])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)
        self._dados_atuais = []
        self.atualizar()

    def atualizar(self):
        pipeline = [
            {"$unwind": "$itens"},
            {"$group": {
                "_id": "$itens.produto_nome",
                "qtd": {"$sum": "$itens.quantidade"},
                "total": {"$sum": {"$multiply": ["$itens.quantidade", "$itens.preco_unit"]}},
            }},
            {"$sort": {"total": -1}},
        ]
        resultado = list(self.db.vendas.aggregate(pipeline))
        faturamento_total = sum(r["total"] for r in resultado) or 1

        self.tabela.setRowCount(0)
        acumulado = 0
        self._dados_atuais = []
        for r in resultado:
            pct = (r["total"] / faturamento_total) * 100
            acumulado += pct
            classe = "A" if acumulado <= 80 else ("B" if acumulado <= 95 else "C")

            produto = self.db.produtos.find_one({"nome": r["_id"]})
            margem_un = 0
            if produto:
                margem_un = produto.get("preco_venda", 0) - produto.get("custo", 0)

            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            self.tabela.setItem(row, 0, QTableWidgetItem(r["_id"]))
            self.tabela.setItem(row, 1, QTableWidgetItem(str(r["qtd"])))
            self.tabela.setItem(row, 2, QTableWidgetItem(fmt_moeda(r["total"])))
            self.tabela.setItem(row, 3, QTableWidgetItem(f"{pct:.1f}%"))
            self.tabela.setItem(row, 4, QTableWidgetItem(f"{acumulado:.1f}%"))
            item_classe = QTableWidgetItem(classe)
            cor = {"A": Qt.green, "B": Qt.yellow, "C": Qt.red}[classe]
            item_classe.setForeground(cor)
            self.tabela.setItem(row, 5, item_classe)
            self.tabela.setItem(row, 6, QTableWidgetItem(fmt_moeda(margem_un)))

            self._dados_atuais.append([r["_id"], r["qtd"], r["total"], f"{pct:.1f}%", f"{acumulado:.1f}%", classe, margem_un])

        if not resultado:
            self.tabela.setRowCount(1)
            self.tabela.setItem(0, 0, QTableWidgetItem("Nenhuma venda registrada ainda."))

    def _exportar(self):
        if not self._dados_atuais:
            alerta(self, "Atenção", "Não há dados para exportar.")
            return
        cabecalhos = ["Produto", "Qtd. Vendida", "Faturamento", "% do Total", "% Acumulado", "Classe", "Margem Unit."]
        exportar_para_excel(self, cabecalhos, self._dados_atuais, "curva_abc_seu_caldo_24.xlsx", "Curva ABC")


# ======================================================================
# ABA: Promoções
# ======================================================================
class PromocaoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self.setWindowTitle("Nova Promoção")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)

        self.produto = QComboBox()
        for p in self.db.produtos.find().sort("nome", 1):
            self.produto.addItem(p["nome"], str(p["_id"]))

        self.desconto = QDoubleSpinBox()
        self.desconto.setSuffix(" %")
        self.desconto.setMaximum(100)

        self.descricao = QLineEdit()
        self.descricao.setPlaceholderText("Ex: Happy Hour Caldos 20%")

        layout.addRow("Produto:", self.produto)
        layout.addRow("Desconto:", self.desconto)
        layout.addRow("Descrição:", self.descricao)

        botoes = QHBoxLayout()
        btn_salvar = QPushButton("Salvar")
        btn_salvar.clicked.connect(self._salvar)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_salvar)
        layout.addRow(botoes)

    def _salvar(self):
        from bson import ObjectId
        produto = self.db.produtos.find_one({"_id": ObjectId(self.produto.currentData())})
        self.db.promocoes.insert_one({
            "produto_id": self.produto.currentData(),
            "produto_nome": produto["nome"],
            "desconto": self.desconto.value(),
            "descricao": self.descricao.text().strip(),
            "ativa": True,
            "criado_em": datetime.datetime.now(),
        })
        self.accept()


class AbaPromocoes(QWidget):
    def __init__(self):
        super().__init__()
        self.db = get_db()
        layout = QVBoxLayout(self)

        topo = QHBoxLayout()
        btn_novo = QPushButton("+ Nova Promoção")
        btn_novo.clicked.connect(self._novo)
        btn_desativar = QPushButton("Ativar/Desativar")
        btn_desativar.setObjectName("btnSecundario")
        btn_desativar.clicked.connect(self._toggle)
        topo.addWidget(btn_novo)
        topo.addWidget(btn_desativar)
        topo.addStretch()
        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 4)
        self.tabela.setHorizontalHeaderLabels(["Produto", "Desconto", "Descrição", "Status"])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)
        self.atualizar()

    def atualizar(self):
        promos = list(self.db.promocoes.find().sort("criado_em", -1))
        self.tabela.setRowCount(0)
        for p in promos:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            self.tabela.setItem(row, 0, QTableWidgetItem(p.get("produto_nome", "")))
            self.tabela.setItem(row, 1, QTableWidgetItem(f"{p.get('desconto',0)}%"))
            self.tabela.setItem(row, 2, QTableWidgetItem(p.get("descricao", "")))
            self.tabela.setItem(row, 3, QTableWidgetItem("Ativa" if p.get("ativa") else "Inativa"))
            self.tabela.item(row, 0).setData(Qt.UserRole, str(p["_id"]))

    def _novo(self):
        if PromocaoDialog(self).exec():
            self.atualizar()

    def _toggle(self):
        row = self.tabela.currentRow()
        if row < 0:
            alerta(self, "Atenção", "Selecione uma promoção.")
            return
        from bson import ObjectId
        pid = self.tabela.item(row, 0).data(Qt.UserRole)
        promo = self.db.promocoes.find_one({"_id": ObjectId(pid)})
        self.db.promocoes.update_one({"_id": promo["_id"]}, {"$set": {"ativa": not promo.get("ativa", True)}})
        self.atualizar()


# ======================================================================
# WIDGET PRINCIPAL: Estoque (agrega as abas)
# ======================================================================
class EstoqueWidget(QWidget):
    def __init__(self, usuario):
        super().__init__()
        self.usuario = usuario

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        titulo = QLabel("Gestão de Estoque")
        titulo.setObjectName("tituloPagina")
        layout.addWidget(titulo)

        self.tabs = QTabWidget()

        self.aba_produtos = AbaProdutos()
        self.aba_categorias = AbaCategorias()
        self.aba_movimentacao = AbaMovimentacao()
        self.aba_fornecedores = AbaFornecedores()
        self.aba_abc = AbaCurvaABC()
        self.aba_promocoes = AbaPromocoes()

        self.tabs.addTab(self.aba_produtos, "Produtos")
        self.tabs.addTab(self.aba_categorias, "Categorias")
        self.tabs.addTab(
            self.aba_movimentacao,
            "Movimentação / Entrada XML"
        )
        self.tabs.addTab(self.aba_fornecedores, "Fornecedores")
        self.tabs.addTab(
            self.aba_abc,
            "Curva ABC / Rentabilidade"
        )
        self.tabs.addTab(self.aba_promocoes, "Promoções")

        layout.addWidget(self.tabs)

    def atualizar(self):
        self.aba_produtos.atualizar()
        self.aba_categorias.atualizar()
        self.aba_movimentacao.atualizar()
        self.aba_movimentacao._carregar_produtos()
        self.aba_fornecedores.atualizar()
        self.aba_abc.atualizar()
        self.aba_promocoes.atualizar()