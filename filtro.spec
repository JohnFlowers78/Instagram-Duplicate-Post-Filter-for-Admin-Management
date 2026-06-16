# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 6.x — Filtro de Repetidas
# Gera dist/FiltroDeRepetidas/ (pasta portátil, sem Python no destino).

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

pw_stealth_datas = collect_data_files("playwright_stealth")
playwright_datas = collect_data_files("playwright")

a = Analysis(
    ["instabot\\main.py"],
    pathex=["instabot"],
    binaries=[],
    datas=[
        ("instabot\\assets", "assets"),
        *pw_stealth_datas,
        *playwright_datas,
    ],
    hiddenimports=[
        "PIL._tkinter_finder",
        "PIL.Image",
        "PIL.ImageTk",
        "PIL.ImageDraw",
        "imagehash",
        "requests",
        "playwright.sync_api",
        *collect_submodules("playwright"),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "pandas", "IPython"],
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
