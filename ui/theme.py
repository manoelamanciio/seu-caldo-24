# -*- coding: utf-8 -*-
"""Tema visual do sistema Seu Caldo 24 - M.A Sistemas"""

COR_PRIMARIA = "#E8590C"
COR_PRIMARIA_ESCURA = "#C94E0B"

COR_FUNDO = "#1E1F26"
COR_FUNDO_DIALOG = "#22242E"
COR_FUNDO_CARD = "#282A36"
COR_FUNDO_CAMPO = "#20222C"
COR_FUNDO_HOVER = "#343744"

COR_TEXTO = "#F4F4F5"
COR_TEXTO_SECUNDARIO = "#C5C7D0"
COR_TEXTO_SUAVE = "#A8ABB5"

COR_BORDA = "#444754"
COR_SUCESSO = "#2ECC71"
COR_ALERTA = "#F1C40F"
COR_PERIGO = "#E74C3C"


QSS = f"""
* {{
    font-family: "Segoe UI", "Arial";
    font-size: 13px;
    color: {COR_TEXTO};
}}

QMainWindow,
QWidget#centralWidget {{
    background-color: {COR_FUNDO};
}}

/* ---------------------------------------------------------
   JANELAS E DIÁLOGOS
--------------------------------------------------------- */

QDialog {{
    background-color: {COR_FUNDO_DIALOG};
}}

QDialog QLabel {{
    color: {COR_TEXTO};
    font-weight: 600;
}}

QMessageBox {{
    background-color: {COR_FUNDO_DIALOG};
}}

QMessageBox QLabel {{
    color: {COR_TEXTO};
    font-weight: 500;
}}

/* ---------------------------------------------------------
   SIDEBAR
--------------------------------------------------------- */

QWidget#sidebar {{
    background-color: #16171C;
}}

QWidget#topbar {{
    background-color: {COR_FUNDO_CARD};
    border-bottom: 1px solid #33343D;
}}

QLabel#logo {{
    color: {COR_PRIMARIA};
    font-size: 20px;
    font-weight: bold;
    padding: 18px;
}}

QLabel#subtitulo {{
    color: {COR_TEXTO_SUAVE};
    font-size: 11px;
    padding-left: 18px;
    margin-top: -14px;
}}

QPushButton#menuBtn {{
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 12px 18px;
    font-size: 13px;
    border-left: 3px solid transparent;
    color: {COR_TEXTO};
}}

QPushButton#menuBtn:hover {{
    background-color: #21222B;
    border-left: 3px solid {COR_PRIMARIA};
}}

QPushButton#menuBtnAtivo {{
    background-color: #21222B;
    border-left: 3px solid {COR_PRIMARIA};
    font-weight: bold;
    color: white;
}}

/* ---------------------------------------------------------
   CARDS
--------------------------------------------------------- */

QFrame.card {{
    background-color: {COR_FUNDO_CARD};
    border-radius: 10px;
    padding: 14px;
}}

/* ---------------------------------------------------------
   BOTÕES
--------------------------------------------------------- */

QPushButton {{
    background-color: {COR_PRIMARIA};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {COR_PRIMARIA_ESCURA};
}}

QPushButton:pressed {{
    background-color: #A94008;
}}

QPushButton:disabled {{
    background-color: #555863;
    color: #B0B2B8;
}}

QPushButton#btnSecundario {{
    background-color: #3A3D49;
    color: white;
}}

QPushButton#btnSecundario:hover {{
    background-color: #4A4E5C;
}}

QPushButton#btnPerigo {{
    background-color: {COR_PERIGO};
    color: white;
}}

QPushButton#btnPerigo:hover {{
    background-color: #C0392B;
}}

/* ---------------------------------------------------------
   CAMPOS
--------------------------------------------------------- */

QLineEdit,
QComboBox,
QDateEdit,
QSpinBox,
QDoubleSpinBox,
QTextEdit,
QDateTimeEdit {{
    background-color: {COR_FUNDO_CAMPO};
    border: 1px solid {COR_BORDA};
    border-radius: 6px;
    padding: 7px 9px;
    color: white;
    selection-background-color: {COR_PRIMARIA};
    selection-color: white;
}}

QLineEdit::placeholder {{
    color: #8E919C;
}}

QLineEdit:focus,
QComboBox:focus,
QDateEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QTextEdit:focus,
QDateTimeEdit:focus {{
    border: 1px solid {COR_PRIMARIA};
    background-color: #242732;
}}

/* ---------------------------------------------------------
   COMBOBOX
--------------------------------------------------------- */

QComboBox {{
    padding-right: 28px;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid {COR_BORDA};
    background-color: #2E313D;
}}

QComboBox::drop-down:hover {{
    background-color: {COR_FUNDO_HOVER};
}}

QComboBox QAbstractItemView {{
    background-color: {COR_FUNDO_DIALOG};
    color: white;
    border: 1px solid {COR_BORDA};
    selection-background-color: {COR_PRIMARIA};
    selection-color: white;
    outline: none;
    padding: 4px;
}}

/* ---------------------------------------------------------
   SPINBOX
--------------------------------------------------------- */

QSpinBox::up-button,
QDoubleSpinBox::up-button,
QDateEdit::up-button,
QDateTimeEdit::up-button {{
    background-color: #2E313D;
    border-left: 1px solid {COR_BORDA};
    border-bottom: 1px solid {COR_BORDA};
    width: 22px;
}}

QSpinBox::down-button,
QDoubleSpinBox::down-button,
QDateEdit::down-button,
QDateTimeEdit::down-button {{
    background-color: #2E313D;
    border-left: 1px solid {COR_BORDA};
    width: 22px;
}}

QSpinBox::up-button:hover,
QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover {{
    background-color: {COR_FUNDO_HOVER};
}}

/* ---------------------------------------------------------
   TABELAS
--------------------------------------------------------- */

QTableWidget {{
    background-color: {COR_FUNDO_CARD};
    alternate-background-color: #242630;
    gridline-color: #3A3D48;
    border: 1px solid #363945;
    border-radius: 8px;
    selection-background-color: {COR_PRIMARIA};
    selection-color: white;
    color: {COR_TEXTO};
}}

QTableWidget::item {{
    padding: 6px;
}}

QTableWidget::item:selected {{
    background-color: {COR_PRIMARIA};
    color: white;
}}

QHeaderView::section {{
    background-color: #333641;
    color: white;
    padding: 8px;
    border: none;
    border-right: 1px solid #414450;
    font-weight: bold;
}}

/* ---------------------------------------------------------
   ABAS
--------------------------------------------------------- */

QTabWidget::pane {{
    border: 1px solid #333641;
    border-radius: 8px;
    top: -1px;
    background-color: transparent;
}}

QTabBar::tab {{
    background: {COR_FUNDO_CARD};
    color: {COR_TEXTO_SECUNDARIO};
    padding: 10px 18px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}}

QTabBar::tab:hover {{
    background-color: #343744;
    color: white;
}}

QTabBar::tab:selected {{
    background: {COR_PRIMARIA};
    color: white;
    font-weight: bold;
}}

/* ---------------------------------------------------------
   BARRAS DE ROLAGEM
--------------------------------------------------------- */

QScrollBar:vertical {{
    background: {COR_FUNDO};
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: #555967;
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: #696D7C;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ---------------------------------------------------------
   TEXTOS ESPECÍFICOS
--------------------------------------------------------- */

QLabel#tituloPagina {{
    font-size: 20px;
    font-weight: bold;
    color: white;
}}

QLabel#kpiValor {{
    font-size: 26px;
    font-weight: bold;
    color: {COR_PRIMARIA};
}}

QLabel#kpiTitulo {{
    font-size: 12px;
    color: {COR_TEXTO_SECUNDARIO};
}}
"""