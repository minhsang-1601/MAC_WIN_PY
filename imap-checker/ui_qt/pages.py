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

    def __init__(self, cmd, cwd=None, extra_env=None, parent=None):
        super().__init__(parent)
        self.process = QtCore.QProcess(self)
        if cwd:
            self.process.setWorkingDirectory(cwd)
        if extra_env:
            env = QtCore.QProcessEnvironment.systemEnvironment()
            for key, val in extra_env.items():
                env.insert(key, val)
            self.process.setProcessEnvironment(env)
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

        retention_row = QtWidgets.QHBoxLayout()
        retention_row.addWidget(QtWidgets.QLabel("Giữ log:"))
        self.retention_spin = QtWidgets.QSpinBox()
        self.retention_spin.setRange(0, 3650)
        self.retention_spin.setValue(h.get_log_retention_days())
        self.retention_spin.setSuffix(" ngày (0 = không tự xoá)")
        retention_row.addWidget(self.retention_spin)
        save_retention_btn = QtWidgets.QPushButton("💾 Lưu")
        save_retention_btn.clicked.connect(self._save_retention)
        retention_row.addWidget(save_retention_btn)
        cleanup_btn = QtWidgets.QPushButton("🧹 Dọn log cũ ngay")
        cleanup_btn.clicked.connect(self._cleanup_now)
        retention_row.addWidget(cleanup_btn)
        retention_row.addStretch()
        log_layout.addLayout(retention_row)

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

    def _save_retention(self):
        h.set_log_retention_days(self.retention_spin.value())
        QtWidgets.QMessageBox.information(
            self, "Đã lưu", f"Giữ log {self.retention_spin.value()} ngày (áp dụng từ lần dọn tiếp theo)."
        )

    def _cleanup_now(self):
        deleted = h.cleanup_old_logs(self.retention_spin.value())
        QtWidgets.QMessageBox.information(self, "Đã dọn", f"Đã xoá {len(deleted)} file log cũ.")
        self.reload()

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

    def run_script(self, cmd, log_widget, run_btn, on_finished=None, extra_env=None):
        run_btn.setEnabled(False)
        log_widget.clear()
        self._runner = ProcessRunner(cmd, cwd=str(h.SCRIPTS_DIR), extra_env=extra_env)
        self._runner.output.connect(lambda s: self._append_log(log_widget, s))
        self._runner.finished.connect(lambda code: self._on_finished(code, run_btn, on_finished))
        self._runner.start()

    def run_script_queue(self, cmds, log_widget, run_btn, on_item_start=None, on_all_finished=None):
        """Chạy tuần tự nhiều lệnh, nối log liên tục. cmds: list[(label, cmd_list)]."""
        run_btn.setEnabled(False)
        log_widget.clear()
        self._queue = list(cmds)
        self._queue_log = log_widget
        self._queue_btn = run_btn
        self._queue_on_item_start = on_item_start
        self._queue_on_all_finished = on_all_finished
        self._run_next_in_queue()

    def _run_next_in_queue(self):
        if not self._queue:
            self._queue_btn.setEnabled(True)
            if self._queue_on_all_finished:
                self._queue_on_all_finished()
            return
        label, cmd = self._queue.pop(0)
        if self._queue_on_item_start:
            self._queue_on_item_start(label)
        self._runner = ProcessRunner(cmd, cwd=str(h.SCRIPTS_DIR))
        self._runner.output.connect(lambda s: self._append_log(self._queue_log, s))
        self._runner.finished.connect(lambda code: self._run_next_in_queue())
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


