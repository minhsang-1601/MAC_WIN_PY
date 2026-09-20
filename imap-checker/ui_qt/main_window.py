#!/usr/bin/env python3
import time

from PyQt5 import QtCore, QtGui, QtWidgets

import helpers as h
from pages import DashboardPage, RunJobPage, AccountsPage, ConfigPage
from security import SetPasswordDialog


class MainWindow(QtWidgets.QMainWindow):
    # Chỉ số trang trong QStackedWidget
    IDX_DASHBOARD, IDX_RUNJOB, IDX_ACCOUNTS, IDX_CONFIG, IDX_LOCK = 0, 1, 2, 3, 4

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IMAP Checker")
        self.resize(1150, 760)

        try:
            h.cleanup_old_logs()
        except Exception:
            pass

        self.dashboard_page = DashboardPage()
        self.run_job_page = RunJobPage()
        self.accounts_page = AccountsPage()
        self.config_page = ConfigPage()
        # Lưu danh sách gốc xong mà chưa có mật khẩu → bắt buộc đặt.
        self.accounts_page.master_saved.connect(self.enforce_password_after_save)

        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self.dashboard_page)   # 0
        self.stack.addWidget(self.run_job_page)     # 1
        self.stack.addWidget(self.accounts_page)    # 2
        self.stack.addWidget(self.config_page)      # 3
        self.stack.addWidget(self._build_lock_page())  # 4
        self.setCentralWidget(self.stack)

        self._build_toolbar()

        self.status_label = QtWidgets.QLabel(f"BASE_DIR: {h.BASE_DIR}")
        self.statusBar().addWidget(self.status_label)

        # ── Tự khoá khi rảnh ──
        self._locked = False
        self._last_active = time.time()
        QtWidgets.QApplication.instance().installEventFilter(self)
        self._lock_timer = QtCore.QTimer(self)
        self._lock_timer.timeout.connect(self._check_auto_lock)
        self._lock_timer.start(5000)  # kiểm mỗi 5s

    # ============================================================
    # Toolbar
    # ============================================================
    def _build_toolbar(self):
        toolbar = QtWidgets.QToolBar("Điều hướng")
        toolbar.setMovable(False)
        toolbar.setIconSize(QtCore.QSize(1, 1))
        self.addToolBar(toolbar)

        actions = [
            ("🏠 Tổng quan", self.IDX_DASHBOARD, self._on_show_dashboard),
            ("▶️ Chạy Job", self.IDX_RUNJOB, self._on_show_run_job),
            ("👤 Quản lý Account", self.IDX_ACCOUNTS, self._on_show_accounts),
            ("⚙️ Cấu hình", self.IDX_CONFIG, self._on_show_config),
        ]
        self._nav_actions = []
        for label, index, handler in actions:
            action = QtWidgets.QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(handler)
            toolbar.addAction(action)
            self._nav_actions.append(action)

        self._nav_actions[0].setChecked(True)

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        self.lock_action = QtWidgets.QAction("🔒 Khoá", self)
        self.lock_action.triggered.connect(self.lock_screen)
        toolbar.addAction(self.lock_action)
        self._toolbar = toolbar

    def _select(self, index):
        self.stack.setCurrentIndex(index)
        for i, action in enumerate(self._nav_actions):
            action.setChecked(i == index)

    def _on_show_dashboard(self):
        self._select(self.IDX_DASHBOARD)
        self.dashboard_page.reload()

    def _on_show_run_job(self):
        self._select(self.IDX_RUNJOB)
        self.run_job_page.reload()

    def _on_show_accounts(self):
        self._select(self.IDX_ACCOUNTS)
        self.accounts_page.reload()

    def _on_show_config(self):
        self._select(self.IDX_CONFIG)
        self.config_page.reload()

    # ============================================================
    # Khoá màn hình
    # ============================================================
    def _build_lock_page(self):
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)
        outer.addStretch()
        box = QtWidgets.QVBoxLayout()
        box.setAlignment(QtCore.Qt.AlignHCenter)

        icon = QtWidgets.QLabel("🔒")
        icon.setStyleSheet("font-size: 64px;")
        icon.setAlignment(QtCore.Qt.AlignCenter)
        box.addWidget(icon)

        title = QtWidgets.QLabel("Màn hình đang khoá")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color:#1a3a6e;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        box.addWidget(title)

        self._lock_pwd = QtWidgets.QLineEdit()
        self._lock_pwd.setEchoMode(QtWidgets.QLineEdit.Password)
        self._lock_pwd.setPlaceholderText("Nhập mật khẩu để mở khoá")
        self._lock_pwd.setMaximumWidth(320)
        self._lock_pwd.setAlignment(QtCore.Qt.AlignCenter)
        self._lock_pwd.returnPressed.connect(self._try_unlock)
        box.addWidget(self._lock_pwd, alignment=QtCore.Qt.AlignHCenter)

        self._lock_err = QtWidgets.QLabel("")
        self._lock_err.setStyleSheet("color:#b00000;")
        self._lock_err.setAlignment(QtCore.Qt.AlignCenter)
        box.addWidget(self._lock_err)

        unlock_btn = QtWidgets.QPushButton("🔓 Mở khoá")
        unlock_btn.setMaximumWidth(200)
        unlock_btn.clicked.connect(self._try_unlock)
        box.addWidget(unlock_btn, alignment=QtCore.Qt.AlignHCenter)

        outer.addLayout(box)
        outer.addStretch()
        return page

    def lock_screen(self):
        if not h.has_screen_password():
            QtWidgets.QMessageBox.information(
                self, "Chưa có mật khẩu",
                "Chưa đặt mật khẩu màn hình. Vào 👤 Quản lý Account lưu danh "
                "sách gốc để đặt mật khẩu, hoặc đặt trong ⚙️ Cấu hình.")
            return
        self._locked = True
        self._toolbar.setVisible(False)
        self._lock_err.setText("")
        self._lock_pwd.clear()
        self.stack.setCurrentIndex(self.IDX_LOCK)
        self._lock_pwd.setFocus()

    def _try_unlock(self):
        if h.verify_screen_password(self._lock_pwd.text()):
            self._locked = False
            self._last_active = time.time()
            self._toolbar.setVisible(True)
            self._lock_pwd.clear()
            self._select(self.IDX_DASHBOARD)
            self.dashboard_page.reload()
        else:
            self._lock_err.setText("Sai mật khẩu.")
            self._lock_pwd.clear()

    def _check_auto_lock(self):
        if self._locked or not h.has_screen_password():
            return
        minutes = h.get_auto_lock_minutes()
        if minutes <= 0:
            return
        if time.time() - self._last_active >= minutes * 60:
            self.lock_screen()

    def eventFilter(self, obj, event):
        if event.type() in (
            QtCore.QEvent.MouseMove, QtCore.QEvent.KeyPress,
            QtCore.QEvent.MouseButtonPress, QtCore.QEvent.Wheel,
        ):
            self._last_active = time.time()
        return super().eventFilter(obj, event)

    def enforce_password_after_save(self):
        """Sau khi lưu danh sách gốc mà chưa có mật khẩu → bắt buộc đặt."""
        if h.has_screen_password():
            return
        dlg = SetPasswordDialog(self, force=True)
        dlg.exec_()

    # ============================================================
    def closeEvent(self, event):
        unsaved = []
        if self.config_page.has_unsaved_changes():
            unsaved.append("Cấu hình")
        if self.accounts_page.has_unsaved_changes():
            unsaved.append("Quản lý Account")

        if unsaved:
            ret = QtWidgets.QMessageBox.warning(
                self,
                "Có thay đổi chưa lưu",
                f"Trang {', '.join(unsaved)} có thay đổi chưa lưu. "
                "Đóng cửa sổ sẽ mất thay đổi này.\n\nVẫn đóng?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Cancel,
            )
            if ret != QtWidgets.QMessageBox.Yes:
                event.ignore()
                return
        event.accept()
