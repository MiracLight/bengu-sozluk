"""Bengü — Osmanlıca ⇄ Günümüz Türkçesi karşılık bulucu.

Yapay zekâ kullanmaz; yalnızca sözlük verisindeki belgelenmiş ilişkilerden öneri üretir:
  tanım       → Osmanlıca kaydın Türkçe tanımında kelime geçiyor       (güçlü)
  eş anlamlı  → Vikisözlük eş anlamlı bağlantısı                         (iyi)
  İngilizce   → İngilizce köprü: özlem → longing → iştiyak               (yakın anlam, en düşük güven)
"""
import re

from .normal import normal, arap_normal, arap_mi

GUVEN = [(2.6, "tam karşılık"), (2.0, "eş anlamlı"), (0, "yakın anlam")]
YOL_ADI = {"tanım": "tanımdan", "eş anlamlı": "eş anlamlı bağlantısından", "İngilizce": "İngilizce köprüden"}
OSM_KOSUL = "(dil='ota' OR koken IN ('Ar','Fa') OR (koken IS NULL AND osmanli IS NOT NULL AND dil='tr'))"


def _guven(p):
    return next(ad for esik, ad in GUVEN if p >= esik)


def _ilk_anlam(db, kid, dil="tr"):
    r = db.execute("SELECT metin FROM anlam WHERE kayit_id=? ORDER BY sira LIMIT 1", (kid,)).fetchone()
    return r[0] if r else None


def _turkce_anlam(db, norm):
    """Aynı başlığın Türkçe açıklamalı (Osmanlıca/Ar/Fa) bir kaydı varsa ilk anlamını döndürür."""
    r = db.execute(f"""SELECT (SELECT metin FROM anlam WHERE kayit_id=k.id ORDER BY sira LIMIT 1)
                       FROM kayit k WHERE norm=? AND aciklama_dili='tr' AND tur!='özel ad'
                       ORDER BY {OSM_KOSUL} DESC, kaynak_id='bengu' DESC LIMIT 1""", (norm,)).fetchone()
    return r[0] if r else None


def _lemma_adaylari(db, q):
    """Sorgunun sözlük biçimi adayları: kendisi, çekim sözlüğü, kök (en uzun baş kısım)."""
    yield q, None
    for (lem,) in db.execute("SELECT DISTINCT lemma FROM cekim WHERE norm=?", (q,)):
        yield normal(lem), "çekim"
    if " " not in q:
        for n in range(len(q) - 1, 2, -1):
            if db.execute("SELECT 1 FROM karsilik WHERE tr_norm=? LIMIT 1", (q[:n],)).fetchone():
                yield q[:n], "kök"
                break


