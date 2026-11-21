"""Bengü — anlamsal arama dizini (veri/vektor.npz).

Dizine girenler:
  kayıtlar: Osmanlıca / Arapça / Farsça / Türkçe kökenli kelimeler, deyimler, atasözleri, tamlamalar
            (Türkçe açıklamalı olanlar; metin = "başlık: tanım1; tanım2")
  satırlar: Vikikaynak tanık derlemindeki şiir ve metin satırları (Orhun'da Türkiye Türkçesi çevirisiyle)
Kullanım:  python araclar/vektor.py     (aktar.py'den sonra; ~3–5 dk)
"""
import sqlite3
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402

from cekirdek import anlam  # noqa: E402


def main():
    db = sqlite3.connect(KOK / "veri" / "bengu.db")
    t0 = time.time()
    kayitlar = db.execute("""
        SELECT k.id, k.baslik, (SELECT group_concat(metin, '; ') FROM (SELECT metin FROM anlam WHERE kayit_id=k.id ORDER BY sira LIMIT 3))
        FROM kayit k
        WHERE k.aciklama_dili='tr' AND k.tur NOT IN ('özel ad','kısaltma','ek')
          AND (k.dil IN ('ota','otk') OR k.koken IN ('Ar','Fa','T') OR k.tur IN ('deyim','atasözü','tamlama') OR k.kaynak_id='bengu')
          AND EXISTS(SELECT 1 FROM anlam WHERE kayit_id=k.id)""").fetchall()
    k_id = np.array([r[0] for r in kayitlar], dtype=np.int32)
    k_metin = [f"{r[1]}: {r[2][:300]}" for r in kayitlar]
    print(f"Kayıtlar: {len(k_metin)}")
    k_v = anlam.kodla(k_metin, "passage", parti=128)
    print(f"  bitti ({time.time() - t0:.0f} sn)")

    satirlar = db.execute("""SELECT s.id, s.metin, s.ceviri FROM satir s WHERE length(s.metin) >= 12""").fetchall()
    s_id = np.array([r[0] for r in satirlar], dtype=np.int32)
    s_metin = [(r[2] if r[2] else r[1])[:400] for r in satirlar]  # Orhun: çeviri anlamı daha iyi taşır
    print(f"Satırlar: {len(s_metin)}")
    s_v = anlam.kodla(s_metin, "passage", parti=128)
    print(f"  bitti ({time.time() - t0:.0f} sn)")

    hedef = KOK / "veri" / "vektor.npz"
    np.savez(hedef, kayit_id=k_id, kayit_v=k_v.astype(np.float16), satir_id=s_id, satir_v=s_v.astype(np.float16))
    print(f"Kaydedildi: {hedef.stat().st_size / 1e6:.0f} MB, toplam {time.time() - t0:.0f} sn")


if __name__ == "__main__":
    main()
