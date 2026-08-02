#!/usr/bin/env python3
"""IMAP Checker — app desktop PyQt5 (native, không cần trình duyệt).

Chạy: python3 main.py
"""
import sys

from PyQt5 import QtWidgets

from theme import APP_STYLE
from main_window import MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
