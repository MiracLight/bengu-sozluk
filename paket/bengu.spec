# PyInstaller tarifi — Bengu.exe (klasör kipi: hızlı açılış, kararlı)
# Derleme:  pyinstaller paket/bengu.spec --distpath <çıktı> --workpath <geçici>
import os
from pathlib import Path

KOK = Path(SPECPATH).resolve().parent  # bengu/

veriler = [
    (str(KOK / "ui"), "ui"),
    (str(KOK / "veri" / "bengu.db"), "veri"),
    (str(KOK / "modeller" / "e5-small" / "model_quantized.onnx"), "modeller/e5-small"),
    (str(KOK / "modeller" / "e5-small" / "tokenizer.json"), "modeller/e5-small"),
    (str(KOK / "modeller" / "e5-small" / "config.json"), "modeller/e5-small"),
    (str(KOK / "modeller" / "e5-small" / "LISANS.md"), "modeller/e5-small"),
]
if (KOK / "veri" / "vektor.npz").exists():
    veriler.append((str(KOK / "veri" / "vektor.npz"), "veri"))

a = Analysis(
    [str(KOK / "bengu_baslat.py")],
    pathex=[str(KOK)],
    datas=veriler,
    hiddenimports=["sunucu", "surum", "cekirdek.arama", "cekirdek.ceviri", "cekirdek.rehber", "cekirdek.anlam",
                   "cekirdek.cozumleme", "cekirdek.normal"],
    excludes=["tkinter", "PIL", "PyInstaller", "pip", "setuptools", "unittest", "pydoc", "test"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Bengu",
    icon=str(KOK / "paket" / "bengu.ico"),
    version=str(KOK / "paket" / "surum_bilgisi.txt"),
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Bengu", upx=False)
