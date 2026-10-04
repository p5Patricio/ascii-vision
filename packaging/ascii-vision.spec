# PyInstaller spec: builds one folder holding the GUI (windowed) and the CLI (console).
#
#   pip install -e ".[video]" pyinstaller
#   pyinstaller packaging/ascii-vision.spec --noconfirm
#
# Output: dist/ASCII Vision/ASCII Vision(.exe)  and  dist/ASCII Vision/ascii-vision(.exe)
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
ICON = os.path.join(SPECPATH, "app.ico")
PKG = os.path.join(ROOT, "src", "ascii_vision")

datas = [
    (os.path.join(PKG, "assets", "fonts"), os.path.join("ascii_vision", "assets", "fonts")),
    (os.path.join(PKG, "config_schema.json"), "ascii_vision"),
    (os.path.join(PKG, "assets", "icon.png"), os.path.join("ascii_vision", "assets")),
]
datas += collect_data_files("jsonschema_specifications")  # needed by jsonschema at runtime
datas += copy_metadata("ascii-vision")                      # so --version reports the real version
binaries = collect_dynamic_libs("av")                      # bundled FFmpeg libraries (PyAV)

hidden = ["av", "platformdirs"]
excludes = ["tkinter", "matplotlib", "scipy", "pandas", "pytest", "sklearn", "IPython",
            "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
            "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtCharts", "PySide6.QtDataVisualization"]

common = dict(pathex=[os.path.join(ROOT, "src")], datas=datas, binaries=binaries,
              hiddenimports=hidden, excludes=excludes)

gui_a = Analysis([os.path.join(SPECPATH, "gui_entry.py")], **common)
cli_a = Analysis([os.path.join(SPECPATH, "cli_entry.py")], **common)
MERGE((gui_a, "gui_entry", "gui_entry"), (cli_a, "cli_entry", "cli_entry"))

gui_pyz = PYZ(gui_a.pure)
cli_pyz = PYZ(cli_a.pure)

gui_exe = EXE(gui_pyz, gui_a.scripts, [], exclude_binaries=True, name="ASCII Vision",
              console=False, icon=ICON)
cli_exe = EXE(cli_pyz, cli_a.scripts, [], exclude_binaries=True, name="ascii-vision",
              console=True, icon=ICON)

COLLECT(gui_exe, gui_a.binaries, gui_a.datas,
        cli_exe, cli_a.binaries, cli_a.datas,
        strip=False, upx=False, name="ASCII Vision")
