# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

webview_datas, webview_bins, webview_imports = collect_all('webview')

a = Analysis(
    ['app/app.py'],
    pathex=['app'],
    binaries=webview_bins,
    datas=[
        ('app/mbc2-dashboard.html', '.'),
        ('app/schema.sql', '.'),
        ('app/default_programs.json', '.'),
        ('app/VERSION', '.'),
        ('app/icon.ico', '.'),
        *webview_datas,
    ],
    hiddenimports=[
        'server',
        'db_manager',
        'motor_api',
        *webview_imports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

splash = Splash(
    'app/splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    splash.binaries,
    a.binaries,
    a.datas,
    [],
    name='MBC2Dashboard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app/icon.ico'],
)