def turkceden_osmanlicaya(db, kelime, sinir=15):
    q = normal(kelime)
    if not q:
        return {"sorgu": kelime, "oneriler": []}
    satirlar, aranan, yol = [], q, None
    for aday, y in _lemma_adaylari(db, q):
        satirlar = db.execute("SELECT kayit_id, puan, yol FROM karsilik WHERE tr_norm=?", (aday,)).fetchall()
        if satirlar:
            aranan, yol = aday, y
            break

    # Kayıt başına puan: en yüksek yol + birden fazla yoldan doğrulanma ödülü
    kayit_puan = {}
    for kid, p, y in satirlar:
        d = kayit_puan.setdefault(kid, {"puan": 0, "yollar": set()})
        d["puan"] = max(d["puan"], p)
        d["yollar"].add(y)
    gruplar = {}
    for kid, d in kayit_puan.items():
        k = db.execute("SELECT id, baslik, norm, osmanli, koken, dil, aciklama_dili, ceviri FROM kayit WHERE id=?", (kid,)).fetchone()
        if not k:
            continue
        p = d["puan"] + 0.25 * (len(d["yollar"]) - 1)
        baslik = k["ceviri"] if arap_mi(k["baslik"]) and k["ceviri"] else k["baslik"]
        if arap_mi(baslik) or "gerekiyor" in baslik:
            continue  # okunuşu bilinmeyen kayıtlar ve şablon artıkları öneri olarak sunulmaz
        anahtar = arap_normal(k["osmanli"]) if k["osmanli"] else k["norm"]
        g = gruplar.setdefault(anahtar, {"basliklar": [], "osmanli": k["osmanli"], "koken": k["koken"], "dil": k["dil"],
                                         "puan": 0, "yollar": set(), "anlam": None, "anlam_en": None, "madde": None})
        if baslik not in g["basliklar"]:
            g["basliklar"].append(baslik)
        g["koken"] = g["koken"] or k["koken"]
        g["yollar"] |= d["yollar"]
        if p > g["puan"]:
            g["puan"], g["madde"] = p, baslik
        anlam = _ilk_anlam(db, k["id"])
        if k["aciklama_dili"] == "tr":
            g["anlam"] = g["anlam"] or anlam
        else:
            g["anlam_en"] = g["anlam_en"] or anlam
            g["anlam"] = g["anlam"] or _turkce_anlam(db, k["norm"])
    # Aynı okunuşlu grupları birleştir (biri Arap harfli yazılışlı, diğeri yazılışsız kayıttan gelmiş olabilir)
    birlesik = {}
    for g in sorted(gruplar.values(), key=lambda g: g["osmanli"] is None):
        ortak = next((b for b in (normal(x) for x in g["basliklar"]) if b in birlesik), None)
        if ortak is None:
            for x in g["basliklar"]:
                birlesik[normal(x)] = g
            continue
        h = birlesik[ortak]
        h["basliklar"] += [x for x in g["basliklar"] if x not in h["basliklar"]]
        h["yollar"] |= g["yollar"]
        h["anlam"] = h["anlam"] or g["anlam"]
        h["koken"] = h["koken"] or g["koken"]
        if g["puan"] > h["puan"]:
            h["puan"], h["madde"] = g["puan"], g["madde"]
    tekil = list({id(g): g for g in birlesik.values()}.values())
    oneriler = sorted(tekil, key=lambda g: (-g["puan"], len(g["basliklar"][0])))[:sinir]
    for g in oneriler:
        g["guven"] = _guven(g["puan"])
        g["yollar"] = [YOL_ADI[y] for y in ("tanım", "eş anlamlı", "İngilizce") if y in g["yollar"]]
        g["puan"] = round(g["puan"], 2)

    # Aranan kelimenin kendisi zaten Arapça/Farsça kökenliyse bunu da bildir
    kendi = db.execute(f"""SELECT baslik, osmanli, koken FROM kayit WHERE norm=? AND {OSM_KOSUL} AND osmanli IS NOT NULL
                           AND tur!='özel ad' ORDER BY kaynak_id='bengu' DESC LIMIT 1""", (aranan,)).fetchone()
    return {"sorgu": kelime, "aranan": aranan, "yol": yol, "oneriler": oneriler,
            "kendisi": dict(kendi) if kendi else None}


