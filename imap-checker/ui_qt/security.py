#!/usr/bin/env python3
"""Hộp thoại đặt / nhập mật khẩu màn hình (cổng mở app + khoá màn hình).

Mật khẩu chỉ là cổng truy cập (SHA-256) — KHÔNG mã hoá file account, nên
launchd/script vẫn chạy nền bình thường.
"""
from PyQt5 import QtCore, QtWidgets

import helpers as h


class SetPasswordDialog(QtWidgets.QDialog):
    """Đặt (hoặc đổi) mật khẩu màn hình. force=True: không cho huỷ."""

    def __init__(self, parent=None, force=False):
        super().__init__(parent)
        self._force = force
        self.setWindowTitle("Đặt mật khẩu màn hình")
        self.setMinimumWidth(420)
        if force:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)

        layout = QtWidgets.QVBoxLayout(self)
        note = QtWidgets.QLabel(
            "App cần mật khẩu để bảo vệ màn hình sử dụng.\n"
            "Mật khẩu này KHÔNG mã hoá file account — chỉ chặn mở app."
            if force else "Nhập mật khẩu mới cho màn hình.")
        note.setWordWrap(True)
        layout.addWidget(note)

        form = QtWidgets.QFormLayout()
        self.pwd1 = QtWidgets.QLineEdit()
        self.pwd1.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pwd2 = QtWidgets.QLineEdit()
        self.pwd2.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("Mật khẩu:", self.pwd1)
        form.addRow("Nhập lại:", self.pwd2)
        layout.addLayout(form)

        self.err = QtWidgets.QLabel("")
        self.err.setStyleSheet("color:#b00000;")
        self.err.setWordWrap(True)
        layout.addWidget(self.err)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        if not force:
            btns.addButton(QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_ok(self):
        p1, p2 = self.pwd1.text(), self.pwd2.text()
        if len(p1) < 4:
            self.err.setText("Mật khẩu tối thiểu 4 ký tự.")
            return
        if p1 != p2:
            self.err.setText("Hai ô mật khẩu không khớp.")
            return
        h.set_screen_password(p1)
        self.accept()

    def closeEvent(self, event):
        if self._force and not h.has_screen_password():
            event.ignore()
        else:
            super().closeEvent(event)


class AskPasswordDialog(QtWidgets.QDialog):
    """Nhập mật khẩu để mở app khi khởi động. Sai/huỷ → không accept."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nhập mật khẩu")
        self.setMinimumWidth(360)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Nhập mật khẩu để mở app:"))
        self.pwd = QtWidgets.QLineEdit()
        self.pwd.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pwd.returnPressed.connect(self._on_ok)
        layout.addWidget(self.pwd)

        self.err = QtWidgets.QLabel("")
        self.err.setStyleSheet("color:#b00000;")
        layout.addWidget(self.err)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_ok(self):
        if h.verify_screen_password(self.pwd.text()):
            self.accept()
        else:
            self.err.setText("Sai mật khẩu.")
            self.pwd.clear()
            self.pwd.setFocus()
