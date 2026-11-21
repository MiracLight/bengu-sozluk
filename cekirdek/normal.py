"""Bengü — Türkçe metin normalleştirme.

Aktarım (araclar/aktar.py) ve arama (cekirdek/arama.py) aynı kuralları kullanır.
  normal(): Türkçe harfleri korur; â/î/û ve çeviri yazı işaretlerini (ā ḥ ḳ ṭ ʿ ŋ …) sadeleştirir.
  ascii_(): ayrıca ş ç ğ ö ü ı → s c g o u i (Türkçe klavyesi olmayan kullanıcı için).
"""
import re

_TABLO = str.maketrans({
    "â": "a", "ā": "a", "á": "a", "à": "a", "ă": "a",
    "î": "i", "ī": "i", "í": "i",
    "û": "u", "ū": "u", "ú": "u",
    "ê": "e", "ē": "e", "é": "e", "ô": "o", "ō": "o",
    "ḥ": "h", "ḫ": "h", "ḳ": "k", "ḳ": "k", "ṭ": "t", "ṣ": "s", "ẓ": "z", "ż": "z", "ż": "z",
    "ḏ": "d", "ṯ": "t", "ġ": "g", "ñ": "n", "ŋ": "n", "ẕ": "z",
    "¹": "", "²": "", "³": "", "⁰": "",  # Eski Türkçe çeviri yazısındaki ünlü uyumu işaretleri (t²ŋr²i)
    "ʿ": "", "ʾ": "", "'": "", "’": "", "‘": "", "-": "", "̇": "", "̂": "", "̄": "",
})
_ASCII = str.maketrans({"ş": "s", "ç": "c", "ğ": "g", "ö": "o", "ü": "u", "ı": "i"})
_NOKTA = re.compile(r"[.,;:!?()\[\]\"«»“”…/]+")
_BOSLUK = re.compile(r"\s+")


def kucuk(s: str) -> str:
    """Türkçe kurallarıyla küçük harf (I→ı, İ→i)."""
    return s.replace("I", "ı").replace("İ", "i").lower()


def normal(s: str) -> str:
    s = kucuk(s or "").translate(_TABLO)
    s = _NOKTA.sub(" ", s)
    return _BOSLUK.sub(" ", s).strip()


def ascii_(s: str) -> str:
    return normal(s).translate(_ASCII)


# ---------- Arap harfli (Osmanlıca) yazı ----------
_HAREKE = re.compile(r"[ً-ٰٟـ‌‍]")  # harekeler, tatvil, ZWNJ
_ARAP_TABLO = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ة": "ه", "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
                             "ۀ": "ه", "ؤ": "و", "ئ": "ی", "ء": ""})
ARAP_HARF = re.compile(r"[؀-ۿ]")


def arap_normal(s: str) -> str:
    """Arap harfli yazıyı karşılaştırma için sadeleştirir (hareke yok, ي/ی ك/ک farkı yok)."""
    s = _HAREKE.sub("", s or "").translate(_ARAP_TABLO)
    return _BOSLUK.sub(" ", s).strip()


def arap_mi(s: str) -> bool:
    return bool(ARAP_HARF.search(s or ""))


_PARANTEZ = re.compile(r"\([^)]*\)")


def tanim_parcalari(metin: str):
    """'pres, basınç, baskı' → ['pres', 'basınç', 'baskı'] ; parantezli etiketler ve uzun açıklamalar atılır."""
    metin = _PARANTEZ.sub(" ", metin or "")
    out = []
    for p in re.split(r"[;,]", metin):
        p = normal(p)
        if p and len(p.split()) <= 3 and len(p) <= 40:
            out.append(p)
    return out
