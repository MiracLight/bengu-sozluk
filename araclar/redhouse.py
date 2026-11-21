"""Redhouse, A Turkish and English Lexicon (1890) — Internet Archive makine okumasından madde çıkarımı.

Makine okuması Arap harflerini bozduğu için yalnız Latin kısım kullanılır:
  köken (A./P./T./F.) · Redhouse çeviri yazısı · sözcük türü · İngilizce tanım
Okuma hatalarını elemek için madde başı, Bengü veritabanında var olan bir kelimeyle eşleşmek zorundadır.
"""
import re
from pathlib import Path

HAM = Path(__file__).resolve().parent.parent / "veri" / "ham" / "ia-redhouse1890"
DESEN = re.compile(r"^(A|P|T|F)\.\s+(?:\S+\s+){0,3}?([a-zâîûēāīūçşğöüıA-Za-z'ʿ‘’\-]{2,})(?:,\s*[^,]{0,25})?,"
                   r"\s*(s|a|v\. ?[nt]?|v|adv|prep|conj|int|pl|pron|n)\.\s+(.{5,})")
KOKEN = {"A": "Ar", "P": "Fa", "T": "T", "F": "Bt"}
TUR = {"s": "ad", "a": "sıfat", "v": "fiil", "v. n": "fiilden ad", "v.n": "fiilden ad", "v. t": "geçişli fiil",
       "v.t": "geçişli fiil", "adv": "zarf", "prep": "edat", "conj": "bağlaç", "int": "ünlem", "pl": "çoğul", "pron": "zamir", "n": "ad"}
# Redhouse çeviri yazısı → Türk alfabesi (yaklaşık)
CEVIR = [("sh", "ş"), ("ch", "ç"), ("kh", "h"), ("gh", "g"), ("dh", "z"), ("th", "s"), ("zh", "j"),
         ("q", "k"), ("w", "v"), ("j", "c"), ("x", "h")]


def turkcelestir(s):
    s = s.lower().replace("’", "").replace("‘", "").replace("'", "").replace("ʿ", "")
    for a, b in CEVIR:
        s = s.replace(a, b)
    return s


def maddeler():
    txt = "".join((HAM / f).read_text(encoding="utf-8") for f in ("part1.txt", "part2.txt"))
    for p in re.split(r"\n\s*\n", txt):
        p = re.sub(r"-\s*\n\s*", "", p).replace("\n", " ").strip()
        p = re.sub(r"\s{2,}", " ", p)
        m = DESEN.match(p)
        if not m:
            continue
        tanim = m.group(4)
        tanim = re.split(r"\s[|£§¢¥]\s|\s{3,}", tanim)[0].strip(" |;.,")
        # Numaralı anlamlar: "1. ... 2. ..."
        anlamlar = [a.strip(" ;.,") for a in re.split(r"(?:^|\s)\d[.,]\s*", tanim) if len(a.strip(" ;.,")) > 2]
        yield {"koken": KOKEN[m.group(1)], "ceviri": m.group(2), "tur": TUR.get(m.group(3).replace(" ", "").replace(".", ". ").strip(), m.group(3)),
               "anlamlar": anlamlar[:6] or [tanim]}
