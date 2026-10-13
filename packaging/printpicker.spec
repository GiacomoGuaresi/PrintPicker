# PyInstaller spec: builds a windowed PrintPicker app for the current platform.
#
#     uv run pyinstaller packaging/printpicker.spec --noconfirm
#
# Output: dist/PrintPicker/ (Windows, Linux) or dist/PrintPicker.app (macOS).

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))
from printpicker.about import APP_NAME, BUNDLE_ID, COPYRIGHT, LICENSE_NAME, __version__  # noqa: E402

# Qt modules PrintPicker does not use: leaving them out saves a lot of space.
QT_EXCLUDES = [
    f"PySide6.{m}"
    for m in (
        "Qt3DAnimation", "Qt3DCore", "Qt3DExtras", "Qt3DInput", "Qt3DLogic", "Qt3DRender",
        "QtBluetooth", "QtCharts", "QtConcurrent", "QtDataVisualization", "QtDesigner",
        "QtGraphs", "QtHelp", "QtLocation", "QtMultimedia", "QtMultimediaWidgets", "QtNetworkAuth",
        "QtNfc", "QtOpenGL", "QtOpenGLWidgets", "QtPdf", "QtPdfWidgets", "QtPositioning",
        "QtQml", "QtQuick", "QtQuick3D", "QtQuickControls2", "QtQuickWidgets", "QtRemoteObjects",
        "QtScxml", "QtSensors", "QtSerialBus", "QtSerialPort", "QtSpatialAudio", "QtSql",
        "QtStateMachine", "QtSvgWidgets", "QtTest", "QtTextToSpeech", "QtUiTools",
        "QtWebChannel", "QtWebEngineCore", "QtWebEngineQuick", "QtWebEngineWidgets",
        "QtWebSockets", "QtWebView", "QtXml",
    )
]

a = Analysis(
    [str(SRC / "printpicker" / "__main__.py")],
    pathex=[str(SRC)],
    binaries=collect_dynamic_libs("rawpy") + collect_dynamic_libs("pillow_heif"),
    datas=[
        (str(SRC / "printpicker" / "i18n" / "*.qm"), "printpicker/i18n"),
        (str(SRC / "printpicker" / "resources" / "*.png"), "printpicker/resources"),
        (str(SRC / "printpicker" / "resources" / "*.svg"), "printpicker/resources"),
        (str(SRC / "printpicker" / "resources" / "fonts" / "*"), "printpicker/resources/fonts"),
        # Run scripts/fetch_model.py first; --self-test fails without it.
        (str(SRC / "printpicker" / "resources" / "models" / "*.onnx"), "printpicker/resources/models"),
        (str(SRC / "printpicker" / "resources" / "models" / "NOTICE.md"), "printpicker/resources/models"),
    ]
    + collect_data_files("pillow_heif"),
    hiddenimports=["pillow_heif", "onnxruntime"],
    excludes=["tkinter", "unittest", "pydoc", *QT_EXCLUDES],
    noarchive=False,
)
pyz = PYZ(a.pure)

icon_dir = ROOT / "packaging" / "icons"
icon = None
if sys.platform == "darwin" and (icon_dir / "printpicker.icns").exists():
    icon = str(icon_dir / "printpicker.icns")
elif sys.platform == "win32" and (icon_dir / "printpicker.ico").exists():
    icon = str(icon_dir / "printpicker.ico")

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    console=False,
    icon=icon,
)
coll = COLLECT(exe, a.binaries, a.datas, name=APP_NAME)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=icon,
        bundle_identifier=BUNDLE_ID,
        version=__version__,
        info_plist={
            "CFBundleShortVersionString": __version__,
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": f"{COPYRIGHT} — {LICENSE_NAME}",
        },
    )
