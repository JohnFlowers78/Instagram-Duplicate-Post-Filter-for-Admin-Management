"""Utilitario de caminhos: funciona tanto ao rodar como script quanto como .exe (PyInstaller).

Ao ser empacotado com PyInstaller (--onedir):
  DATA_DIR   = pasta "data/" ao lado do FiltroDeRepetidas.exe   (gravavel pelo usuario)
  ASSETS_DIR = pasta "assets/" dentro do bundle _internal/      (somente leitura)

Ao rodar como script Python normal:
  DATA_DIR   = instabot/data/
  ASSETS_DIR = instabot/assets/
"""
import sys
from pathlib import Path

_FROZEN = getattr(sys, "frozen", False)

if _FROZEN:
    DATA_DIR   = Path(sys.executable).parent / "data"
    ASSETS_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets"
else:
    DATA_DIR   = Path(__file__).parent / "data"
    ASSETS_DIR = Path(__file__).parent / "assets"
