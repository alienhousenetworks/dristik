#!/usr/bin/env bash
set -e

echo "Verifying PDF Rendering Toolchain..."
which weasyprint >/dev/null 2>&1 && echo "[OK] WeasyPrint found." || echo "[INFO] WeasyPrint not installed. Headless Chrome / Puppeteer fallback active."
