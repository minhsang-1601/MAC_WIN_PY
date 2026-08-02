#!/usr/bin/env python3
"""4 trang chính của app: Tổng quan, Chạy Job, Quản lý Account, Cấu hình."""
import csv
import os
from datetime import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

import helpers as h


# ============================================================
# Chạy subprocess không block UI (QProcess) — dùng chung cho mọi tab job
# ============================================================

class ProcessRunner(QtCore.QObject):
    output = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(int)

    def __init__(self, cmd, cwd=None, parent=None):
        super().__init__(parent)
        self.process = QtCore.QProcess(self)
        if cwd:
            self.process.setWorkingDirectory(cwd)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_ready)
        self.process.finished.connect(lambda code, status: self.finished.emit(code))
        self.cmd = cmd

    def start(self):
        self.process.start(self.cmd[0], self.cmd[1:])

    def _on_ready(self):
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.output.emit(data)

    def kill(self):
        if self.process.state() != QtCore.QProcess.NotRunning:
            self.process.kill()


def snapshot_mtimes(folder):
    if not folder.exists():
        return {}
    return {p.name: p.stat().st_mtime for p in folder.iterdir() if p.is_file()}


def newest_files_since(folder, before_mtimes, suffixes):
    found = []
    if not folder.exists():
        return found
    for p in folder.iterdir():
        if p.is_file() and p.suffix in suffixes:
            mtime = p.stat().st_mtime
            if p.name not in before_mtimes or mtime > before_mtimes[p.name]:
                found.append(p)
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def load_csv_rows(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.reader(f))


# ============================================================
# TRANG 1: TỔNG QUAN
# ============================================================

class DashboardPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)

        top = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Tổng quan")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #1a3a6e;")
        top.addWidget(title)
        top.addStretch()
        self.refresh_btn = QtWidgets.QPushButton("🔄 Làm mới")
        self.refresh_btn.clicked.connect(self.reload)
        top.addWidget(self.refresh_btn)
        layout.addLayout(top)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        acc_box = QtWidgets.QGroupBox("📁 File account")
        acc_layout = QtWidgets.QVBoxLayout(acc_box)
        self.acc_table = QtWidgets.QTableWidget(0, 2)
        self.acc_table.setHorizontalHeaderLabels(["File", "Số account"])
        self.acc_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.acc_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.acc_table.setAlternatingRowColors(True)
        acc_layout.addWidget(self.acc_table)
        splitter.addWidget(acc_box)

        log_box = QtWidgets.QGroupBox("📝 Log gần đây (double-click để xem)")
        log_layout = QtWidgets.QVBoxLayout(log_box)
        self.log_list = QtWidgets.QListWidget()
        self.log_list.itemDoubleClicked.connect(self._open_log)
        log_layout.addWidget(self.log_list)
        splitter.addWidget(log_box)

        splitter.setSizes([350, 550])
        layout.addWidget(splitter)

        self.reload()

    def reload(self):
        files = h.list_account_files()
        self.acc_table.setRowCount(len(files))
        for row, p in enumerate(files):
            n = len(h.read_account_lines(p))
            self.acc_table.setItem(row, 0, QtWidgets.QTableWidgetItem(p.name))
            count_item = QtWidgets.QTableWidgetItem(str(n))
            count_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.acc_table.setItem(row, 1, count_item)

        self.log_list.clear()
        if h.LOG_DIR.exists():
            log_files = sorted(h.LOG_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:40]
            for p in log_files:
                mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                item = QtWidgets.QListWidgetItem(f"{p.name}   ·   {mtime}")
                item.setData(QtCore.Qt.UserRole, str(p))
                self.log_list.addItem(item)

    def _open_log(self, item):
        path = item.data(QtCore.Qt.UserRole)
        from pathlib import Path
        p = Path(path)
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(p.name)
        dlg.resize(700, 500)
        v = QtWidgets.QVBoxLayout(dlg)

        if p.suffix == ".csv":
            rows = load_csv_rows(p)
            table = QtWidgets.QTableWidget(max(0, len(rows) - 1), len(rows[0]) if rows else 0)
            if rows:
                table.setHorizontalHeaderLabels(rows[0])
                for r, row in enumerate(rows[1:]):
                    for c, val in enumerate(row):
                        table.setItem(r, c, QtWidgets.QTableWidgetItem(val))
            table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            v.addWidget(table)
        else:
            text = QtWidgets.QTextEdit()
            text.setReadOnly(True)
            text.setObjectName("log_panel")
            text.setPlainText(p.read_text(encoding="utf-8", errors="replace"))
            v.addWidget(text)

        btn_row = QtWidgets.QHBoxLayout()
        reveal_btn = QtWidgets.QPushButton("📂 Hiện trong Finder")
        reveal_btn.clicked.connect(lambda: QtCore.QProcess.startDetached("open", ["-R", str(p)]))
        btn_row.addWidget(reveal_btn)
        btn_row.addStretch()
        close_btn = QtWidgets.QPushButton("Đóng")
        close_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(close_btn)
        v.addLayout(btn_row)

        dlg.exec_()


