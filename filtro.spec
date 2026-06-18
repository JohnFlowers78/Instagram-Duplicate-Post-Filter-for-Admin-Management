# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 6.x — Filtro de Repetidas
# Gera dist/FiltroDeRepetidas/ (pasta portátil, sem Python no destino).

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

# collect_all garante que os binarios dos decoders de imagem do PIL (JPEG, PNG, etc.)
# sejam incluidos no bundle — sem isso Image.open() falha silenciosamente no .exe.
pil_datas, pil_binaries, pil_hiddenimports = collect_all("PIL")
pw_stealth_datas = collect_data_files("playwright_stealth")
playwright_datas = collect_data_files("playwright")

a = Analysis(
    ["instabot\\main.py"],
    pathex=["instabot"],
    binaries=[*pil_binaries],
    datas=[
        ("instabot\\assets", "assets"),
        *pil_datas,
        *pw_stealth_datas,
        *playwright_datas,
    ],
    hiddenimports=[
        *pil_hiddenimports,
        "imagehash",
        *collect_submodules("imagehash"),
        *collect_submodules("numpy"),
        "requests",
        "playwright.sync_api",
        *collect_submodules("playwright"),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "pandas", "IPython"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FiltroDeRepetidas",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="instabot\\assets\\icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FiltroDeRepetidas",
)
