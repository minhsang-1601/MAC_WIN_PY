#!/usr/bin/env python3
"""Hộp thoại đặt / nhập / khôi phục mật khẩu màn hình.

Mật khẩu chỉ là cổng truy cập (SHA-256) — KHÔNG mã hoá file account, nên
launchd/script vẫn chạy nền bình thường. Khi đặt mật khẩu, app sinh một
Recovery Key hiển thị MỘT LẦN; quên mật khẩu thì nhập Recovery Key để đặt lại.
"""
from PyQt5 import QtCore, QtWidgets

import helpers as h


def show_recovery_key(parent, key):
    """Hiển thị mã khôi phục MỘT LẦN để người dùng lưu lại (chọn/sao chép được)."""
    dlg = QtWidgets.QDialog(parent)
    dlg.setWindowTitle("Mã khôi phục — LƯU LẠI NGAY")
    dlg.setMinimumWidth(460)
    v = QtWidgets.QVBoxLayout(dlg)
    note = QtWidgets.QLabel(
        "⚠️ Đây là MÃ KHÔI PHỤC mật khẩu. Chỉ hiện MỘT LẦN.\n"
        "Hãy chép và cất nơi an toàn. Quên mật khẩu → dùng mã này để đặt lại.")
    note.setWordWrap(True)
    v.addWidget(note)
    field = QtWidgets.QLineEdit(key)
    field.setReadOnly(True)
    field.setStyleSheet("font-size:18px; font-weight:700; letter-spacing:2px;")
    field.setAlignment(QtCore.Qt.AlignCenter)
    v.addWidget(field)
    copy_btn = QtWidgets.QPushButton("📋 Sao chép mã")
    copy_btn.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(key))
    v.addWidget(copy_btn)
    btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
    btns.button(QtWidgets.QDialogButtonBox.Ok).setText("Tôi đã lưu mã")
    btns.accepted.connect(dlg.accept)
    v.addWidget(btns)
    dlg.exec_()


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
            "Mật khẩu này KHÔNG mã hoá file account — chỉ chặn mở app.\n"
            "Sau khi đặt, app sẽ hiện MÃ KHÔI PHỤC — hãy lưu lại."
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
        recovery = h.set_password_with_recovery(p1)
        show_recovery_key(self, recovery)
        self.accept()

    def closeEvent(self, event):
        if self._force and not h.has_screen_password():
            event.ignore()
        else:
            super().closeEvent(event)


class RecoveryDialog(QtWidgets.QDialog):
    """Quên mật khẩu: nhập Mã khôi phục + đặt mật khẩu mới."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quên mật khẩu — khôi phục")
        self.setMinimumWidth(440)

        v = QtWidgets.QVBoxLayout(self)
        v.addWidget(QtWidgets.QLabel(
            "Nhập MÃ KHÔI PHỤC đã lưu khi đặt mật khẩu, rồi đặt mật khẩu mới:"))

        form = QtWidgets.QFormLayout()
        self.key_edit = QtWidgets.QLineEdit()
        self.key_edit.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.pwd1 = QtWidgets.QLineEdit()
        self.pwd1.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pwd2 = QtWidgets.QLineEdit()
        self.pwd2.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("Mã khôi phục:", self.key_edit)
        form.addRow("Mật khẩu mới:", self.pwd1)
        form.addRow("Nhập lại:", self.pwd2)
        v.addLayout(form)

        self.err = QtWidgets.QLabel("")
        self.err.setStyleSheet("color:#b00000;")
        self.err.setWordWrap(True)
        v.addWidget(self.err)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.button(QtWidgets.QDialogButtonBox.Ok).setText("Đặt lại mật khẩu")
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        v.addWidget(btns)

    def _on_ok(self):
        if not h.verify_recovery_key(self.key_edit.text()):
            self.err.setText("Mã khôi phục không đúng.")
            return
        p1, p2 = self.pwd1.text(), self.pwd2.text()
        if len(p1) < 4:
            self.err.setText("Mật khẩu tối thiểu 4 ký tự.")
            return
        if p1 != p2:
            self.err.setText("Hai ô mật khẩu không khớp.")
            return
        recovery = h.set_password_with_recovery(p1)
        show_recovery_key(self, recovery)  # mã mới thay mã cũ
        self.accept()


class AskPasswordDialog(QtWidgets.QDialog):
    """Nhập mật khẩu để mở app khi khởi động. Sai/huỷ → không accept.
    Có 'Quên mật khẩu?' để khôi phục bằng Recovery Key."""

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

        forgot = QtWidgets.QPushButton("Quên mật khẩu?")
        forgot.setFlat(True)
        forgot.setStyleSheet("color:#1a3a6e; text-decoration:underline; border:none;")
        forgot.setCursor(QtCore.Qt.PointingHandCursor)
        forgot.clicked.connect(self._forgot)
        layout.addWidget(forgot, alignment=QtCore.Qt.AlignLeft)

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

    def _forgot(self):
        if not h.has_recovery_key():
            QtWidgets.QMessageBox.warning(
                self, "Không có mã khôi phục",
                "Mật khẩu này được đặt ở bản cũ chưa có mã khôi phục. Xoá dòng "
                "screen_password trong context/config.ini để đặt lại.")
            return
        if RecoveryDialog(self).exec_():
            # Đã đặt mật khẩu mới → vào app luôn.
            self.accept()
