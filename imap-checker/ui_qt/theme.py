"""
Light Warm Yellow + Black text + Dark Blue headers theme.
Background : #fffbe6  (warm light yellow)
Text       : #1a1a1a  (near black)
Headers    : #1a3a6e  (dark blue)
Accent     : #d4a017  (golden)
"""

APP_STYLE = """
/* ── Base ── */
QMainWindow, QDialog, QWidget {
    background-color: #fffbe6;
    color: #1a1a1a;
    font-family: 'SF Pro Display', 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}

/* ── ToolBar ── */
QToolBar {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1a3a6e,
        stop:0.6 #1e4a8a,
        stop:1 #163060);
    border-bottom: 3px solid #d4a017;
    padding: 4px 8px;
    spacing: 4px;
}
QToolBar::separator {
    background: #4a6aae;
    width: 1px;
    margin: 4px 8px;
}
QToolBar QToolButton {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #24508e, stop:1 #1a3a6e);
    color: #e8f0ff;
    border: 1px solid #4a6aae;
    border-radius: 7px;
    padding: 5px 14px;
    font-weight: 700;
    font-size: 13px;
    min-width: 80px;
}
QToolBar QToolButton:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #2e60a8, stop:1 #1e4a88);
    border-color: #d4a017;
    color: #ffe082;
}
QToolBar QToolButton:pressed {
    background: #102848;
    border-color: #ffca28;
    color: #ffca28;
}

/* ── Table ── */
QTableWidget {
    background-color: #fffdf0;
    alternate-background-color: #fff8d6;
    gridline-color: #e8d88a;
    color: #1a1a1a;
    border: 1px solid #d4c060;
    border-radius: 6px;
    selection-background-color: #c8deff;
    selection-color: #0a1a40;
}
QTableWidget::item {
    padding: 4px 7px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #c8deff;
    color: #0a1a40;
    border-left: 3px solid #1a3a6e;
}
QHeaderView::section {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #1e4a8a, stop:1 #1a3a6e);
    color: #ffffff;
    font-weight: 700;
    font-size: 12px;
    border: none;
    border-right: 1px solid #4a6aae;
    border-bottom: 2px solid #d4a017;
    padding: 6px 7px;
    letter-spacing: 0.3px;
}
QHeaderView::section:hover {
    background: #2e60a8;
    color: #ffe082;
}

/* ── Scrollbar ── */
QScrollBar:vertical {
    background: #f5e8b0;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #1a3a6e;
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover { background: #d4a017; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #f5e8b0;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #1a3a6e;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover { background: #d4a017; }

/* ── Status bar ── */
QStatusBar {
    background: #fff8cc;
    color: #1a3a6e;
    border-top: 1px solid #d4c060;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 8px;
}

/* ── Log panel ── */
QTextEdit#log_panel {
    background-color: #fffdf0;
    color: #1a1a1a;
    font-family: 'JetBrains Mono', 'Fira Code', 'Menlo', 'Consolas', monospace;
    font-size: 12px;
    border: none;
    border-top: 2px solid #1a3a6e;
    padding: 7px;
}

/* ── Time label ── */
QLabel#time_label {
    color: #1a3a6e;
    font-weight: 700;
    font-size: 14px;
    padding: 3px 10px;
    background: #fff8cc;
    border-bottom: 1px solid #d4c060;
    letter-spacing: 1px;
}

/* ── Log header ── */
QLabel#log_header {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1a3a6e, stop:1 #1e4a8a);
    color: #ffe082;
    font-weight: 700;
    font-size: 12px;
    padding: 4px 10px;
    border-bottom: 1px solid #d4a017;
}

/* ── Splitter ── */
QSplitter::handle {
    background: #d4c060;
    height: 3px;
}
QSplitter::handle:hover { background: #1a3a6e; }

/* ── Dialog ── */
QDialog {
    background: #fffbe6;
}
QTabWidget::pane {
    border: 1px solid #d4c060;
    background: #fffbe6;
    border-radius: 0 6px 6px 6px;
}
QTabBar::tab {
    background: #fff0a0;
    color: #1a3a6e;
    padding: 8px 20px;
    border: 1px solid #d4c060;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    font-weight: 700;
}
QTabBar::tab:selected {
    background: #fffbe6;
    color: #1a3a6e;
    border-color: #1a3a6e;
    border-bottom: 2px solid #fffbe6;
}
QTabBar::tab:hover { background: #ffe87a; color: #0e2858; }

/* ── Form fields ── */
QLineEdit, QSpinBox, QComboBox, QTimeEdit {
    background: #ffffff;
    color: #1a1a1a;
    border: 1px solid #c8b84a;
    border-radius: 5px;
    padding: 5px 8px;
    selection-background-color: #c8deff;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTimeEdit:focus {
    border: 2px solid #1a3a6e;
    background: #f8f4e0;
}
/* Editor NẰM TRONG Ô BẢNG: bỏ padding/bo góc của rule QLineEdit chung —
   editor bị ép đúng chiều cao ô (32px), padding 5px trên+dưới + border focus
   2px làm chữ bị CẮT MẤT CHÂN khi nhập ở mọi bảng. */
QTableWidget QLineEdit, QTableView QLineEdit {
    padding: 0px 4px;
    border: 1px solid #1a3a6e;
    border-radius: 0;
}
QTableWidget QLineEdit:focus, QTableView QLineEdit:focus {
    padding: 0px 4px;
    border: 1px solid #1a3a6e;
    background: #ffffff;
}
/* ComboBox NẰM TRONG Ô BẢNG (vd cột 'Hãng thẻ', 'Nhận OTP'): bỏ padding
   trên/dưới — padding 5px trong ô cao 32px làm CẮT CHÂN chữ (vd 'PayPay'). */
QTableWidget QComboBox, QTableView QComboBox {
    padding: 0px 6px;
    border-radius: 0;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox::down-arrow { image: none; }
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #1a1a1a;
    border: 1px solid #c8b84a;
    selection-background-color: #c8deff;
    selection-color: #0a1a40;
}
QSpinBox::up-button, QSpinBox::down-button {
    background: #f5e8b0;
    border: none;
    width: 16px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #d4c060; }

/* ── GroupBox ── */
QGroupBox {
    background: #fffdf0;
    border: 1px solid #c8b84a;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: 700;
    color: #1a3a6e;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    top: -2px;
    color: #1a3a6e;
    padding: 0 6px;
    background: #fffbe6;
    font-size: 13px;
}

/* ── Buttons ── */
QPushButton {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #24508e, stop:1 #1a3a6e);
    color: #e8f0ff;
    border: 1px solid #4a6aae;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 700;
    min-width: 70px;
}
QPushButton:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #2e60a8, stop:1 #1e4a88);
    border-color: #d4a017;
    color: #ffe082;
}
QPushButton:pressed { background: #102848; }

/* ── Checkbox, RadioButton ── */
QCheckBox, QRadioButton {
    color: #1a1a1a;
    spacing: 8px;
    font-size: 13px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #1a3a6e;
    border-radius: 3px;
    background: #ffffff;
}
QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background: #1a3a6e;
    border-color: #1a3a6e;
}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {
    border-color: #d4a017;
}

/* ── Disabled states — làm mờ toàn bộ widget bị vô hiệu hoá ── */
QWidget:disabled {
    color: #b0a870;
}
QGroupBox:disabled {
    border-color: #ddd8a0;
    background: #faf8ec;
}
QGroupBox::title:disabled {
    color: #b0a870;
}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled, QTimeEdit:disabled {
    background: #f5f0d8;
    color: #b0a870;
    border-color: #ddd8a0;
}
QCheckBox:disabled, QRadioButton:disabled {
    color: #b0a870;
}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
    border-color: #c8c090;
    background: #f0ecd0;
}
QCheckBox::indicator:checked:disabled, QRadioButton::indicator:checked:disabled {
    background: #c0bc90;
    border-color: #c0bc90;
}
QPushButton:disabled {
    background: #e0d8a8;
    color: #b0a870;
    border-color: #c8c090;
}
QLabel:disabled {
    color: #b0a870;
}

/* ── MessageBox ── */
QMessageBox {
    background: #fffbe6;
    color: #1a1a1a;
}
QMessageBox QPushButton { min-width: 80px; }

/* ── ToolTip ── */
QToolTip {
    background: #1a3a6e;
    color: #ffe082;
    border: 1px solid #d4a017;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
"""
