"""Rehber doğruluk testi: soru → beklenen niyet, kavram, süzgeç ve (anlamsal açıksa) ilk sonuçlarda bulunması gereken kelimeler.

Çalıştırma:  python testler/rehber_testi.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")
from cekirdek import anlam, arama, rehber  # noqa: E402
from cekirdek.normal import normal  # noqa: E402

# (soru, niyet, kavram, süzgeç, ilk ~10 sonuçta beklenenlerden en az biri)
DURUMLAR = [
    ("savaşın Osmanlıcası", "karsilik", "savaş", {}, {"cenk", "harp", "cidal"}),
    ("özlem için Farsça bir kelime", "karsilik", "özlem", {"koken": "Fa"}, {"ārzū", "arzu"}),
    ("gizlinin Osmanlıcası ne", "karsilik", "gizli", {}, {"nihan", "mektûm", "mahfi"}),
    ("nihan ne demek", "anlam", "nihan", {}, set()),
    ("mektûm kelimesinin anlamı", "anlam", "mektum", {}, set()),
    ("kibir anlamına gelen kelimeler", "kavram", "kibir", {}, {"gurur", "tekebbür", "azamet"}),
    ("cömertlik anlamında Arapça kelimeler", "kavram", "cömertlik", {"koken": "Ar"}, {"kerem", "semahat", "mürüvvet"}),
    ("korku anlamına gelen Osmanlıca kelimeler", "kavram", "korku", {"osm": True}, {"endişe", "havf", "dehşet", "haşyet"}),
    ("emek ile ilgili atasözleri", "kavram", "emek", {"tur": "atasözü"}, {"emek olmadan yemek olmaz"}),
    ("dostluk hakkında deyimler", "kavram", "dostluk", {"tur": "deyim"}, {"dostluk etmek"}),
    ("Fuzûlî'nin aşk geçen beyitleri", "tanik", "aşk", {"yazar": "fuzuli"}, set()),
    ("Divan şiirinde ayrılık temalı beyitler", "tanik", "ayrılık", {"gelenek": "Divan"}, set()),
    ("Yunus Emre gönül", "tanik", "gönül", {"yazar": "yunus-emre"}, set()),
    ("Orhun yazıtlarında tengri", "tanik", "tengri", {"donem": "islam-oncesi"}, set()),
    ("Karacaoğlan'ın şiirlerinde dağ", "tanik", "dağ", {"yazar": "karacaoglan"}, set()),
    ("ölüm ile ilgili Divan beyitleri", "tanik", "ölüm", {"gelenek": "Divan"}, set()),
    ("حسرت", "anlam", "حسرت", {}, set()),
    # Genişletilmiş niyetler
    ("çözümle: Aşk imiş her ne var âlemde", "cozumle", "Aşk imiş her ne var âlemde", {}, set()),
    ("Ezelden şâh-ı aşkın bende-i fermânıyuz cânâ", "cozumle", "Ezelden şâh-ı aşkın bende-i fermânıyuz cânâ", {}, set()),
    ("gül ile kafiyeli kelimeler", "kafiye", "gül", {}, {"bülbül", "gönül", "sünbül"}),
    ("-dâr ile biten Farsça kelimeler", "kafiye", "dar", {"koken": "Fa"}, {"didar", "payidar"}),
    ("kitabın kökeni nedir", "koken", "kitap", {}, set()),
    ("hasret kelimesinin eş anlamlısı", "ilgili", "hasret", {}, {"özlem"}),
    ("güzel kelimesinin zıt anlamlısı", "ilgili", "güzel", {}, {"çirkin", "çirkîn"}),
    ("aşk ile sevda arasındaki fark", "karsilastir", "aşk / sevda", {}, set()),
    ("Fuzûlî kimdir", "yazar", "", {"yazar": "fuzuli"}, set()),
    ("Tanzimat yazarları", "yazarlar", "", {"donem": "bati"}, set()),
]

# Çözümleyici: (metin, {yazılan: beklenen sözlük biçimi})
COZUMLEME = [
    ("Bir safâ bahşedelim gel şu dil-i nâşâde", {"dil-i nâşâde": "dil-i nâşâd", "bahşedelim": "bahşetmek"}),
    ("Yoh menüm kimi yanan âteş-i hicrân içre", {"menüm": "benim", "Yoh": "yok", "âteş": "ateş"}),
    ("Ezelden şâh-ı aşkın bende-i fermânıyuz cânâ", {"Ezelden": "ezel", "fermânıyuz": "ferman"}),
    ("Gönüllerimizde aşkın ateşi yanar", {"Gönüllerimizde": "gönül", "yanar": "yanmak"}),
]


def basliklar(yanit):
    out = set()
    for b in yanit["bolumler"]:
        v = b["veri"]
        if isinstance(v, list):
            out |= {normal(x.get("baslik", "")) for x in v[:10]}
        elif "oneriler" in v:
            out |= {normal(x) for o in v["oneriler"][:10] for x in o["basliklar"]}
    return out


def cozumleme_testi(db):
    from cekirdek import cozumleme
    gecen = toplam = 0
    for metin, beklenen in COZUMLEME:
        r = {k["yazilan"]: normal(k["bicim"] or "") for k in cozumleme.cozumle(db, metin)["kelimeler"]}
        for yaz, bic in beklenen.items():
            toplam += 1
            if r.get(yaz) == normal(bic):
                gecen += 1
            else:
                print(f"✗ çözümleme: {yaz} → {r.get(yaz)} (beklenen {bic})")
    print(f"Çözümleme: {gecen}/{toplam} kelime doğru")
    return gecen == toplam


def main():
    db = arama.baglan()
    acik = anlam.hazir()
    print(f"Anlamsal arama: {'açık' if acik else 'kapalı'}")
    gecen = 0
    for soru, niyet, kavram, sz, beklenen in DURUMLAR:
        t = time.time()
        y = rehber.sor(db, soru)
        ms = (time.time() - t) * 1000
        hatalar = []
        if y["niyet"] != niyet:
            hatalar.append(f"niyet {y['niyet']}≠{niyet}")
        if normal(y["kavram"]) != normal(kavram):
            hatalar.append(f"kavram '{y['kavram']}'≠'{kavram}'")
        for a, d in sz.items():
            if y["suzgec"].get(a) != d:
                hatalar.append(f"{a}={y['suzgec'].get(a)}≠{d}")
        if beklenen and (acik or niyet == "karsilik"):
            if not basliklar(y) & {normal(b) for b in beklenen}:
                hatalar.append(f"sonuçlarda yok: {sorted(beklenen)}")
        if not y["bolumler"] and niyet != "ara":
            hatalar.append("boş yanıt")
        durum = "✓" if not hatalar else "✗"
        gecen += not hatalar
        print(f"{durum} {soru:45} {ms:5.0f} ms  {'; '.join(hatalar)}")
    print(f"\n{gecen}/{len(DURUMLAR)} soru geçti")
    coz = cozumleme_testi(db)
    return gecen == len(DURUMLAR) and coz


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
