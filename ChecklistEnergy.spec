# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\python\\PROJETO2\\Checklist_Energy\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\python\\PROJETO2\\Checklist_Energy\\templates', 'templates'), ('D:\\python\\PROJETO2\\Checklist_Energy\\static', 'static')],
    hiddenimports=['jinja2', 'uvicorn', 'fastapi', 'starlette'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ChecklistEnergy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