class EmailPickerWidget(QtWidgets.QWidget):
    """Danh sách email đánh số, có ô tìm kiếm lọc nhanh — click 1 lần để tick chọn/bỏ chọn,
    không cần giữ Cmd/Shift, chọn được nhiều dòng."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Tìm email...")
        self.search_edit.textChanged.connect(self._filter)
        layout.addWidget(self.search_edit)

        hint_row = QtWidgets.QHBoxLayout()
        hint = QtWidgets.QLabel("Click vào 1 dòng để chọn/bỏ chọn — chọn được nhiều dòng.")
        hint.setStyleSheet("color: #7a5800; font-size: 11px;")
        hint_row.addWidget(hint)
        hint_row.addStretch()
        self.selected_count_label = QtWidgets.QPushButton("Đã chọn: 0 email")
        self.selected_count_label.setCursor(QtCore.Qt.PointingHandCursor)
        self.selected_count_label.setStyleSheet(
            "QPushButton {"
            "  color: #1a3a6e; font-weight: 700; font-size: 11px;"
            "  background: #fff0a0; border: 1px solid #d4a017; border-radius: 4px;"
            "  padding: 3px 10px; min-width: 0px;"
            "}"
            "QPushButton:hover { background: #ffe87a; }"
        )
        self.selected_count_label.setToolTipDuration(15000)
        self.selected_count_label.clicked.connect(self._show_selected_popup)
        hint_row.addWidget(self.selected_count_label)
        layout.addLayout(hint_row)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setMaximumHeight(220)
        self.list_widget.itemClicked.connect(self._toggle_item)
        layout.addWidget(self.list_widget)

        self._numbered = []
        self._selected = set()
        self._update_selected_label()

    def set_emails(self, emails):
        self._numbered = list(enumerate(sorted(emails), 1))
        self._selected = set()
        self._populate(self._numbered)
        self._update_selected_label()

    def _update_selected_label(self):
        n = len(self._selected)
        self.selected_count_label.setText(f"Đã chọn: {n} email")
        if n:
            tooltip = "\n".join(sorted(self._selected))
        else:
            tooltip = "Chưa chọn email nào"
        self.selected_count_label.setToolTip(tooltip)

    def _show_selected_popup(self):
        if self._selected:
            text = "\n".join(f"• {e}" for e in sorted(self._selected))
        else:
            text = "Chưa chọn email nào."
        QtWidgets.QMessageBox.information(self, f"Đã chọn ({len(self._selected)} email)", text)

    def _populate(self, numbered_list):
        self.list_widget.clear()
        for i, email_addr in numbered_list:
            mark = "☑" if email_addr in self._selected else "☐"
            item = QtWidgets.QListWidgetItem(f"{mark}  {i}. {email_addr}")
            item.setData(QtCore.Qt.UserRole, email_addr)
            item.setData(QtCore.Qt.UserRole + 1, i)
            self.list_widget.addItem(item)

    def _toggle_item(self, item):
        email_addr = item.data(QtCore.Qt.UserRole)
        idx = item.data(QtCore.Qt.UserRole + 1)
        if email_addr in self._selected:
            self._selected.discard(email_addr)
        else:
            self._selected.add(email_addr)
        mark = "☑" if email_addr in self._selected else "☐"
        item.setText(f"{mark}  {idx}. {email_addr}")
        self._update_selected_label()

    def _filter(self, text):
        text = text.strip().lower()
        if not text:
            self._populate(self._numbered)
        else:
            self._populate([(i, e) for i, e in self._numbered if text in e.lower()])

    def selected_emails(self):
        return list(self._selected)


class CheckAllTab(BaseJobTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Chạy check_mail_all_common.py cho nhiều account theo 1 section."))

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(16)
        self.section_cb = QtWidgets.QComboBox()
        self.file_cb = QtWidgets.QComboBox()
        form.addRow("Section:", self.section_cb)
        form.addRow("File account:", self.file_cb)
        layout.addLayout(form)

        mail_row = QtWidgets.QHBoxLayout()
        self.send_cb = QtWidgets.QCheckBox("Gửi mail báo cáo sau khi xong")
        self.send_cb.setChecked(True)
        self.send_cb.toggled.connect(self._on_send_toggled)
        mail_row.addWidget(self.send_cb)

        self.from_label = QtWidgets.QLabel("Từ:")
        self.from_cb = QtWidgets.QComboBox()
        self.from_cb.setEditable(True)
        self.to_label = QtWidgets.QLabel("Đến:")
        self.to_cb = QtWidgets.QComboBox()
        self.to_cb.setEditable(True)
        mail_row.addWidget(self.from_label)
        mail_row.addWidget(self.from_cb, 1)
        mail_row.addWidget(self.to_label)
        mail_row.addWidget(self.to_cb, 1)
        layout.addLayout(mail_row)

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

        self._from_accounts = h.list_sendable_accounts()
        self._to_accounts = h.list_accounts_with_password()
        default_from, default_to = h.get_mail_config_defaults()
        self._default_from = default_from
        self._default_to = default_to

        for cb, accounts, default in [
            (self.from_cb, self._from_accounts, default_from),
            (self.to_cb, self._to_accounts, default_to),
        ]:
            cb.blockSignals(True)
            cb.clear()
            items = sorted(accounts.keys())
            if default and default not in items:
                items.insert(0, default)
            cb.addItems(items)
            if default:
                idx = cb.findText(default)
                cb.setCurrentIndex(idx if idx >= 0 else 0)
            cb.blockSignals(False)

        self._on_send_toggled()

    def _on_send_toggled(self):
        show = self.send_cb.isChecked()
        self.from_label.setVisible(show)
        self.from_cb.setVisible(show)
        self.to_label.setVisible(show)
        self.to_cb.setVisible(show)

    def _run(self):
        if not self._files or self.section_cb.count() == 0:
            QtWidgets.QMessageBox.warning(self, "Thiếu dữ liệu", "Chưa có section hoặc file account.")
            return
        section = self.section_cb.currentText()
        accounts_path = self._files[self.file_cb.currentIndex()]
        send_flag = "1" if self.send_cb.isChecked() else "0"

        extra_env = None
        if self.send_cb.isChecked():
            from_email = self.from_cb.currentText().strip()
            to_email = self.to_cb.currentText().strip()
            # Chỉ ghi đè khi khác mặc định — giữ nguyên hành vi cũ (đọc mail_account.conf)
            # nếu người dùng không đổi gì, tránh yêu cầu mật khẩu không cần thiết.
            if from_email and to_email and (from_email != self._default_from or to_email != self._default_to):
                from_pwd = self._from_accounts.get(from_email)
                if not from_pwd:
                    QtWidgets.QMessageBox.warning(
                        self, "Không gửi được",
                        f"Chưa có mật khẩu đã lưu cho '{from_email}' trong Quản lý Account — "
                        "chỉ chọn được email Gmail đã có sẵn trong danh sách account làm người gửi.",
                    )
                    return
                extra_env = {
                    "MAIL_FROM_OVERRIDE": from_email,
                    "MAIL_FROM_PASSWORD_OVERRIDE": from_pwd,
                    "MAIL_TO_OVERRIDE": to_email,
                }

        self._before = snapshot_mtimes(h.LOG_DIR)
        cmd = [h.PY_CMD, str(h.SCRIPT_CHECK_ALL), section, str(accounts_path), send_flag]
        self.run_script(cmd, self.log, self.run_btn, on_finished=self._show_results, extra_env=extra_env)

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
        layout.addWidget(QtWidgets.QLabel("Email (chọn 1 hoặc nhiều):"))

        self.email_picker = EmailPickerWidget()
        layout.addWidget(self.email_picker)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(16)
        self.section_cb = QtWidgets.QComboBox()
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

        # Email lấy từ danh sách account đã lưu (Quản lý Account) — không cần gõ tay App Password.
        self._accounts = h.list_all_accounts()
        self.email_picker.set_emails(self._accounts.keys())

    def _run(self):
        selected = self.email_picker.selected_emails()
        section = self.section_cb.currentText()
        if not selected or not section:
            QtWidgets.QMessageBox.warning(self, "Thiếu dữ liệu", "Chọn ít nhất 1 email và Section.")
            return
        cmds = []
        for email_addr in selected:
            pwd = self._accounts.get(email_addr, "")
            cmd = [h.PY_CMD, str(self.script_path), email_addr, pwd, section]
            cmds.append((email_addr, cmd))
        self.run_script_queue(
            cmds, self.log, self.run_btn,
            on_item_start=lambda label: self._append_log(self.log, f"\n===== {label} =====\n"),
        )


class CleanMailTab(BaseJobTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tmp_path = None
        layout = QtWidgets.QVBoxLayout(self)

        warn = QtWidgets.QLabel("⚠️ Thao tác này XOÁ VĨNH VIỄN email trong hộp thư, không thể hoàn tác.")
        warn.setStyleSheet("color: #b00000; font-weight: 700;")
        layout.addWidget(warn)

        mode_row = QtWidgets.QHBoxLayout()
        self.mode_file_rb = QtWidgets.QRadioButton("Theo file account")
        self.mode_file_rb.setChecked(True)
        self.mode_email_rb = QtWidgets.QRadioButton("Theo email tự chọn")
        self.mode_file_rb.toggled.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_file_rb)
        mode_row.addWidget(self.mode_email_rb)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # ---- Chế độ 1: theo file account ----
        self.file_mode_widget = QtWidgets.QWidget()
        file_form = QtWidgets.QFormLayout(self.file_mode_widget)
        file_form.setContentsMargins(0, 0, 0, 0)
        file_form.setLabelAlignment(QtCore.Qt.AlignLeft)
        file_form.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        file_form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        file_form.setHorizontalSpacing(16)
        self.file_cb = QtWidgets.QComboBox()
        file_form.addRow("File account sẽ dọn:", self.file_cb)
        layout.addWidget(self.file_mode_widget)

        # ---- Chế độ 2: theo email tự chọn (đánh số, tìm kiếm, chọn nhiều) ----
        self.email_mode_widget = QtWidgets.QWidget()
        email_layout = QtWidgets.QVBoxLayout(self.email_mode_widget)
        email_layout.setContentsMargins(0, 0, 0, 0)
        email_layout.addWidget(QtWidgets.QLabel("Chọn email cần dọn:"))
        self.email_picker = EmailPickerWidget()
        email_layout.addWidget(self.email_picker)
        layout.addWidget(self.email_mode_widget)
        self.email_mode_widget.setVisible(False)

        # ---- Số tháng — dùng chung cho cả 2 chế độ ----
        months_form = QtWidgets.QFormLayout()
        months_form.setLabelAlignment(QtCore.Qt.AlignLeft)
        months_form.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        months_form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        months_form.setHorizontalSpacing(16)
        self.months_spin = QtWidgets.QSpinBox()
        self.months_spin.setRange(0, 120)
        self.months_spin.setValue(12)
        self.months_spin.setSuffix(" tháng (0 = xoá TOÀN BỘ)")
        months_form.addRow("Xoá email cũ hơn:", self.months_spin)
        layout.addLayout(months_form)

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

    def _on_mode_changed(self):
        is_file_mode = self.mode_file_rb.isChecked()
        self.file_mode_widget.setVisible(is_file_mode)
        self.email_mode_widget.setVisible(not is_file_mode)

    def reload_options(self):
        self.file_cb.clear()
        self._files = h.list_account_files()
        for p in self._files:
            n = len(h.read_account_lines(p))
            self.file_cb.addItem(f"{p.name} ({n} account)")

        self._accounts = h.list_all_accounts()
        self.email_picker.set_emails(self._accounts.keys())

    def _update_enabled(self):
        ok = self.confirm_edit.text().strip().upper() == "XOA" and self.confirm_cb.isChecked()
        self.run_btn.setEnabled(ok)

    def _run(self):
        if self.mode_file_rb.isChecked():
            if not self._files:
                return
            fname = self._files[self.file_cb.currentIndex()].name
            cmd = [h.PY_CMD, str(h.SCRIPT_CLEAN), fname, str(self.months_spin.value())]
            self.run_script(cmd, self.log, self.run_btn)
        else:
            selected = self.email_picker.selected_emails()
            if not selected:
                QtWidgets.QMessageBox.warning(self, "Chưa chọn", "Chưa chọn email nào để dọn.")
                return
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            tmp_name = f"_tmp_clean_{ts}.txt"
            tmp_path = h.ACCOUNT_DIR / tmp_name
            with open(tmp_path, "w", encoding="utf-8") as f:
                for email_addr in selected:
                    f.write(f"{email_addr},{self._accounts.get(email_addr, '')}\n")
            self._tmp_path = tmp_path
            cmd = [h.PY_CMD, str(h.SCRIPT_CLEAN), tmp_name, str(self.months_spin.value())]
            self.run_script(cmd, self.log, self.run_btn, on_finished=self._cleanup_tmp)

    def _cleanup_tmp(self, code):
        if self._tmp_path and self._tmp_path.exists():
            self._tmp_path.unlink()
        self._tmp_path = None


class ScheduleTab(BaseJobTab):
    """Lên lịch chạy tự động bằng launchd (macOS) — chạy đúng giờ kể cả khi tắt app."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)

        info = QtWidgets.QLabel(
            "⏰ Lên lịch chạy tự động bằng launchd (macOS) — chạy đúng giờ hàng ngày kể cả khi đã tắt app."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(16)

        self.job_type_cb = QtWidgets.QComboBox()
        self.job_type_cb.addItems(["Check hàng loạt", "Dọn mail"])
        self.job_type_cb.currentIndexChanged.connect(self._on_job_type_changed)
        form.addRow("Loại job:", self.job_type_cb)

        self.section_label = QtWidgets.QLabel("Section:")
        self.section_cb = QtWidgets.QComboBox()
        form.addRow(self.section_label, self.section_cb)

        self.file_cb = QtWidgets.QComboBox()
        form.addRow("File account:", self.file_cb)

        self.send_cb = QtWidgets.QCheckBox("Gửi mail báo cáo sau khi xong")
        self.send_cb.setChecked(True)
        self.send_cb.toggled.connect(self._update_mail_visibility)
        form.addRow("", self.send_cb)

        self.mail_label = QtWidgets.QLabel("Gửi báo cáo:")
        mail_row = QtWidgets.QHBoxLayout()
        self.from_label = QtWidgets.QLabel("Từ:")
        self.from_cb = QtWidgets.QComboBox()
        self.from_cb.setEditable(True)
        self.to_label = QtWidgets.QLabel("Đến:")
        self.to_cb = QtWidgets.QComboBox()
        self.to_cb.setEditable(True)
        mail_row.addWidget(self.from_label)
        mail_row.addWidget(self.from_cb, 1)
        mail_row.addWidget(self.to_label)
        mail_row.addWidget(self.to_cb, 1)
        self.mail_widget = QtWidgets.QWidget()
        self.mail_widget.setLayout(mail_row)
        form.addRow(self.mail_label, self.mail_widget)

        self.months_label = QtWidgets.QLabel("Xoá email cũ hơn:")
        self.months_spin = QtWidgets.QSpinBox()
        self.months_spin.setRange(0, 120)
        self.months_spin.setValue(12)
        self.months_spin.setSuffix(" tháng (0 = xoá TOÀN BỘ)")
        form.addRow(self.months_label, self.months_spin)

        self.repeat_cb = QtWidgets.QComboBox()
        self.repeat_cb.addItems(["Hàng ngày", "Theo thứ trong tuần", "Theo ngày trong tháng"])
        self.repeat_cb.currentIndexChanged.connect(self._on_repeat_changed)
        form.addRow("Kiểu lặp:", self.repeat_cb)

        self.weekday_label = QtWidgets.QLabel("Chọn thứ:")
        weekday_row = QtWidgets.QHBoxLayout()
        self.weekday_checks = {}
        for wd, name in [(1, "T2"), (2, "T3"), (3, "T4"), (4, "T5"), (5, "T6"), (6, "T7"), (7, "CN")]:
            cb = QtWidgets.QCheckBox(name)
            self.weekday_checks[wd] = cb
            weekday_row.addWidget(cb)
        weekday_row.addStretch()
        self.weekday_widget = QtWidgets.QWidget()
        self.weekday_widget.setLayout(weekday_row)
        form.addRow(self.weekday_label, self.weekday_widget)

        self.day_of_month_label = QtWidgets.QLabel("Chọn ngày:")
        day_grid = QtWidgets.QGridLayout()
        day_grid.setSpacing(4)
        self.day_of_month_checks = {}
        for day in range(1, 32):
            cb = QtWidgets.QCheckBox(str(day))
            self.day_of_month_checks[day] = cb
            row, col = divmod(day - 1, 7)
            day_grid.addWidget(cb, row, col)
        self.day_of_month_widget = QtWidgets.QWidget()
        self.day_of_month_widget.setLayout(day_grid)
        form.addRow(self.day_of_month_label, self.day_of_month_widget)

        self.time_edit = QtWidgets.QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QtCore.QTime(9, 0))
        form.addRow("Giờ chạy:", self.time_edit)

        layout.addLayout(form)

        add_btn = QtWidgets.QPushButton("➕ Thêm lịch")
        add_btn.clicked.connect(self._add_schedule)
        layout.addWidget(add_btn)

        layout.addWidget(QtWidgets.QLabel("📋 Các lịch đã đặt:"))
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Giờ chạy", "Loại job", "Chi tiết", "Thao tác"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        self.table.setColumnWidth(3, 220)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setMinimumHeight(220)
        self.table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.table.verticalHeader().setDefaultSectionSize(44)
        layout.addWidget(self.table, 1)

        self.log = self.make_log_panel()
        layout.addWidget(self.log)

        self._schedules = []
        self._on_job_type_changed()
        self._on_repeat_changed()
        self.reload_options()

    def _on_repeat_changed(self):
        idx = self.repeat_cb.currentIndex()
        is_weekly = idx == 1
        is_monthly = idx == 2
        self.weekday_label.setVisible(is_weekly)
        self.weekday_widget.setVisible(is_weekly)
        self.day_of_month_label.setVisible(is_monthly)
        self.day_of_month_widget.setVisible(is_monthly)

    def _on_job_type_changed(self):
        is_check_all = self.job_type_cb.currentIndex() == 0
        self.section_label.setVisible(is_check_all)
        self.section_cb.setVisible(is_check_all)
        self.send_cb.setVisible(is_check_all)
        self.months_label.setVisible(not is_check_all)
        self.months_spin.setVisible(not is_check_all)
        self._update_mail_visibility()

    def _update_mail_visibility(self):
        show = self.job_type_cb.currentIndex() == 0 and self.send_cb.isChecked()
        self.mail_label.setVisible(show)
        self.mail_widget.setVisible(show)

    def reload_options(self):
        cfg = h.load_ini()
        self.section_cb.clear()
        self.section_cb.addItems(h.job_sections(cfg))

        self.file_cb.clear()
        self._files = h.list_account_files()
        for p in self._files:
            n = len(h.read_account_lines(p))
            self.file_cb.addItem(f"{p.name} ({n} account)")

        self._from_accounts = h.list_sendable_accounts()
        self._to_accounts = h.list_accounts_with_password()
        default_from, default_to = h.get_mail_config_defaults()
        self._default_from = default_from
        self._default_to = default_to
        for cb, accounts, default in [
            (self.from_cb, self._from_accounts, default_from),
            (self.to_cb, self._to_accounts, default_to),
        ]:
            cb.blockSignals(True)
            cb.clear()
            items = sorted(accounts.keys())
            if default and default not in items:
                items.insert(0, default)
            cb.addItems(items)
            if default:
                idx = cb.findText(default)
                cb.setCurrentIndex(idx if idx >= 0 else 0)
            cb.blockSignals(False)

        self._schedules = h.load_schedules()
        self._refresh_table()

    WEEKDAY_NAMES = {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}

    def _repeat_text(self, sch):
        repeat = sch.get("repeat", "daily")
        if repeat == "weekly":
            names = [self.WEEKDAY_NAMES.get(wd, str(wd)) for wd in sch.get("weekdays", [])]
            return f"{sch['time']} ({','.join(names)})"
        if repeat == "monthly":
            days = ",".join(str(d) for d in sch.get("days_of_month", []))
            return f"{sch['time']} (ngày {days} hàng tháng)"
        return f"{sch['time']} (hàng ngày)"

    def _refresh_table(self):
        self.table.setRowCount(len(self._schedules))
        for row, sch in enumerate(self._schedules):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(self._repeat_text(sch)))
            if sch["job_type"] == "check_all":
                label = "Check hàng loạt"
                p = sch["params"]
                detail = f"Section {p['section']} — {p['file']}"
                if p.get("send_flag") == "1":
                    if sch.get("mail_from") and sch.get("mail_to"):
                        detail += f" — gửi từ {sch['mail_from']} đến {sch['mail_to']}"
                    else:
                        detail += " — gửi mail báo cáo"
            else:
                label = "Dọn mail"
                p = sch["params"]
                months = int(p["months"])
                detail = f"{p['file']} — " + (f"giữ {months} tháng" if months else "xoá TOÀN BỘ")
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(label))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(detail))

            action_widget = QtWidgets.QWidget()
            action_layout = QtWidgets.QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(8)
            run_now_btn = QtWidgets.QPushButton("▶️ Chạy thử")
            run_now_btn.setStyleSheet("QPushButton { padding: 2px 8px; min-width: 0px; }")
            run_now_btn.clicked.connect(lambda _, s=sch, b=run_now_btn: self._run_now(s, b))
            del_btn = QtWidgets.QPushButton("🗑️ Xoá")
            del_btn.setStyleSheet(
                "QPushButton { background: #b00000; border-color: #7a0000; color: #ffffff;"
                "  padding: 2px 8px; min-width: 0px; }"
                "QPushButton:hover { background: #d40000; border-color: #ff8080; color: #ffe8e8; }"
            )
            del_btn.clicked.connect(lambda _, sid=sch["id"]: self._delete_schedule(sid))
            action_layout.addWidget(run_now_btn)
            action_layout.addWidget(del_btn)
            self.table.setCellWidget(row, 3, action_widget)

    def _schedule_signature(self, sch):
        """Chữ ký để so trùng lịch: cùng giờ + kiểu lặp + loại job + chi tiết + FROM/TO y hệt."""
        return (
            sch.get("job_type"),
            sch.get("time"),
            sch.get("repeat", "daily"),
            tuple(sorted(sch.get("weekdays", []))),
            tuple(sorted(sch.get("days_of_month", []))),
            tuple(sorted(sch.get("params", {}).items())),
            sch.get("mail_from"),
            sch.get("mail_to"),
        )

    def _add_schedule(self):
        time_str = self.time_edit.time().toString("HH:mm")
        if not self._files:
            QtWidgets.QMessageBox.warning(self, "Thiếu dữ liệu", "Chưa có file account nào.")
            return
        fname = self._files[self.file_cb.currentIndex()].name

        repeat_idx = self.repeat_cb.currentIndex()
        repeat = ["daily", "weekly", "monthly"][repeat_idx]
        extra = {"repeat": repeat}
        if repeat == "weekly":
            weekdays = [wd for wd, cb in self.weekday_checks.items() if cb.isChecked()]
            if not weekdays:
                QtWidgets.QMessageBox.warning(self, "Thiếu dữ liệu", "Chưa chọn thứ nào trong tuần.")
                return
            extra["weekdays"] = weekdays
        elif repeat == "monthly":
            days_of_month = [d for d, cb in self.day_of_month_checks.items() if cb.isChecked()]
            if not days_of_month:
                QtWidgets.QMessageBox.warning(self, "Thiếu dữ liệu", "Chưa chọn ngày nào trong tháng.")
                return
            extra["days_of_month"] = days_of_month

        if self.job_type_cb.currentIndex() == 0:
            if self.section_cb.count() == 0:
                QtWidgets.QMessageBox.warning(self, "Thiếu dữ liệu", "Chưa có section nào.")
                return
            if self.send_cb.isChecked():
                from_email = self.from_cb.currentText().strip()
                to_email = self.to_cb.currentText().strip()
                if from_email and to_email and (from_email != self._default_from or to_email != self._default_to):
                    from_pwd = self._from_accounts.get(from_email)
                    if not from_pwd:
                        QtWidgets.QMessageBox.warning(
                            self, "Không đặt được lịch",
                            f"Chưa có mật khẩu đã lưu cho '{from_email}' — chỉ chọn được email Gmail "
                            "đã có sẵn trong danh sách account làm người gửi.",
                        )
                        return
                    extra["mail_from"] = from_email
                    extra["mail_from_password"] = from_pwd
                    extra["mail_to"] = to_email
            schedule = {
                "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                "job_type": "check_all",
                "time": time_str,
                **extra,
                "params": {
                    "section": self.section_cb.currentText(),
                    "file": fname,
                    "send_flag": "1" if self.send_cb.isChecked() else "0",
                },
            }
        else:
            schedule = {
                "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                "job_type": "clean",
                "time": time_str,
                **extra,
                "params": {"file": fname, "months": self.months_spin.value()},
            }

        new_sig = self._schedule_signature(schedule)
        if any(self._schedule_signature(s) == new_sig for s in self._schedules):
            QtWidgets.QMessageBox.warning(
                self, "Trùng lịch",
                "Đã có lịch giống hệt (cùng giờ, kiểu lặp, loại job và chi tiết). Không thêm trùng.",
            )
            return

        try:
            h.install_schedule(schedule)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Lỗi", f"Không tạo được lịch chạy: {e}")
            return

        self._schedules.append(schedule)
        h.save_schedules(self._schedules)
        self._refresh_table()
        QtWidgets.QMessageBox.information(self, "Đã thêm", f"Đã đặt lịch: {self._repeat_text(schedule)}.")

    def _delete_schedule(self, schedule_id):
        ret = QtWidgets.QMessageBox.question(
            self, "Xác nhận xoá", "Xoá lịch chạy này?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if ret != QtWidgets.QMessageBox.Yes:
            return
        h.uninstall_schedule(schedule_id)
        self._schedules = [s for s in self._schedules if s["id"] != schedule_id]
        h.save_schedules(self._schedules)
        self._refresh_table()

    def _run_now(self, schedule, button):
        cmd = h.build_schedule_command(schedule)
        extra_env = None
        if schedule.get("mail_from") and schedule.get("mail_from_password") and schedule.get("mail_to"):
            extra_env = {
                "MAIL_FROM_OVERRIDE": schedule["mail_from"],
                "MAIL_FROM_PASSWORD_OVERRIDE": schedule["mail_from_password"],
                "MAIL_TO_OVERRIDE": schedule["mail_to"],
            }
        self.run_script(cmd, self.log, button, extra_env=extra_env)


class RunJobPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Chạy Job")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #1a3a6e;")
        layout.addWidget(title)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setElideMode(QtCore.Qt.ElideNone)
        self.tab_all = CheckAllTab()
        self.tab_one = SingleAccountTab(h.SCRIPT_CHECK_ONE, "Chạy check_gmail_common.py — tìm mail khớp keyword cho 1 account.")
        self.tab_body = SingleAccountTab(h.SCRIPT_GETBODY, "Chạy getbody_mail_common.py — in toàn bộ nội dung mail khớp section.")
        self.tab_clean = CleanMailTab()
        self.tab_schedule = ScheduleTab()

        self.tabs.addTab(self.tab_all, "📚 Check hàng loạt")
        self.tabs.addTab(self.tab_one, "✉️ Check 1 account")
        self.tabs.addTab(self.tab_body, "📄 Xem full mail")
        self.tabs.addTab(self.tab_clean, "🧹 Dọn mail (xoá)")
        self.tabs.addTab(self.tab_schedule, "⏰ Lên lịch")
        layout.addWidget(self.tabs)

    def reload(self):
        self.tab_all.reload_options()
        self.tab_one.reload_options()
        self.tab_body.reload_options()
        self.tab_clean.reload_options()
        self.tab_schedule.reload_options()


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
        self.del_file_btn = QtWidgets.QPushButton("🗑️ Xoá file")
        self.del_file_btn.clicked.connect(self._delete_file)
        top.addWidget(self.new_name_edit)
        top.addWidget(self.new_file_btn)
        top.addWidget(self.del_file_btn)
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

    def _delete_file(self):
        path = self._current_path()
        if not path:
            return
        if path.exists():
            ret = QtWidgets.QMessageBox.question(
                self, "Xác nhận xoá",
                f"Xoá vĩnh viễn file '{path.name}' ({len(h.read_account_lines(path))} account)?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if ret != QtWidgets.QMessageBox.Yes:
                return
            path.unlink()
        self._dirty = False
        self.reload()

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