# ============================================================
# TRANG 2: CHẠY JOB
# ============================================================

class BaseJobTab(QtWidgets.QWidget):
    """Tiện ích chung: log panel + chạy script qua QProcess."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._runner = None

    def make_log_panel(self):
        log = QtWidgets.QTextEdit()
        log.setObjectName("log_panel")
        log.setReadOnly(True)
        log.setMinimumHeight(180)
        return log

    def run_script(self, cmd, log_widget, run_btn, on_finished=None):
        run_btn.setEnabled(False)
        log_widget.clear()
        self._runner = ProcessRunner(cmd, cwd=str(h.SCRIPTS_DIR))
        self._runner.output.connect(lambda s: self._append_log(log_widget, s))
        self._runner.finished.connect(lambda code: self._on_finished(code, run_btn, on_finished))
        self._runner.start()

    def _append_log(self, log_widget, text):
        cursor = log_widget.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        log_widget.setTextCursor(cursor)
        log_widget.ensureCursorVisible()

    def _on_finished(self, code, run_btn, on_finished):
        run_btn.setEnabled(True)
        if on_finished:
            on_finished(code)


class CheckAllTab(BaseJobTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Chạy check_mail_all_common.py cho nhiều account theo 1 section."))

        form = QtWidgets.QFormLayout()
        self.section_cb = QtWidgets.QComboBox()
        self.file_cb = QtWidgets.QComboBox()
        form.addRow("Section:", self.section_cb)
        form.addRow("File account:", self.file_cb)
        layout.addLayout(form)

        self.send_cb = QtWidgets.QCheckBox("Gửi mail báo cáo sau khi xong")
        self.send_cb.setChecked(True)
        layout.addWidget(self.send_cb)

        self.run_btn = QtWidgets.QPushButton("▶️ Chạy")
        self.run_btn.setProperty("class", "primary")
        self.run_btn.clicked.connect(self._run)
        layout.addWidget(self.run_btn)

        self.log = self.make_log_panel()
        layout.addWidget(self.log)

        result_row = QtWidgets.QHBoxLayout()
        self.summary_box = QtWidgets.QTextEdit()
        self.summary_box.setReadOnly(True)
        self.summary_box.setObjectName("log_panel")
        self.result_table = QtWidgets.QTableWidget(0, 0)
        self.result_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        result_row.addWidget(self.summary_box, 1)
        result_row.addWidget(self.result_table, 2)
        layout.addLayout(result_row)

        self.reload_options()

    def reload_options(self):
        cfg = h.load_ini()
        self.section_cb.clear()
        self.section_cb.addItems(h.job_sections(cfg))

        self.file_cb.clear()
        self._files = h.list_account_files()
        for p in self._files:
            n = len(h.read_account_lines(p))
            self.file_cb.addItem(f"{p.name} ({n} account)")

    def _run(self):
        if not self._files or self.section_cb.count() == 0:
            QtWidgets.QMessageBox.warning(self, "Thiếu dữ liệu", "Chưa có section hoặc file account.")
            return
        section = self.section_cb.currentText()
        accounts_path = self._files[self.file_cb.currentIndex()]
        send_flag = "1" if self.send_cb.isChecked() else "0"

        self._before = snapshot_mtimes(h.LOG_DIR)
        cmd = [h.PY_CMD, str(h.SCRIPT_CHECK_ALL), section, str(accounts_path), send_flag]
        self.run_script(cmd, self.log, self.run_btn, on_finished=self._show_results)

    def _show_results(self, code):
        new_files = newest_files_since(h.LOG_DIR, self._before, {".csv", ".txt"})
        for p in new_files:
            if p.name.endswith("_TongKet.txt"):
                self.summary_box.setPlainText(p.read_text(encoding="utf-8"))
            elif p.name.endswith(".csv"):
                rows = load_csv_rows(p)
                self.result_table.setRowCount(max(0, len(rows) - 1))
                self.result_table.setColumnCount(len(rows[0]) if rows else 0)
                if rows:
                    self.result_table.setHorizontalHeaderLabels(rows[0])
                    for r, row in enumerate(rows[1:]):
                        for c, val in enumerate(row):
                            self.result_table.setItem(r, c, QtWidgets.QTableWidgetItem(val))


class SingleAccountTab(BaseJobTab):
    """Dùng chung cho 'Check 1 account' và 'Xem full mail' — chỉ khác script gọi."""

    def __init__(self, script_path, description, parent=None):
        super().__init__(parent)
        self.script_path = script_path
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(description))

        form = QtWidgets.QFormLayout()
        self.email_edit = QtWidgets.QLineEdit()
        pwd_row = QtWidgets.QHBoxLayout()
        self.pwd_edit = QtWidgets.QLineEdit()
        self.pwd_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.show_pwd_btn = QtWidgets.QPushButton("👁")
        self.show_pwd_btn.setFixedWidth(32)
        self.show_pwd_btn.setCheckable(True)
        self.show_pwd_btn.toggled.connect(
            lambda on: self.pwd_edit.setEchoMode(
                QtWidgets.QLineEdit.Normal if on else QtWidgets.QLineEdit.Password
            )
        )
        pwd_row.addWidget(self.pwd_edit)
        pwd_row.addWidget(self.show_pwd_btn)
        self.section_cb = QtWidgets.QComboBox()

        form.addRow("Email:", self.email_edit)
        form.addRow("App Password:", pwd_row)
        form.addRow("Section:", self.section_cb)
        layout.addLayout(form)

        self.run_btn = QtWidgets.QPushButton("▶️ Chạy")
        self.run_btn.clicked.connect(self._run)
        layout.addWidget(self.run_btn)

        self.log = self.make_log_panel()
        layout.addWidget(self.log)

        self.reload_options()

    def reload_options(self):
        cfg = h.load_ini()
        self.section_cb.clear()
        self.section_cb.addItems(h.job_sections(cfg))

    def _run(self):
        email_addr = self.email_edit.text().strip()
        pwd = self.pwd_edit.text()
        section = self.section_cb.currentText()
        if not email_addr or not pwd or not section:
            QtWidgets.QMessageBox.warning(self, "Thiếu dữ liệu", "Nhập đủ Email / Password / Section.")
            return
        cmd = [h.PY_CMD, str(self.script_path), email_addr, pwd, section]
        self.run_script(cmd, self.log, self.run_btn)


class CleanMailTab(BaseJobTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)

        warn = QtWidgets.QLabel("⚠️ Thao tác này XOÁ VĨNH VIỄN email trong hộp thư, không thể hoàn tác.")
        warn.setStyleSheet("color: #b00000; font-weight: 700;")
        layout.addWidget(warn)

        form = QtWidgets.QFormLayout()
        self.file_cb = QtWidgets.QComboBox()
        self.months_spin = QtWidgets.QSpinBox()
        self.months_spin.setRange(0, 120)
        self.months_spin.setValue(12)
        self.months_spin.setSuffix(" tháng (0 = xoá TOÀN BỘ)")
        form.addRow("File account sẽ dọn:", self.file_cb)
        form.addRow("Xoá email cũ hơn:", self.months_spin)
        layout.addLayout(form)

        self.confirm_edit = QtWidgets.QLineEdit()
        self.confirm_edit.setPlaceholderText('Gõ "XOA" để xác nhận')
        layout.addWidget(self.confirm_edit)

        self.confirm_cb = QtWidgets.QCheckBox("Tôi hiểu thao tác này không thể hoàn tác")
        layout.addWidget(self.confirm_cb)

        self.run_btn = QtWidgets.QPushButton("🧹 Xoá ngay")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._run)
        layout.addWidget(self.run_btn)

        self.confirm_edit.textChanged.connect(self._update_enabled)
        self.confirm_cb.toggled.connect(self._update_enabled)

        self.log = self.make_log_panel()
        layout.addWidget(self.log)

        self.reload_options()

    def reload_options(self):
        self.file_cb.clear()
        self._files = h.list_account_files()
        for p in self._files:
            n = len(h.read_account_lines(p))
            self.file_cb.addItem(f"{p.name} ({n} account)")

    def _update_enabled(self):
        ok = self.confirm_edit.text().strip().upper() == "XOA" and self.confirm_cb.isChecked()
        self.run_btn.setEnabled(ok)

    def _run(self):
        if not self._files:
            return
        fname = self._files[self.file_cb.currentIndex()].name
        cmd = [h.PY_CMD, str(h.SCRIPT_CLEAN), fname, str(self.months_spin.value())]
        self.run_script(cmd, self.log, self.run_btn)


class RunJobPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Chạy Job")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #1a3a6e;")
        layout.addWidget(title)

        self.tabs = QtWidgets.QTabWidget()
        self.tab_all = CheckAllTab()
        self.tab_one = SingleAccountTab(h.SCRIPT_CHECK_ONE, "Chạy check_gmail_common.py — tìm mail khớp keyword cho 1 account.")
        self.tab_body = SingleAccountTab(h.SCRIPT_GETBODY, "Chạy getbody_mail_common.py — in toàn bộ nội dung mail khớp section.")
        self.tab_clean = CleanMailTab()

        self.tabs.addTab(self.tab_all, "📚 Check hàng loạt")
        self.tabs.addTab(self.tab_one, "✉️ Check 1 account")
        self.tabs.addTab(self.tab_body, "📄 Xem full mail")
        self.tabs.addTab(self.tab_clean, "🧹 Dọn mail (xoá)")
        layout.addWidget(self.tabs)

    def reload(self):
        self.tab_all.reload_options()
        self.tab_one.reload_options()
        self.tab_body.reload_options()
        self.tab_clean.reload_options()


# ============================================================
# TRANG 3: QUẢN LÝ ACCOUNT
# ============================================================

class AccountsPage(QtWidgets.QWidget):
    COL_EMAIL, COL_PWD, COL_PROVIDER = 0, 1, 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dirty = False
        self._last_index = 0
        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Quản lý Account")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #1a3a6e;")
        layout.addWidget(title)

        top = QtWidgets.QHBoxLayout()
        self.file_cb = QtWidgets.QComboBox()
        self.file_cb.currentIndexChanged.connect(self._on_file_changed)
        top.addWidget(QtWidgets.QLabel("Chọn file:"))
        top.addWidget(self.file_cb, 1)

        self.new_name_edit = QtWidgets.QLineEdit()
        self.new_name_edit.setPlaceholderText("accounts_gm_moi")
        self.new_file_btn = QtWidgets.QPushButton("➕ Tạo file")
        self.new_file_btn.clicked.connect(self._create_file)
        top.addWidget(self.new_name_edit)
        top.addWidget(self.new_file_btn)
        layout.addLayout(top)

        self.show_pwd_cb = QtWidgets.QCheckBox("Hiện mật khẩu")
        self.show_pwd_cb.toggled.connect(self._toggle_pwd)
        layout.addWidget(self.show_pwd_cb)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Email", "Password", "Provider"])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        self.warn_label = QtWidgets.QLabel("")
        self.warn_label.setStyleSheet("color: #b00000; font-weight: 700;")
        self.warn_label.setWordWrap(True)
        layout.addWidget(self.warn_label)

        btn_row = QtWidgets.QHBoxLayout()
        add_row_btn = QtWidgets.QPushButton("➕ Thêm dòng")
        add_row_btn.clicked.connect(self._add_row)
        del_row_btn = QtWidgets.QPushButton("🗑️ Xoá dòng đã chọn")
        del_row_btn.clicked.connect(self._delete_selected_rows)
        save_btn = QtWidgets.QPushButton("💾 Lưu")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(add_row_btn)
        btn_row.addWidget(del_row_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        self.reload()

    def reload(self):
        """Nạp lại danh sách file + bảng từ đĩa — bỏ qua toàn bộ nếu đang có
        thay đổi chưa lưu (kể cả file mới tạo chưa bấm Lưu), tránh mất dữ liệu
        khi chuyển trang đi rồi quay lại."""
        if self._dirty:
            return
        h.ACCOUNT_DIR.mkdir(parents=True, exist_ok=True)
        current = self.file_cb.currentText()
        self._files = h.list_account_files()
        self.file_cb.blockSignals(True)
        self.file_cb.clear()
        self.file_cb.addItems([p.name for p in self._files])
        idx = self.file_cb.findText(current)
        self.file_cb.setCurrentIndex(idx if idx >= 0 else 0)
        self._last_index = self.file_cb.currentIndex()
        self.file_cb.blockSignals(False)
        self._load_table()

    def has_unsaved_changes(self):
        return self._dirty

    def _on_file_changed(self, index):
        if self._dirty:
            ret = QtWidgets.QMessageBox.question(
                self, "Có thay đổi chưa lưu",
                "File hiện tại có thay đổi chưa lưu. Đổi file sẽ mất thay đổi này.\n\nVẫn đổi?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if ret != QtWidgets.QMessageBox.Yes:
                self.file_cb.blockSignals(True)
                self.file_cb.setCurrentIndex(self._last_index)
                self.file_cb.blockSignals(False)
                return
        self._last_index = index
        self._dirty = False
        self._load_table()

    def _create_file(self):
        name = self.new_name_edit.text().strip()
        if not name:
            return
        if any(p.name == name for p in self._files):
            QtWidgets.QMessageBox.warning(self, "Trùng tên", "File đã tồn tại.")
            return
        # Chỉ thêm vào danh sách hiển thị — CHƯA tạo file thật trên đĩa.
        # Bấm "Lưu" mới thật sự ghi file (write_account_lines tự tạo file mới).
        self._files.append(h.ACCOUNT_DIR / name)
        self.new_name_edit.clear()
        self.file_cb.blockSignals(True)
        self.file_cb.addItem(name)
        self.file_cb.setCurrentIndex(self.file_cb.count() - 1)
        self._last_index = self.file_cb.currentIndex()
        self.file_cb.blockSignals(False)
        self.table.setRowCount(0)
        self.warn_label.setText("")
        self._dirty = True

    def _current_path(self):
        if not self._files or self.file_cb.currentIndex() < 0:
            return None
        return self._files[self.file_cb.currentIndex()]

    def _load_table(self):
        path = self._current_path()
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        if path:
            rows = h.read_account_lines(path)
            self.table.setRowCount(len(rows))
            for r, (email_addr, pwd) in enumerate(rows):
                self._set_row(r, email_addr, pwd)
        self.table.blockSignals(False)
        self._refresh_warning()

    def _set_row(self, row, email_addr, pwd):
        email_item = QtWidgets.QTableWidgetItem(email_addr)
        self.table.setItem(row, self.COL_EMAIL, email_item)

        pwd_item = QtWidgets.QTableWidgetItem()
        pwd_item.setData(QtCore.Qt.UserRole, pwd)
        show = self.show_pwd_cb.isChecked()
        pwd_item.setText(pwd if show else "•" * 8)
        if not show:
            pwd_item.setFlags(pwd_item.flags() & ~QtCore.Qt.ItemIsEditable)
        self.table.setItem(row, self.COL_PWD, pwd_item)

        prov_item = QtWidgets.QTableWidgetItem(h.provider_label(email_addr))
        prov_item.setFlags(prov_item.flags() & ~QtCore.Qt.ItemIsEditable)
        self.table.setItem(row, self.COL_PROVIDER, prov_item)

    def _toggle_pwd(self):
        show = self.show_pwd_cb.isChecked()
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, self.COL_PWD)
            if item is None:
                continue
            real = item.data(QtCore.Qt.UserRole) or ""
            item.setText(real if show else "•" * 8)
            if show:
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            else:
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
        self.table.blockSignals(False)

    def _on_item_changed(self, item):
        self._dirty = True
        row = item.row()
        if item.column() == self.COL_EMAIL:
            prov_item = self.table.item(row, self.COL_PROVIDER)
            if prov_item:
                prov_item.setText(h.provider_label(item.text().strip()))
            self._refresh_warning()
        elif item.column() == self.COL_PWD and self.show_pwd_cb.isChecked():
            item.setData(QtCore.Qt.UserRole, item.text())

    def _refresh_warning(self):
        bad = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, self.COL_EMAIL)
            email_addr = item.text().strip() if item else ""
            if email_addr and h.get_provider(email_addr) is None:
                bad.append(email_addr)
        if bad:
            self.warn_label.setText(f"⚠️ {len(bad)} email chưa được hỗ trợ (chỉ Gmail/Yahoo): {', '.join(bad)}")
        else:
            self.warn_label.setText("")

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._set_row(row, "", "")
        self._dirty = True

    def _delete_selected_rows(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for r in rows:
            self.table.removeRow(r)
        self._dirty = True

    def _save(self):
        path = self._current_path()
        if not path:
            return
        rows = []
        for r in range(self.table.rowCount()):
            email_item = self.table.item(r, self.COL_EMAIL)
            pwd_item = self.table.item(r, self.COL_PWD)
            email_addr = email_item.text().strip() if email_item else ""
            pwd = (pwd_item.data(QtCore.Qt.UserRole) if pwd_item else "") or ""
            if email_addr:
                rows.append((email_addr, pwd))
        h.write_account_lines(path, rows)
        self._dirty = False
        QtWidgets.QMessageBox.information(self, "Đã lưu", f"Đã lưu {len(rows)} account vào {path.name}")
        self.reload()


# ============================================================
# TRANG 4: CẤU HÌNH (config.ini)
# ============================================================

class ConfigPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dirty = False
        self._loading = False
        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Cấu hình (config.ini)")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #1a3a6e;")
        layout.addWidget(title)

        top = QtWidgets.QHBoxLayout()
        self.section_cb = QtWidgets.QComboBox()
        self.section_cb.currentIndexChanged.connect(self._load_section)
        top.addWidget(QtWidgets.QLabel("Section:"))
        top.addWidget(self.section_cb, 1)

        self.new_section_edit = QtWidgets.QLineEdit()
        self.new_section_edit.setPlaceholderText("PokeX")
        self.new_section_btn = QtWidgets.QPushButton("➕ Tạo section")
        self.new_section_btn.clicked.connect(self._create_section)
        top.addWidget(self.new_section_edit)
        top.addWidget(self.new_section_btn)
        layout.addLayout(top)

        self.group = QtWidgets.QGroupBox("")
        form = QtWidgets.QFormLayout(self.group)
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(16)
        self.fields = {}
        for field in h.CONFIG_FIELDS:
            edit = QtWidgets.QLineEdit()
            edit.textChanged.connect(self._mark_dirty)
            label = h.CONFIG_FIELD_LABELS.get(field, field)
            form.addRow(f"{label}:", edit)
            self.fields[field] = edit
        layout.addWidget(self.group)

        btn_row = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton("💾 Lưu section")
        save_btn.clicked.connect(self._save_section)
        del_btn = QtWidgets.QPushButton("🗑️ Xoá section")
        del_btn.clicked.connect(self._delete_section)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()

        self.reload()

    def reload(self):
        """Nạp lại từ đĩa — bỏ qua nếu đang có thay đổi chưa lưu, tránh mất dữ liệu
        khi chuyển trang đi rồi quay lại (chỉ 'Lưu section' mới thật sự ghi đĩa)."""
        if self._dirty:
            self._refresh_dropdown()
            return
        self.cfg = h.load_ini()
        self._refresh_dropdown()

    def _refresh_dropdown(self, select=None):
        current = select if select is not None else self.section_cb.currentText()
        self.section_cb.blockSignals(True)
        self.section_cb.clear()
        self.section_cb.addItems(h.job_sections(self.cfg))
        idx = self.section_cb.findText(current)
        self.section_cb.setCurrentIndex(idx if idx >= 0 else 0)
        self.section_cb.blockSignals(False)
        self._load_section()

    def _mark_dirty(self):
        if not self._loading:
            self._dirty = True

    def has_unsaved_changes(self):
        return self._dirty

    def _load_section(self):
        self._loading = True
        section = self.section_cb.currentText()
        self.group.setTitle(f"[{section}]" if section else "")
        for field, edit in self.fields.items():
            val = self.cfg[section].get(field, "") if section and section in self.cfg else ""
            edit.setText(val)
        self._loading = False

    def _create_section(self):
        name = self.new_section_edit.text().strip()
        if not name:
            return
        if name in self.cfg:
            QtWidgets.QMessageBox.warning(self, "Trùng tên", "Section đã tồn tại.")
            return
        # Chỉ thêm vào bộ nhớ — CHƯA ghi xuống đĩa. Phải bấm "Lưu section" mới lưu thật.
        self.cfg[name] = {k: "" for k in h.CONFIG_FIELDS}
        self.new_section_edit.clear()
        self._refresh_dropdown(select=name)
        self._dirty = True

    def _save_section(self):
        section = self.section_cb.currentText()
        if not section:
            return
        for field, edit in self.fields.items():
            self.cfg[section][field] = edit.text()
        h.save_ini(self.cfg)
        self._dirty = False
        QtWidgets.QMessageBox.information(self, "Đã lưu", f"Đã lưu section [{section}].")

    def _delete_section(self):
        section = self.section_cb.currentText()
        if not section:
            return
        ret = QtWidgets.QMessageBox.question(
            self, "Xác nhận xoá", f"Xoá section [{section}]?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if ret == QtWidgets.QMessageBox.Yes:
            self.cfg.remove_section(section)
            h.save_ini(self.cfg)
            self._dirty = False
            self.cfg = h.load_ini()
            self._refresh_dropdown()
