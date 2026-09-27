# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


project_root = Path(SPECPATH).parent
coincurve_datas, coincurve_binaries, coincurve_hiddenimports = collect_all("coincurve")

a = Analysis(
    [str(project_root / "keysmith" / "launcher.py")],
    pathex=[str(project_root)],
    binaries=coincurve_binaries,
    datas=[
        (str(project_root / "keysmith" / "static"), "keysmith/static"),
        *coincurve_datas,
    ],
    hiddenimports=coincurve_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="Keysmith",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    contents = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        name="Keysmith",
    )
    app = BUNDLE(
        contents,
        name="Keysmith.app",
        icon=None,
        bundle_identifier="com.keysmith.educational",
        info_plist={
            "CFBundleDisplayName": "Keysmith",
            "LSApplicationCategoryType": "public.app-category.education",
            "NSHighResolutionCapable": True,
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="Keysmith",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
    )
