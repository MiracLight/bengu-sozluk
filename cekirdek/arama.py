"""Bengü — arama ve madde sorguları (SQLite üzerinde).

Arama katmanları (puan sırasıyla):
  1. Tam eşleşme (yazım farkları önemsiz: â/a, ḥ/h, ş/s …)
  2. Çekim sözlüğü: "aşkın" → aşk (Vikisözlük'ün çekimli biçimleri)
  3. Kök bulma: sorgunun en uzun madde olan baş kısmı ("gönüllerimizde" → gönül)
  4. Baş kısım eşleşmesi: "gönü" → gönül, gönüllü …
  5. Tam metin: tanımlar ve örnek cümlelerde geçen kelime
"""
import datetime
import re
import sqlite3
from pathlib import Path

from .normal import normal, ascii_, arap_normal, arap_mi

VERITABANI = Path(__file__).resolve().parent.parent / "veri" / "bengu.db"
KAYNAK_SIRA = {"bengu": 0, "trwikt": 1, "enwikt-ota": 2, "enwikt-otk": 3}


def baglan():
    if not VERITABANI.is_file():
        raise FileNotFoundError(f"Sözlük veritabanı bulunamadı: {VERITABANI}")
    # as_uri(): boşluk / Türkçe harf / # içeren kurulum yollarında da doğru adres; immutable: kurulum klasörüne hiç yazılmaz
    db = sqlite3.connect(VERITABANI.as_uri() + "?mode=ro&immutable=1", uri=True, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db


def _liste(s):
    return [x for x in (s or "").split(",") if x]


def ara(db, sorgu, donem="", koken="", tur="", dil="", kaynak="", sayfa=1, boyut=25):
    q, qa = normal(sorgu), ascii_(sorgu)
    if not q:
        return {"sorgu": sorgu, "toplam": 0, "sonuclar": [], "kok": None}
    puan = {}  # kayit_id -> puan

    def ekle(satirlar, p):
        for r in satirlar:
            puan[r[0]] = max(puan.get(r[0], 0), p)

    kok = None
    if arap_mi(sorgu):  # Arap harfiyle arama: yazılışı eşleşen bütün kayıtlar
        ekle(db.execute("SELECT kayit_id FROM osmanli_dizin WHERE ar_norm=?", (arap_normal(sorgu),)), 100)
        ekle(db.execute("SELECT kayit_id FROM osmanli_dizin WHERE ar_norm LIKE ? LIMIT 60", (arap_normal(sorgu) + "%",)), 70)
    else:
        ekle(db.execute("SELECT id FROM kayit WHERE norm=?", (q,)), 100)
        ekle(db.execute("SELECT id FROM kayit WHERE ascii=? AND norm!=?", (qa, q)), 95)

    # 2. Çekim sözlüğü
    lemmalar = [] if arap_mi(sorgu) else [r[0] for r in db.execute("SELECT DISTINCT lemma FROM cekim WHERE norm=?", (q,))]
    for lem in lemmalar:
        ids = db.execute("SELECT id FROM kayit WHERE norm=?", (normal(lem),)).fetchall()
        if ids:
            ekle(ids, 90)
            kok = kok or {"sorgu": sorgu, "madde": lem, "yol": "çekim"}
    # 3. Kök bulma (tek kelimelik sorgularda)
    if not kok and not puan and " " not in q and not arap_mi(sorgu):
        for n in range(len(q) - 1, 1, -1):
            ids = db.execute("SELECT id FROM kayit WHERE norm=? AND tur!='özel ad'", (q[:n],)).fetchall()
            if ids:
                ekle(ids, 85)
                kok = {"sorgu": sorgu, "madde": q[:n], "yol": "kök"}
                break
    # 4. Baş kısım
    if len(q) >= 2 and not arap_mi(sorgu):
        ekle(db.execute("SELECT id FROM kayit WHERE norm LIKE ? ESCAPE '\\' ORDER BY length(norm) LIMIT 80",
                        (q.replace("%", "\\%").replace("_", "\\_") + "%",)), 70)
    # 5. Tam metin
    if len(qa) >= 3:
        ifade = '"' + qa.replace('"', "") + '"'
        try:
            ekle(db.execute("SELECT rowid FROM kayit_fts WHERE kayit_fts MATCH ? ORDER BY bm25(kayit_fts) LIMIT 300",
                            (ifade,)), 40)
        except sqlite3.OperationalError:
            pass

    if not puan:
        return {"sorgu": sorgu, "toplam": 0, "sonuclar": [], "kok": kok}

    # Süzgeçler
    kosul, arg = [f"k.id IN ({','.join('?' * len(puan))})"], list(puan)
    for alan, deger in (("k.koken", koken), ("k.tur", tur), ("k.dil", dil), ("k.kaynak_id", kaynak)):
        l = _liste(deger)
        if l:
            kosul.append(f"{alan} IN ({','.join('?' * len(l))})")
            arg += l
    dl = _liste(donem)
    if dl:
        kosul.append(f"k.id IN (SELECT kayit_id FROM kayit_donem WHERE donem IN ({','.join('?' * len(dl))}))")
        arg += dl
    satirlar = db.execute(f"""
        SELECT k.id, k.baslik, k.norm, k.dil, k.tur, k.koken, k.osmanli, k.eski_yazi, k.kaynak_id, k.aciklama_dili,
               (SELECT metin FROM anlam WHERE kayit_id=k.id ORDER BY sira LIMIT 1) AS anlam,
               (SELECT COALESCE(yazar,'') || '|' || COALESCE(eser,'') || '|' || COALESCE(yuzyil,'')
                  FROM ornek WHERE kayit_id=k.id AND yazar IS NOT NULL LIMIT 1) AS kunye
        FROM kayit k WHERE {' AND '.join(kosul)}""", arg).fetchall()

    # Başlığa göre grupla
    gruplar = {}
    for r in satirlar:
        p = puan[r["id"]]
        if r["tur"] == "özel ad":
            p -= 20
        if r["aciklama_dili"] == "en":
            p -= 5
        if r["kaynak_id"] == "bengu":
            p += 5
        g = gruplar.setdefault(r["norm"], {"baslik": r["baslik"], "puan": -999, "kayitlar": []})
        g["puan"] = max(g["puan"], p)
        g["kayitlar"].append(dict(r))
    sirali = sorted(gruplar.values(), key=lambda g: (-g["puan"], len(g["baslik"]), g["baslik"]))
    for g in sirali:
        g["kayitlar"].sort(key=lambda k: (k["tur"] == "özel ad", KAYNAK_SIRA.get(k["kaynak_id"], 9)))
        g["baslik"] = g["kayitlar"][0]["baslik"]
    bas = (max(1, sayfa) - 1) * boyut
    return {"sorgu": sorgu, "toplam": len(sirali), "sonuclar": sirali[bas:bas + boyut], "kok": kok,
            "sayfa": sayfa, "boyut": boyut}


def _kayit_ayrinti(db, k):
    d = dict(k)
    d["donem"] = [r[0] for r in db.execute("SELECT donem FROM kayit_donem WHERE kayit_id=?", (k["id"],))]
    d["anlamlar"] = [dict(r) for r in db.execute("SELECT sira, metin, etiket FROM anlam WHERE kayit_id=? ORDER BY sira", (k["id"],))]
    d["ornekler"] = [dict(r) for r in db.execute(
        "SELECT o.*, y.id AS yazar_id FROM ornek o LEFT JOIN yazar y ON y.ad=o.yazar WHERE o.kayit_id=?", (k["id"],))]
    d["ilgili"] = [{"baslik": r[0], "tip": r[1],
                    "var": db.execute("SELECT 1 FROM kayit WHERE norm=? LIMIT 1", (normal(r[0]),)).fetchone() is not None}
                   for r in db.execute("SELECT baslik, tip FROM ilgili WHERE kayit_id=?", (k["id"],))]
    return d


def madde(db, baslik):
    n = normal(baslik)
    kayitlar = db.execute("""SELECT k.*, s.ad AS kaynak_ad, s.kisa AS kaynak_kisa, s.lisans AS kaynak_lisans, s.url AS kaynak_url
                             FROM kayit k JOIN kaynak s ON s.id=k.kaynak_id WHERE k.norm=?
                             ORDER BY k.tur='özel ad', s.sira, k.id""", (n,)).fetchall()
    if not kayitlar:
        return None
    return {"baslik": kayitlar[0]["baslik"], "kayitlar": [_kayit_ayrinti(db, k) for k in kayitlar]}


def _gun():
    return (datetime.date.today() - datetime.date(2024, 1, 1)).days


def _sec(db, sql, tuz=0):
    n = db.execute(f"SELECT count(*) FROM ({sql})").fetchone()[0]
    if not n:
        return None
    return db.execute(f"{sql} LIMIT 1 OFFSET ?", (((_gun() * 7919) + tuz * 104729) % n,)).fetchone()


def gunun_seckisi(db):
    # Günün kelimesi: tanıklı derleme maddeleri ile örnekli, kökeni belli eski/Arapça/Farsça kökenli kelimeler dönüşümlü
    if _gun() % 3 == 0:
        k = _sec(db, "SELECT k.norm FROM kayit k WHERE k.kaynak_id='bengu' AND k.tur='kelime' AND EXISTS(SELECT 1 FROM ornek WHERE kayit_id=k.id)", 1)
    else:
        k = _sec(db, """SELECT k.norm FROM kayit k WHERE k.kaynak_id='trwikt' AND k.dil='tr' AND k.tur='kelime'
                        AND k.osmanli IS NOT NULL AND length(k.norm) > 3
                        AND (k.koken IN ('Ar','Fa') OR EXISTS(SELECT 1 FROM kayit_donem WHERE kayit_id=k.id AND donem='islam-oncesi'))
                        AND EXISTS(SELECT 1 FROM ornek WHERE kayit_id=k.id) ORDER BY k.id""", 2)
    deyim = _sec(db, "SELECT baslik, (SELECT metin FROM anlam WHERE kayit_id=k.id ORDER BY sira LIMIT 1) AS anlam FROM kayit k WHERE tur='deyim' AND dil='tr' ORDER BY id", 3)
    atasozu = _sec(db, "SELECT baslik, (SELECT metin FROM anlam WHERE kayit_id=k.id ORDER BY sira LIMIT 1) AS anlam FROM kayit k WHERE tur='atasözü' ORDER BY id", 4)
    beyit = None
    if _gun() % 4 != 0:  # çoğu gün tanık derleminden (Divan / Tekke / Halk), arada Bengü derlemesinden
        s = _sec(db, """SELECT s.id, s.metin_id, s.sira, s.kita, s.metin FROM satir s JOIN metin m ON m.id=s.metin_id
                        WHERE m.gelenek IN ('Divan','Tekke','Halk') AND s.ceviri IS NULL AND s.kita > 0 AND length(s.metin) BETWEEN 25 AND 90
                          AND EXISTS(SELECT 1 FROM satir x WHERE x.metin_id=s.metin_id AND x.kita=s.kita AND x.sira=s.sira+1 AND length(x.metin) > 20)
                          AND NOT EXISTS(SELECT 1 FROM satir x WHERE x.metin_id=s.metin_id AND x.kita=s.kita AND x.sira=s.sira-1)
                        ORDER BY s.id""", 5)
        if s:
            ikinci = db.execute("SELECT metin FROM satir WHERE metin_id=? AND sira=?", (s["metin_id"], s["sira"] + 1)).fetchone()[0]
            m = db.execute("SELECT m.eser, m.url, m.yazar_id, COALESCE(y.gorunen, y.ad) AS yazar FROM metin m LEFT JOIN yazar y ON y.id=m.yazar_id WHERE m.id=?",
                           (s["metin_id"],)).fetchone()
            beyit = {"metin": s["metin"] + " / " + ikinci, "aciklama": None, "yazar": m["yazar"], "yazar_id": m["yazar_id"],
                     "eser": m["eser"], "yuzyil": None, "url": m["url"], "metin_id": s["metin_id"]}
    if not beyit:
        b = _sec(db, "SELECT o.metin, o.aciklama, o.yazar, o.eser, o.yuzyil, y.id AS yazar_id FROM ornek o LEFT JOIN yazar y ON y.ad=o.yazar WHERE o.metin LIKE '% / %' ORDER BY o.rowid", 5)
        beyit = dict(b) if b else None
    sanat = _sec(db, "SELECT baslik, osmanli, (SELECT metin FROM anlam WHERE kayit_id=k.id ORDER BY sira LIMIT 1) AS anlam FROM kayit k WHERE tur='sanat' ORDER BY id", 6)
    return {"kelime": madde(db, k[0]) if k else None,
            "deyim": dict(deyim) if deyim else None, "atasozu": dict(atasozu) if atasozu else None,
            "beyit": beyit, "sanat": dict(sanat) if sanat else None}


def oneri(db, sorgu, n=8):
    q = normal(sorgu)
    if len(q) < 2:
        return []
    return [r[0] for r in db.execute(
        "SELECT baslik FROM kayit WHERE norm LIKE ? AND tur!='özel ad' GROUP BY norm ORDER BY length(norm), norm LIMIT ?",
        (q.replace("%", "") + "%", n))]


def yazarlar(db):
    out = []
    for y in db.execute("SELECT * FROM yazar"):
        d = dict(y)
        d["tur"] = _liste(d["tur"])
        d["eserler"] = [dict(e) for e in db.execute("SELECT ad, tarih, tur, notu FROM eser WHERE yazar_id=? ORDER BY sira", (y["id"],))]
        d["tanik_sayisi"] = db.execute("SELECT count(*) FROM ornek WHERE yazar=?", (y["ad"],)).fetchone()[0]
        d["metin_sayisi"] = db.execute("SELECT count(*) FROM metin WHERE yazar_id=?", (y["id"],)).fetchone()[0]
        d["satir_sayisi"] = db.execute("SELECT count(*) FROM satir s JOIN metin m ON m.id=s.metin_id WHERE m.yazar_id=?", (y["id"],)).fetchone()[0]
        out.append(d)
    return out


def yazar(db, yid):
    y = next((x for x in yazarlar(db) if x["id"] == yid), None)
    if not y:
        return None
    y["taniklar"] = [dict(r) for r in db.execute(
        "SELECT o.metin, o.eser, o.yuzyil, k.baslik FROM ornek o JOIN kayit k ON k.id=o.kayit_id WHERE o.yazar=?", (y["ad"],))]
    # Vikikaynak'taki metinleri (eser sayfaları) ve ilk dörtlük/beyit
    y["metinler"] = []
    for m in db.execute("""SELECT m.id, m.eser, m.sayfa, m.url, count(s.id) AS satir FROM metin m JOIN satir s ON s.metin_id=m.id
                           WHERE m.yazar_id=? GROUP BY m.id ORDER BY m.sayfa""", (yid,)):
        ilk = [r[0] for r in db.execute("SELECT metin FROM satir WHERE metin_id=? ORDER BY sira LIMIT 2", (m["id"],))]
        d = dict(m)
        d["ilk"] = ilk
        y["metinler"].append(d)
    return y


def metin(db, mid):
    """Bir eser sayfasının tam metni (okuma görünümü)."""
    m = db.execute("""SELECT m.*, COALESCE(y.gorunen, y.ad) AS yazar FROM metin m LEFT JOIN yazar y ON y.id=m.yazar_id
                      WHERE m.id=?""", (mid,)).fetchone()
    if not m:
        return None
    d = dict(m)
    d["satirlar"] = [dict(r) for r in db.execute("SELECT sira, kita, metin, ceviri, eski_yazi FROM satir WHERE metin_id=? ORDER BY sira", (mid,))]
    return d


DONEM_SIRA = {"islam-oncesi": 0, "gecis": 1, "islami": 2, "bati": 3, "gunumuz": 4}
_KELIME = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîûÊêÔôÑñŊŋ]+")


