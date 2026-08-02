#!/usr/bin/env python3
from PyQt5 import QtCore, QtGui, QtWidgets

import helpers as h
from pages import DashboardPage, RunJobPage, AccountsPage, ConfigPage


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IMAP Checker")
        self.resize(1150, 760)

        self.dashboard_page = DashboardPage()
        self.run_job_page = RunJobPage()
        self.accounts_page = AccountsPage()
        self.config_page = ConfigPage()

        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.run_job_page)
        self.stack.addWidget(self.accounts_page)
        self.stack.addWidget(self.config_page)
        self.setCentralWidget(self.stack)

        self._build_toolbar()

        self.status_label = QtWidgets.QLabel(f"BASE_DIR: {h.BASE_DIR}")
        self.statusBar().addWidget(self.status_label)

    def _build_toolbar(self):
        toolbar = QtWidgets.QToolBar("Điều hướng")
        toolbar.setMovable(False)
        toolbar.setIconSize(QtCore.QSize(1, 1))
        self.addToolBar(toolbar)

        actions = [
            ("🏠 Tổng quan", 0, self._on_show_dashboard),
            ("▶️ Chạy Job", 1, self._on_show_run_job),
            ("👤 Quản lý Account", 2, self._on_show_accounts),
            ("⚙️ Cấu hình", 3, self._on_show_config),
        ]
        self._nav_actions = []
        for label, index, handler in actions:
            action = QtWidgets.QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(handler)
            toolbar.addAction(action)
            self._nav_actions.append(action)

        self._nav_actions[0].setChecked(True)

    def _select(self, index):
        self.stack.setCurrentIndex(index)
        for i, action in enumerate(self._nav_actions):
            action.setChecked(i == index)

    def _on_show_dashboard(self):
        self._select(0)
        self.dashboard_page.reload()

    def _on_show_run_job(self):
        self._select(1)
        self.run_job_page.reload()

    def _on_show_accounts(self):
        self._select(2)
        self.accounts_page.reload()

    def _on_show_config(self):
        self._select(3)
        self.config_page.reload()

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
