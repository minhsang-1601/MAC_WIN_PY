#!/usr/bin/env python3
"""IMAP Checker — app desktop PyQt5 (native, không cần trình duyệt).

Chạy: python3 main.py
"""
import os
import sys

from PyQt5 import QtWidgets, QtGui

from theme import APP_STYLE
from main_window import MainWindow

_ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AppIcon.png")


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    if os.path.exists(_ICON_PATH):
        app.setWindowIcon(QtGui.QIcon(_ICON_PATH))

    # ── Cổng mở app: đã đặt mật khẩu thì BẮT BUỘC nhập đúng mới vào ──
    import helpers as h
    from security import AskPasswordDialog
    if h.has_screen_password():
        if not AskPasswordDialog().exec_():
            sys.exit(0)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