def _vurgular(db, metin, n, formlar):
    """Satırda aranan kelimenin (ve çekimli biçimlerinin) geçtiği konumlar."""
    out = []
    for m in _KELIME.finditer(metin):
        k = normal(m.group(0))
        if k == n or k in formlar or normal(m.group(0).lower().replace("ñ", "ng").replace("ŋ", "ng")) == n:
            out.append([m.start(), m.end()])
    return out


def tanik(db, baslik, yazar="", donem="", sayfa=1, boyut=20):
    """Edebî metinlerde (Vikikaynak derlemi) kelimenin geçtiği satırlar; beyit bağlamıyla."""
    n = normal(baslik)
    if not n:
        return {"toplam": 0, "satirlar": [], "yazarlar": [], "donemler": {}}
    if " " in n:
        # Çok kelimeli madde: kelime dizisi; son kelime ekli olabilir (dil-i nâşâd → dil-i nâşâde)
        jetonlar = [j for j in re.split(r"\W+", ascii_(baslik)) if j]
        ifade = " + ".join(f'"{j}"' for j in jetonlar[:-1]) + (" + " if len(jetonlar) > 1 else "") + f'"{jetonlar[-1]}"*'
        try:
            ids = [r[0] for r in db.execute("SELECT rowid FROM satir_fts WHERE satir_fts MATCH ? LIMIT 2000", (ifade,))]
        except sqlite3.OperationalError:
            ids = []
        formlar = set()
    else:
        ids = [r[0] for r in db.execute("SELECT satir_id FROM satir_dizin WHERE norm=?", (n,))]
        formlar = {r[0] for r in db.execute("SELECT norm FROM cekim WHERE lemma=? OR lemma=?", (baslik, n))}
    if not ids:
        return {"toplam": 0, "satirlar": [], "yazarlar": [], "donemler": {}}
    yer = ",".join("?" * len(ids))
    tum = db.execute(f"""SELECT s.id, s.metin_id, s.sira, s.kita, s.metin, s.ceviri, s.eski_yazi,
                                m.yazar_id, m.eser, m.url, m.donem, m.gelenek, COALESCE(y.gorunen, y.ad, m.yazar_id) AS yazar
                         FROM satir s JOIN metin m ON m.id=s.metin_id LEFT JOIN yazar y ON y.id=m.yazar_id
                         WHERE s.id IN ({yer})""", ids).fetchall()
    # Aynı şiir birden çok sayfada olabilir: yazar + satır metni tekrarını at
    gorulen, tekil = set(), []
    for r in tum:
        a = (r["yazar_id"], normal(r["metin"]))
        if a not in gorulen:
            gorulen.add(a)
            tekil.append(r)
    yazar_say, donem_say = {}, {}
    for r in tekil:
        d = yazar_say.setdefault(r["yazar_id"], {"id": r["yazar_id"], "ad": r["yazar"], "donem": r["donem"], "sayi": 0})
        d["sayi"] += 1
        donem_say[r["donem"]] = donem_say.get(r["donem"], 0) + 1
    secili = [r for r in tekil if (not yazar or r["yazar_id"] in yazar.split(",")) and (not donem or r["donem"] in donem.split(","))]
    secili.sort(key=lambda r: (DONEM_SIRA.get(r["donem"], 9), r["yazar"] or "", r["metin_id"], r["sira"]))
    # Kelime beytin iki satırında da geçiyorsa beyit bir kez gösterilsin: ikinci satırı ayıkla
    konum = {(r["metin_id"], r["sira"]) for r in secili}
    secili = [r for r in secili if not (r["sira"] % 2 == 1 and (r["metin_id"], r["sira"] - 1) in konum and r["ceviri"] is None)]
    bas = (max(1, sayfa) - 1) * boyut
    out = []
    for r in secili[bas:bas + boyut]:
        # Beyit bağlamı: aynı kıtadaki sonraki satır (yoksa önceki)
        komsu = db.execute("SELECT metin, sira FROM satir WHERE metin_id=? AND kita=? AND sira IN (?,?) ORDER BY sira",
                           (r["metin_id"], r["kita"], r["sira"] - 1, r["sira"] + 1)).fetchall()
        sonraki = next((k for k in komsu if k["sira"] == r["sira"] + 1), None)
        onceki = next((k for k in komsu if k["sira"] == r["sira"] - 1), None)
        d = {k: r[k] for k in ("metin", "ceviri", "eski_yazi", "yazar_id", "yazar", "eser", "url", "donem", "gelenek")}
        d["vurgu"] = _vurgular(db, r["metin"], n, formlar) if " " not in n else []
        if r["ceviri"] is None:  # Orhun satırlarında bağlam yerine çeviri gösterilir
            if sonraki and (r["sira"] % 2 == 0 or not onceki):
                d["sonra"] = sonraki["metin"]
                d["sonra_vurgu"] = _vurgular(db, sonraki["metin"], n, formlar) if " " not in n else []
            elif onceki:
                d["once"] = onceki["metin"]
                d["once_vurgu"] = _vurgular(db, onceki["metin"], n, formlar) if " " not in n else []
        out.append(d)
    yazarlar_ = sorted(yazar_say.values(), key=lambda d: (DONEM_SIRA.get(d["donem"], 9), -d["sayi"]))
    return {"toplam": len(secili), "genel_toplam": len(tekil), "sayfa": sayfa, "boyut": boyut, "satirlar": out,
            "yazarlar": yazarlar_, "donemler": donem_say}