def osmanlicadan_turkceye(db, kelime, sinir=20):
    s = kelime.strip()
    if not s:
        return {"sorgu": kelime, "bulunan": [], "karsiliklar": []}
    if arap_mi(s):
        ids = [r[0] for r in db.execute("SELECT kayit_id FROM osmanli_dizin WHERE ar_norm=?", (arap_normal(s),))]
    else:
        q = normal(s)
        ids = [r[0] for r in db.execute("SELECT id FROM kayit WHERE norm=? AND tur!='özel ad'", (q,))]
        if not ids:  # Türkçe harfsiz yazım (nihan / nihân / nihān hepsi aynı)
            from .normal import ascii_
            ids = [r[0] for r in db.execute("SELECT id FROM kayit WHERE ascii=? AND tur!='özel ad'", (ascii_(s),))]
    if not ids:
        return {"sorgu": kelime, "bulunan": [], "karsiliklar": []}
    yer = ",".join("?" * len(ids))
    kayitlar = db.execute(f"""SELECT k.id, k.baslik, k.norm, k.osmanli, k.koken, k.koken_ayrinti, k.dil, k.ceviri, k.aciklama_dili,
                                     s.ad AS kaynak_ad
                              FROM kayit k JOIN kaynak s ON s.id=k.kaynak_id WHERE k.id IN ({yer}) AND k.tur!='özel ad'
                              ORDER BY {OSM_KOSUL.replace('dil', 'k.dil').replace('koken', 'k.koken')} DESC, s.sira""", ids).fetchall()
    bulunan = []
    for k in kayitlar:
        anlamlar = [r[0] for r in db.execute("SELECT metin FROM anlam WHERE kayit_id=? ORDER BY sira", (k["id"],))]
        baslik = k["ceviri"] if arap_mi(k["baslik"]) and k["ceviri"] else k["baslik"]
        bulunan.append({"baslik": baslik, "osmanli": k["osmanli"], "koken": k["koken"], "koken_ayrinti": k["koken_ayrinti"],
                        "dil": k["dil"], "kaynak": k["kaynak_ad"], "ingilizce": k["aciklama_dili"] == "en",
                        "anlamlar": anlamlar[:6]})
    # Günümüz Türkçesi karşılıkları: karşılık tablosunun ters yönü
    karsiliklar = {}
    for tr_norm, p, y in db.execute(f"SELECT tr_norm, puan, yol FROM karsilik WHERE kayit_id IN ({yer})", ids):
        d = karsiliklar.setdefault(tr_norm, {"puan": 0, "yollar": set()})
        d["puan"] = max(d["puan"], p)
        d["yollar"].add(y)
    out = []
    kendileri = {normal(b["baslik"]) for b in bulunan}
    for tr_norm, d in karsiliklar.items():
        if tr_norm in kendileri:
            continue
        r = db.execute("SELECT baslik, koken FROM kayit WHERE norm=? AND dil='tr' AND tur!='özel ad' ORDER BY kaynak_id='bengu' DESC LIMIT 1",
                       (tr_norm,)).fetchone()
        if not r:
            continue
        p = d["puan"] + 0.25 * (len(d["yollar"]) - 1)
        out.append({"baslik": r["baslik"], "oz_turkce": r["koken"] == "T", "koken": r["koken"],
                    "guven": _guven(p), "puan": round(p, 2)})
    # Osmanlıca karşılığı sorulan kelimenin Arapça/Farsça eş anlamlıları da "günümüz karşılığı" değildir; sona at
    out.sort(key=lambda x: (x["koken"] in ("Ar", "Fa"), -x["puan"], not x["oz_turkce"], x["baslik"]))
    return {"sorgu": kelime, "bulunan": bulunan, "karsiliklar": out[:sinir]}


_KELIME = re.compile(r"[^\s.,;:!?()\"'“”«»…]+")


def cevir(db, metin, yon="tr-ota"):
    """Tek kelime ya da birden çok kelime. Birden çok kelimede her kelime için ayrı öneri listesi döner."""
    kelimeler = _KELIME.findall(metin or "")
    f = turkceden_osmanlicaya if yon == "tr-ota" else osmanlicadan_turkceye
    if len(kelimeler) <= 1:
        # Deyim / tamlama gibi çok kelimeli tek birim de olabilir: önce bütün olarak dene
        return {"yon": yon, "tek": True, "sonuc": f(db, metin)}
    butun = f(db, metin)
    dolu = butun.get("oneriler") or butun.get("bulunan")
    return {"yon": yon, "tek": False, "butun": butun if dolu else None,
            "kelimeler": [f(db, k, sinir=6) for k in kelimeler[:12]]}
