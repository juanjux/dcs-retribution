# -*- mode: python -*-

import glob
import os
import sysconfig

block_cipher = None


# The `mgrs` dependency (used by the target-recon kneeboard pages) ships a
# top-level compiled extension `libmgrs.<abi>-<platform>.pyd` that its core.py
# loads at import time via ctypes, from the `mgrs` package's parent directory.
# Because it's loaded by ctypes rather than imported, PyInstaller's static
# analysis can't see it, so we add it explicitly at the bundle root (".") so it
# sits next to the collected `mgrs` package, matching the wheel layout.
_mgrs_site_dirs = {sysconfig.get_paths()[k] for k in ("purelib", "platlib")}
_mgrs_libs = []
for _d in _mgrs_site_dirs:
    _mgrs_libs += glob.glob(os.path.join(_d, "libmgrs*.pyd"))
    _mgrs_libs += glob.glob(os.path.join(_d, "libmgrs*.so"))
mgrs_binaries = [(_p, ".") for _p in sorted(set(_mgrs_libs))]


analysis = Analysis(
    ['./qt_ui/main.py'],
    pathex=['.'],
    binaries=mgrs_binaries,
    datas=[
        ('resources', 'resources'),
        ('resources/caucasus.p', 'dcs/terrain/'),
        ('resources/nevada.p', 'dcs/terrain/'),
        ('client/build', 'client/build'),
    ],
    hiddenimports=['mgrs', 'mgrs.core', 'packaging.tags'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(
    analysis.pure,
    analysis.zipped_data,
    cipher=block_cipher,
)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    icon="resources/icon.ico",
    exclude_binaries=True,
    name='retribution_main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    contents_directory='.'
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    name='dcs-retribution',
)