def kaynaklar(db):
    return [dict(r) for r in db.execute(
        """SELECT s.*, (SELECT count(*) FROM kayit WHERE kaynak_id=s.id) AS kayit_sayisi,
                  (SELECT count(*) FROM metin WHERE kaynak_id=s.id) AS eser_sayisi,
                  (SELECT count(*) FROM satir x JOIN metin m ON m.id=x.metin_id WHERE m.kaynak_id=s.id) AS satir_sayisi
           FROM kaynak s ORDER BY sira""")]


def istatistik(db):
    q = lambda s: db.execute(s).fetchone()[0]
    return {
        "kayit": q("SELECT count(*) FROM kayit"),
        "baslik": q("SELECT count(DISTINCT norm) FROM kayit"),
        "deyim": q("SELECT count(*) FROM kayit WHERE tur='deyim'"),
        "atasozu": q("SELECT count(*) FROM kayit WHERE tur='atasözü'"),
        "osmanli": q("SELECT count(*) FROM kayit WHERE osmanli IS NOT NULL"),
        "ornek": q("SELECT count(*) FROM ornek"),
        "satir": q("SELECT count(*) FROM satir"),
        "eser": q("SELECT count(*) FROM metin"),
        "donem": {r[0]: r[1] for r in db.execute("SELECT donem, count(*) FROM kayit_donem GROUP BY donem")},
        "olusturma": q("SELECT deger FROM bilgi WHERE anahtar='olusturma'"),
    }


