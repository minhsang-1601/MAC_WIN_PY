#!/bin/bash
# Build IMAP Checker (PyQt5) thành app macOS bằng Nuitka (arm64 / chip M).
# Chạy từ thư mục ui_qt/:  ./build_macos.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

source .venv/bin/activate
if ! python -c "import nuitka" 2>/dev/null; then
  pip install -q nuitka ordered-set zstandard
fi

PRODUCT_DIR="$SCRIPT_DIR/Product"
mkdir -p "$PRODUCT_DIR"

echo "🔨 Bắt đầu build bằng Nuitka..."

python -m nuitka \
  --standalone \
  --macos-create-app-bundle \
  --macos-app-name="IMAP Checker" \
  --macos-app-mode=gui \
  --enable-plugin=pyqt5 \
  --nofollow-import-to=PyQt5.QtQuick \
  --nofollow-import-to=PyQt5.QtQml \
  --nofollow-import-to=PyQt5.QtWebEngine \
  --nofollow-import-to=PyQt5.QtWebEngineCore \
  --nofollow-import-to=PyQt5.QtWebEngineWidgets \
  --nofollow-import-to=PyQt5.QtMultimedia \
  --nofollow-import-to=PyQt5.QtNetwork \
  --nofollow-import-to=PyQt5.QtTest \
  --assume-yes-for-downloads \
  --output-dir="$PRODUCT_DIR" \
  --remove-output \
  --company-name="IMAP Checker" \
  --product-name="IMAP Checker" \
  --product-version=1.0.0 \
  main.py

echo ""
if [ -d "$PRODUCT_DIR/main.app" ]; then
  rm -rf "$PRODUCT_DIR/IMAP Checker.app"
  mv "$PRODUCT_DIR/main.app" "$PRODUCT_DIR/IMAP Checker.app"
fi

echo "✅ Build xong! → Product/IMAP Checker.app"
du -sh "$PRODUCT_DIR/IMAP Checker.app" 2>/dev/null || true
echo ""
echo "⚠️  App chưa ký Apple → lần đầu mở phải: chuột phải → Open → Open"
echo "ℹ️  App vẫn cần thư mục ~/MAC_WIN_PY/imap-checker (scripts/common/config/account) có sẵn trên máy."
