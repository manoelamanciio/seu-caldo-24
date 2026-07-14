# -*- coding: utf-8 -*-
"""
Módulo Administração / Configurações.
Sistema Seu Caldo 24 - M.A Sistemas
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import PERFIS
from services.administracao_service import AdministracaoService
from utils.helpers import alerta, confirmar, fmt_data, info


PERMISSOES_DISPONIVEIS = [
    "Dashboard",
    "Estoque",
    "Clientes",
    "Produção",
    "Financeiro",
    "PDV",
    "Relatórios",
    "Administração",
]


def _configurar_tabela(tabela):
    tabela.horizontalHeader().setSectionResizeMode(
        QHeaderView.Stretch
    )
    tabela.setEditTriggers(QTableWidget.NoEditTriggers)
    tabela.setSelectionBehavior(QTableWidget.SelectRows)
    tabela.setSelectionMode(QTableWidget.SingleSelection)


class UsuarioDialog(QDialog):
    def __init__(
        self,
        parent=None,
        usuario=None,
        operador=None,
    ):
        super().__init__(parent)

        self.service = AdministracaoService()
        self.usuario = usuario
        self.operador = operador

        self.setWindowTitle(
            "Editar Usuário" if usuario else "Novo Usuário"
        )
        self.setMinimumWidth(500)

        layout = QFormLayout(self)

        self.nome = QLineEdit()
        self.login = QLineEdit()
        self.senha = QLineEdit()
        self.senha.setEchoMode(QLineEdit.Password)
        self.senha.setPlaceholderText(
            "Deixe vazio para manter a senha atual"
            if usuario
            else "Mínimo de 6 caracteres"
        )

        self.perfil = QComboBox()
        self.perfil.addItems(PERFIS)

        self.ativo = QCheckBox("Usuário ativo")
        self.ativo.setChecked(True)

        self.permissoes = []

        permissoes_widget = QWidget()
        permissoes_layout = QVBoxLayout(permissoes_widget)
        permissoes_layout.setContentsMargins(0, 0, 0, 0)

        for nome in PERMISSOES_DISPONIVEIS:
            checkbox = QCheckBox(nome)
            self.permissoes.append(checkbox)
            permissoes_layout.addWidget(checkbox)

        layout.addRow("Nome:", self.nome)
        layout.addRow("Login:", self.login)
        layout.addRow("Senha:", self.senha)
        layout.addRow("Perfil:", self.perfil)
        layout.addRow("Status:", self.ativo)
        layout.addRow("Permissões:", permissoes_widget)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(self.reject)

        salvar = QPushButton("Salvar")
        salvar.clicked.connect(self._salvar)

        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)
        layout.addRow(botoes)

        if usuario:
            self._preencher(usuario)
        else:
            self._marcar_permissoes_por_perfil()

        self.perfil.currentTextChanged.connect(
            self._marcar_permissoes_por_perfil
        )

    def _preencher(self, usuario):
        self.nome.setText(usuario.get("nome", ""))
        self.login.setText(usuario.get("login", ""))
        self.perfil.setCurrentText(
            usuario.get("perfil", "Caixa/Atendente")
        )
        self.ativo.setChecked(usuario.get("ativo", True))

        permissoes = usuario.get("permissoes", [])

        for checkbox in self.permissoes:
            checkbox.setChecked(
                checkbox.text() in permissoes
            )

    def _marcar_permissoes_por_perfil(self):
        perfil = self.perfil.currentText()

        mapas = {
            "Administrador": PERMISSOES_DISPONIVEIS,
            "Gerente": [
                "Dashboard",
                "Estoque",
                "Clientes",
                "Produção",
                "Financeiro",
                "PDV",
                "Relatórios",
            ],
            "Caixa/Atendente": [
                "Dashboard",
                "Clientes",
                "PDV",
            ],
            "Cozinha": [
                "Dashboard",
                "Estoque",
                "Produção",
            ],
            "Financeiro": [
                "Dashboard",
                "Clientes",
                "Financeiro",
                "Relatórios",
            ],
        }

        permitidas = mapas.get(perfil, [])

        for checkbox in self.permissoes:
            checkbox.setChecked(
                checkbox.text() in permitidas
            )

    def _salvar(self):
        try:
            usuario_id = (
                str(self.usuario["_id"])
                if self.usuario
                else None
            )

            self.service.salvar_usuario(
                {
                    "nome": self.nome.text(),
                    "login": self.login.text(),
                    "senha": self.senha.text(),
                    "perfil": self.perfil.currentText(),
                    "ativo": self.ativo.isChecked(),
                    "permissoes": [
                        item.text()
                        for item in self.permissoes
                        if item.isChecked()
                    ],
                },
                usuario_id=usuario_id,
                operador=self.operador,
            )

            self.accept()
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class AbaEmpresa(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario
        self.service = AdministracaoService()

        layout = QFormLayout(self)

        self.razao_social = QLineEdit()
        self.nome_fantasia = QLineEdit()
        self.cnpj = QLineEdit()
        self.endereco = QLineEdit()
        self.cidade = QLineEdit()
        self.telefone = QLineEdit()
        self.email = QLineEdit()
        self.chave_pix = QLineEdit()

        self.rodape = QTextEdit()
        self.rodape.setFixedHeight(70)

        self.pontos_por_real = QSpinBox()
        self.pontos_por_real.setRange(0, 1000)

        self.backup_automatico = QCheckBox(
            "Habilitar backup automático"
        )

        self.hora_backup = QLineEdit()
        self.hora_backup.setPlaceholderText("23:00")

        salvar = QPushButton("Salvar Configurações")
        salvar.clicked.connect(self._salvar)

        layout.addRow("Razão social:", self.razao_social)
        layout.addRow("Nome fantasia:", self.nome_fantasia)
        layout.addRow("CNPJ:", self.cnpj)
        layout.addRow("Endereço:", self.endereco)
        layout.addRow("Cidade:", self.cidade)
        layout.addRow("Telefone:", self.telefone)
        layout.addRow("E-mail:", self.email)
        layout.addRow("Chave PIX:", self.chave_pix)
        layout.addRow("Rodapé dos relatórios:", self.rodape)
        layout.addRow("Pontos por R$ 1,00:", self.pontos_por_real)
        layout.addRow("Backup:", self.backup_automatico)
        layout.addRow("Horário do backup:", self.hora_backup)
        layout.addRow(salvar)

        self.atualizar()

    def atualizar(self):
        dados = self.service.obter_configuracoes()

        self.razao_social.setText(
            dados.get("razao_social", "")
        )
        self.nome_fantasia.setText(
            dados.get("nome_fantasia", "")
        )
        self.cnpj.setText(dados.get("cnpj", ""))
        self.endereco.setText(dados.get("endereco", ""))
        self.cidade.setText(dados.get("cidade", ""))
        self.telefone.setText(dados.get("telefone", ""))
        self.email.setText(dados.get("email", ""))
        self.chave_pix.setText(dados.get("chave_pix", ""))
        self.rodape.setPlainText(
            dados.get("rodape_relatorios", "")
        )
        self.pontos_por_real.setValue(
            int(dados.get("pontos_por_real", 1))
        )
        self.backup_automatico.setChecked(
            dados.get("backup_automatico", False)
        )
        self.hora_backup.setText(
            dados.get("hora_backup", "23:00")
        )

    def _salvar(self):
        try:
            self.service.salvar_configuracoes(
                {
                    "razao_social": self.razao_social.text(),
                    "nome_fantasia": self.nome_fantasia.text(),
                    "cnpj": self.cnpj.text(),
                    "endereco": self.endereco.text(),
                    "cidade": self.cidade.text(),
                    "telefone": self.telefone.text(),
                    "email": self.email.text(),
                    "chave_pix": self.chave_pix.text(),
                    "rodape_relatorios": self.rodape.toPlainText(),
                    "pontos_por_real": self.pontos_por_real.value(),
                    "backup_automatico": (
                        self.backup_automatico.isChecked()
                    ),
                    "hora_backup": self.hora_backup.text(),
                },
                usuario=self.usuario,
            )

            info(
                self,
                "Configurações",
                "Configurações salvas com sucesso.",
            )
        except ValueError as exc:
            alerta(self, "Atenção", str(exc))


class AbaUsuarios(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario_logado = usuario
        self.service = AdministracaoService()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        novo = QPushButton("+ Novo Usuário")
        novo.clicked.connect(self._novo)

        editar = QPushButton("Editar")
        editar.setObjectName("btnSecundario")
        editar.clicked.connect(self._editar)

        status = QPushButton("Ativar / Desativar")
        status.setObjectName("btnSecundario")
        status.clicked.connect(self._alternar_status)

        senha = QPushButton("Alterar Senha")
        senha.clicked.connect(self._alterar_senha)

        topo.addWidget(novo)
        topo.addWidget(editar)
        topo.addWidget(status)
        topo.addWidget(senha)
        topo.addStretch()

        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 5)
        self.tabela.setHorizontalHeaderLabels([
            "Nome",
            "Login",
            "Perfil",
            "Permissões",
            "Status",
        ])
        _configurar_tabela(self.tabela)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        usuarios = self.service.listar_usuarios()
        self.tabela.setRowCount(0)

        for usuario in usuarios:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            item_nome = QTableWidgetItem(
                usuario.get("nome", "")
            )
            item_nome.setData(
                Qt.UserRole,
                str(usuario["_id"]),
            )

            valores = [
                item_nome,
                QTableWidgetItem(usuario.get("login", "")),
                QTableWidgetItem(usuario.get("perfil", "")),
                QTableWidgetItem(
                    ", ".join(usuario.get("permissoes", []))
                ),
                QTableWidgetItem(
                    "Ativo"
                    if usuario.get("ativo", True)
                    else "Inativo"
                ),
            ]

            for coluna, item in enumerate(valores):
                self.tabela.setItem(row, coluna, item)

    def usuario_selecionado(self):
        row = self.tabela.currentRow()

        if row < 0:
            return None

        usuario_id = self.tabela.item(
            row,
            0,
        ).data(Qt.UserRole)

        return self.service.buscar_usuario(usuario_id)

    def _novo(self):
        if UsuarioDialog(
            self,
            operador=self.usuario_logado,
        ).exec():
            self.atualizar()

    def _editar(self):
        usuario = self.usuario_selecionado()

        if not usuario:
            alerta(
                self,
                "Atenção",
                "Selecione um usuário.",
            )
            return

        if UsuarioDialog(
            self,
            usuario=usuario,
            operador=self.usuario_logado,
        ).exec():
            self.atualizar()

    def _alternar_status(self):
        usuario = self.usuario_selecionado()

        if not usuario:
            alerta(
                self,
                "Atenção",
                "Selecione um usuário.",
            )
            return

        if str(usuario["_id"]) == str(
            self.usuario_logado.get("_id")
        ):
            alerta(
                self,
                "Atenção",
                "Você não pode desativar seu próprio usuário.",
            )
            return

        self.service.alternar_usuario(
            str(usuario["_id"]),
            operador=self.usuario_logado,
        )
        self.atualizar()

    def _alterar_senha(self):
        usuario = self.usuario_selecionado()

        if not usuario:
            alerta(
                self,
                "Atenção",
                "Selecione um usuário.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Alterar Senha")
        form = QFormLayout(dialog)

        senha = QLineEdit()
        senha.setEchoMode(QLineEdit.Password)

        confirmar_senha = QLineEdit()
        confirmar_senha.setEchoMode(QLineEdit.Password)

        form.addRow("Nova senha:", senha)
        form.addRow("Confirmar senha:", confirmar_senha)

        botoes = QHBoxLayout()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btnSecundario")
        cancelar.clicked.connect(dialog.reject)

        salvar = QPushButton("Alterar")

        def executar():
            if senha.text() != confirmar_senha.text():
                alerta(
                    dialog,
                    "Atenção",
                    "As senhas não conferem.",
                )
                return

            try:
                self.service.alterar_senha(
                    str(usuario["_id"]),
                    senha.text(),
                    operador=self.usuario_logado,
                )
                dialog.accept()
            except ValueError as exc:
                alerta(dialog, "Atenção", str(exc))

        salvar.clicked.connect(executar)

        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)
        form.addRow(botoes)

        if dialog.exec():
            info(
                self,
                "Senha alterada",
                "Senha alterada com sucesso.",
            )


class AbaBackup(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario
        self.service = AdministracaoService()

        layout = QVBoxLayout(self)

        titulo = QLabel(
            "Backup completo do banco de dados em arquivo JSON."
        )
        titulo.setStyleSheet(
            "font-size:15px; font-weight:bold;"
        )

        aviso = QLabel(
            "A restauração substitui os dados atuais. "
            "Faça um backup antes de restaurar."
        )
        aviso.setWordWrap(True)

        criar = QPushButton("Criar Backup")
        criar.clicked.connect(self._criar_backup)

        restaurar = QPushButton("Restaurar Backup")
        restaurar.setObjectName("btnPerigo")
        restaurar.clicked.connect(self._restaurar_backup)

        layout.addWidget(titulo)
        layout.addWidget(aviso)
        layout.addSpacing(20)
        layout.addWidget(criar)
        layout.addWidget(restaurar)
        layout.addStretch()

    def _criar_backup(self):
        pasta = QFileDialog.getExistingDirectory(
            self,
            "Escolher pasta para o backup",
        )

        if not pasta:
            return

        try:
            caminho = self.service.criar_backup(
                pasta,
                usuario=self.usuario,
            )

            info(
                self,
                "Backup concluído",
                f"Backup salvo em:\n{caminho}",
            )
        except Exception as exc:
            alerta(self, "Erro no backup", str(exc))

    def _restaurar_backup(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar backup",
            "",
            "Backup JSON (*.json)",
        )

        if not caminho:
            return

        if not confirmar(
            self,
            "Confirmar restauração",
            (
                "Todos os dados atuais serão substituídos "
                "pelos dados do backup.\n\nContinuar?"
            ),
        ):
            return

        try:
            self.service.restaurar_backup(
                caminho,
                usuario=self.usuario,
            )

            QMessageBox.information(
                self,
                "Restauração concluída",
                (
                    "Backup restaurado com sucesso.\n"
                    "Feche e abra o sistema novamente."
                ),
            )
        except ValueError as exc:
            alerta(self, "Erro na restauração", str(exc))


class AbaAuditoria(QWidget):
    def __init__(self):
        super().__init__()

        self.service = AdministracaoService()

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()

        self.busca = QLineEdit()
        self.busca.setPlaceholderText(
            "Buscar usuário, módulo, ação ou detalhes..."
        )
        self.busca.textChanged.connect(self.atualizar)

        atualizar = QPushButton("Atualizar")
        atualizar.setObjectName("btnSecundario")
        atualizar.clicked.connect(self.atualizar)

        topo.addWidget(self.busca, 1)
        topo.addWidget(atualizar)

        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 6)
        self.tabela.setHorizontalHeaderLabels([
            "Data",
            "Usuário",
            "Perfil",
            "Módulo",
            "Ação",
            "Detalhes",
        ])
        _configurar_tabela(self.tabela)

        layout.addWidget(self.tabela)

        self.atualizar()

    def atualizar(self):
        registros = self.service.listar_auditoria(
            self.busca.text()
        )

        self.tabela.setRowCount(0)

        for registro in registros:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            valores = [
                fmt_data(registro.get("data")),
                registro.get("usuario_nome", ""),
                registro.get("perfil", ""),
                registro.get("modulo", ""),
                registro.get("acao", ""),
                registro.get("detalhes", ""),
            ]

            for coluna, valor in enumerate(valores):
                self.tabela.setItem(
                    row,
                    coluna,
                    QTableWidgetItem(str(valor)),
                )


class AdministracaoWidget(QWidget):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        titulo = QLabel("Administração / Configurações")
        titulo.setObjectName("tituloPagina")
        layout.addWidget(titulo)

        self.tabs = QTabWidget()

        self.aba_empresa = AbaEmpresa(usuario)
        self.aba_usuarios = AbaUsuarios(usuario)
        self.aba_backup = AbaBackup(usuario)
        self.aba_auditoria = AbaAuditoria()

        self.tabs.addTab(
            self.aba_empresa,
            "Empresa / Parâmetros"
        )
        self.tabs.addTab(
            self.aba_usuarios,
            "Usuários / Permissões"
        )
        self.tabs.addTab(
            self.aba_backup,
            "Backup / Restauração"
        )
        self.tabs.addTab(
            self.aba_auditoria,
            "Auditoria"
        )

        layout.addWidget(self.tabs)

    def atualizar(self):
        self.aba_empresa.atualizar()
        self.aba_usuarios.atualizar()
        self.aba_auditoria.atualizar()