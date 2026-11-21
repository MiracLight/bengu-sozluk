"""Bengü — ham kaynakları ve anlam modelini indirir (depoda tutulmayan büyük dosyalar).

Kullanım:  python araclar/indir.py          (var olan dosyalar atlanır; --yeniden ile hepsi yeniden indirilir)
Sonra:     python araclar/aktar.py && python araclar/vektor.py
"""
import sys
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "BenguSozluk/1.0 (offline Turkish dictionary builder; +https://github.com/MiracLight/bengu-sozluk)"}
HF = "https://huggingface.co/Xenova/multilingual-e5-small/resolve/main"

DOSYALAR = [
    # (hedef, adres, açıklama)
    ("veri/ham/trwiktionary/trwiktionary.jsonl.gz", "https://kaikki.org/trwiktionary/raw-wiktextract-data.jsonl.gz",
     "Türkçe Vikisözlük (kaikki.org, CC BY-SA)"),
    ("veri/ham/kaikki-ota/ota.jsonl", "https://kaikki.org/dictionary/Ottoman%20Turkish/kaikki.org-dictionary-OttomanTurkish.jsonl",
     "İngilizce Vikisözlük — Osmanlı Türkçesi (CC BY-SA)"),
    ("veri/ham/kaikki-otk/otk.jsonl", "https://kaikki.org/dictionary/Old%20Turkic/kaikki.org-dictionary-OldTurkic.jsonl",
     "İngilizce Vikisözlük — Eski Türkçe (CC BY-SA)"),
    ("veri/ham/vikikaynak/trwikisource.xml.bz2", "https://dumps.wikimedia.org/trwikisource/latest/trwikisource-latest-pages-articles.xml.bz2",
     "Türkçe Vikikaynak dökümü (kamu malı / CC BY-SA)"),
    ("veri/ham/vikisoz/trwikiquote.xml.bz2", "https://dumps.wikimedia.org/trwikiquote/latest/trwikiquote-latest-pages-articles.xml.bz2",
     "Türkçe Vikisöz dökümü (CC BY-SA)"),
    ("modeller/e5-small/model_quantized.onnx", f"{HF}/onnx/model_quantized.onnx", "Anlam modeli multilingual-e5-small int8 (MIT)"),
    ("modeller/e5-small/tokenizer.json", f"{HF}/tokenizer.json", "Model metin bölücüsü"),
]


def indir(hedef: Path, adres: str):
    gecici = hedef.with_suffix(hedef.suffix + ".kismi")
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(adres, headers=UA), timeout=120) as r, open(gecici, "wb") as f:
        toplam = int(r.headers.get("Content-Length") or 0)
        alinan = 0
        while parca := r.read(1 << 20):
            f.write(parca)
            alinan += len(parca)
            if toplam:
                print(f"\r    {alinan / 1e6:6.1f} / {toplam / 1e6:.1f} MB", end="", flush=True)
    print()
    gecici.replace(hedef)  # yarım kalan indirme asıl dosyanın yerine geçmez


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    yeniden = "--yeniden" in sys.argv
    for yol, adres, aciklama in DOSYALAR:
        hedef = KOK / yol
        if hedef.exists() and not yeniden:
            print(f"✓ {aciklama} (var)")
            continue
        print(f"↓ {aciklama}")
        indir(hedef, adres)
    print("Tamam. Sıradaki adım: python araclar/aktar.py && python araclar/vektor.py")


if __name__ == "__main__":
    main()
