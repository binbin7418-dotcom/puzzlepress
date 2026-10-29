# PyInstaller spec — build with: pyinstaller puzzlepress.spec
a = Analysis(['gui.py'], pathex=[], binaries=[], datas=[], hiddenimports=[],
             hookspath=[], runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PuzzlePress',
          console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PuzzlePress')