def donem_listesi(db, donem, sayfa=1, boyut=40, tur=""):
    kosul, arg = "d.donem=?", [donem]
    if tur:
        kosul += " AND k.tur=?"
        arg.append(tur)
    # Önce derleme ve tanıklı kayıtlar
    rows = db.execute(f"""
        SELECT k.baslik, k.tur, k.koken, k.osmanli, k.eski_yazi, k.dil, k.kaynak_id,
               (SELECT metin FROM anlam WHERE kayit_id=k.id ORDER BY sira LIMIT 1) AS anlam
        FROM kayit_donem d JOIN kayit k ON k.id=d.kayit_id
        WHERE {kosul} AND k.tur!='özel ad'
        ORDER BY k.kaynak_id!='bengu', k.eski_yazi IS NULL, NOT EXISTS(SELECT 1 FROM ornek WHERE kayit_id=k.id), k.norm
        LIMIT ? OFFSET ?""", arg + [boyut, (max(1, sayfa) - 1) * boyut]).fetchall()
    toplam = db.execute(f"SELECT count(*) FROM kayit_donem d JOIN kayit k ON k.id=d.kayit_id WHERE {kosul} AND k.tur!='özel ad'", arg).fetchone()[0]
    return {"toplam": toplam, "sayfa": sayfa, "boyut": boyut, "kayitlar": [dict(r) for r in rows]}
