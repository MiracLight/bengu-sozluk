"""Bengü — veri aktarımı.

Ham kaynakları (veri/ham) okuyup tek bir SQLite veritabanı üretir: veri/bengu.db

Kaynaklar:
  bengu        Bengü derlemesi (veri/derleme/*.json) — elle hazırlanan, tanıklı maddeler
  trwikt       Türkçe Vikisözlük (kaikki.org çıkarımı) — Türkçe ve Osmanlıca maddeler, CC BY-SA
  enwikt-ota   İngilizce Vikisözlük, Osmanlı Türkçesi — Arap harfli yazılış ve köken, CC BY-SA
  enwikt-otk   İngilizce Vikisözlük, Eski Türkçe — Göktürk harfli maddeler, CC BY-SA

Kullanım:  python araclar/aktar.py
"""
import gzip
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
from cekirdek.normal import normal, ascii_, arap_normal, tanim_parcalari  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
HAM = KOK / "veri" / "ham"
DERLEME = KOK / "veri" / "derleme"
HEDEF = KOK / "veri" / "bengu.db"

SEMA = """
CREATE TABLE kaynak (id TEXT PRIMARY KEY, ad TEXT, kisa TEXT, lisans TEXT, url TEXT, aciklama TEXT, sira INTEGER);
CREATE TABLE kayit (
  id INTEGER PRIMARY KEY, baslik TEXT NOT NULL, norm TEXT NOT NULL, ascii TEXT NOT NULL,
  dil TEXT NOT NULL,            -- tr | ota | otk
  tur TEXT NOT NULL,            -- kelime | tamlama | söz öbeği | deyim | atasözü | sanat | özel ad | ek | kısaltma
  soz_turu TEXT,                -- kaynaktaki sözcük türü (Ad, Eylem, …)
  koken TEXT,                   -- T | Ar | Fa | Bt (Batı dilleri) | Diğer
  koken_ayrinti TEXT,
  osmanli TEXT, ceviri TEXT, eski_yazi TEXT,
  kaynak_id TEXT NOT NULL REFERENCES kaynak(id),
  aciklama_dili TEXT DEFAULT 'tr'  -- tanımlar İngilizceyse 'en'
);
CREATE TABLE kayit_donem (kayit_id INTEGER, donem TEXT);
CREATE TABLE anlam (kayit_id INTEGER, sira INTEGER, metin TEXT, etiket TEXT);
CREATE TABLE ornek (kayit_id INTEGER, anlam_sira INTEGER, metin TEXT, aciklama TEXT, ref TEXT,
                    yazar TEXT, eser TEXT, yuzyil TEXT, kaynak_turu TEXT);
CREATE TABLE ilgili (kayit_id INTEGER, baslik TEXT, tip TEXT);
CREATE TABLE cekim (norm TEXT, lemma TEXT);
CREATE TABLE yazar (id TEXT PRIMARY KEY, ad TEXT, gorunen TEXT, yasam TEXT, donem TEXT, gelenek TEXT, tur TEXT, biyografi TEXT);
CREATE TABLE eser (yazar_id TEXT, sira INTEGER, ad TEXT, tarih TEXT, tur TEXT, notu TEXT);
CREATE TABLE bilgi (anahtar TEXT PRIMARY KEY, deger TEXT);
CREATE TABLE ingilizce (tr_norm TEXT, en TEXT);          -- Türkçe kelimenin İngilizce karşılıkları (köprü için)
CREATE TABLE osmanli_dizin (ar_norm TEXT, kayit_id INTEGER); -- Arap harfiyle arama
CREATE TABLE karsilik (tr_norm TEXT, kayit_id INTEGER, puan REAL, yol TEXT);  -- Günümüz Türkçesi → Osmanlıca
-- Tanık metin derlemi (Vikikaynak): eser sayfaları ve satırları
CREATE TABLE metin (id INTEGER PRIMARY KEY, yazar_id TEXT, eser TEXT, sayfa TEXT, donem TEXT, gelenek TEXT, kaynak_id TEXT, url TEXT);
CREATE TABLE satir (id INTEGER PRIMARY KEY, metin_id INTEGER, sira INTEGER, kita INTEGER, metin TEXT, ceviri TEXT, eski_yazi TEXT);
CREATE TABLE satir_dizin (norm TEXT, satir_id INTEGER);
CREATE VIRTUAL TABLE satir_fts USING fts5(icerik, tokenize = 'unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE kayit_fts USING fts5(icerik, tokenize = 'unicode61 remove_diacritics 2');
"""
DIZINLER = """
CREATE INDEX i_kayit_norm ON kayit(norm);
CREATE INDEX i_kayit_ascii ON kayit(ascii);
CREATE INDEX i_kayit_tur ON kayit(tur);
CREATE INDEX i_donem ON kayit_donem(donem, kayit_id);
CREATE INDEX i_donem_k ON kayit_donem(kayit_id);
CREATE INDEX i_anlam ON anlam(kayit_id);
CREATE INDEX i_ornek ON ornek(kayit_id);
CREATE INDEX i_ornek_yazar ON ornek(yazar);
CREATE INDEX i_ilgili ON ilgili(kayit_id);
CREATE INDEX i_cekim ON cekim(norm);
CREATE INDEX i_ing ON ingilizce(tr_norm);
CREATE INDEX i_osm ON osmanli_dizin(ar_norm);
CREATE INDEX i_karsilik ON karsilik(tr_norm);
CREATE INDEX i_karsilik_k ON karsilik(kayit_id);
CREATE INDEX i_satir_dizin ON satir_dizin(norm);
CREATE INDEX i_satir_metin ON satir(metin_id, sira);
CREATE INDEX i_metin_yazar ON metin(yazar_id);
"""

KAYNAKLAR = [
    ("bengu", "Bengü Derlemesi", "Bengü", "Bengü", "", "Elle hazırlanmış, tanıklı maddeler (uzman denetimi bekliyor).", 0),
    ("trwikt", "Türkçe Vikisözlük", "Vikisözlük", "CC BY-SA 4.0", "https://tr.wiktionary.org",
     "Türkçe ve Osmanlıca maddeler; kaikki.org (wiktextract) çıkarımı.", 1),
    ("enwikt-ota", "İngilizce Vikisözlük — Osmanlı Türkçesi", "Wiktionary (ota)", "CC BY-SA 4.0", "https://en.wiktionary.org",
     "Arap harfli yazılış, köken ve İngilizce açıklamalar; kaikki.org çıkarımı.", 2),
    ("enwikt-otk", "İngilizce Vikisözlük — Eski Türkçe", "Wiktionary (otk)", "CC BY-SA 4.0", "https://en.wiktionary.org",
     "Göktürk harfli maddeler ve İngilizce açıklamalar; kaikki.org çıkarımı.", 3),
    ("vikikaynak", "Türkçe Vikikaynak", "Vikikaynak", "Kamu malı / CC BY-SA 4.0", "https://tr.wikisource.org",
     "Tanık metin derlemi: kamu malı edebî eserler (Orhun Yazıtları, Dede Korkut, Divan, Halk ve Tekke şiiri, Tanzimat sonrası). "
     "Yalnız ölümünün üzerinden 70 yıl geçmiş yazarlar alınmıştır.", 4),
    ("vikisoz", "Türkçe Vikisöz", "Vikisöz", "CC BY-SA 4.0", "https://tr.wikiquote.org",
     "“Türkçe atasözleri” listelerinden, başka kaynakta bulunmayan atasözü ve deyimler (açıklamaları henüz yok).", 5),
]

TUR_ESLE = {"Deyim": "deyim", "Atasözü": "atasözü", "Özel ad": "özel ad", "Son ek": "ek", "Ön ek": "ek",
            "Kısaltma": "kısaltma", "Kısaltmalar": "kısaltma"}
ATLA_TUR = {"Yanlış", "Harf", "Sembol"}
BOZUK = re.compile(r"çevirisi gerekiyor|^\W+$")  # Vikisözlük şablon artıkları
IZAFET = re.compile(r"\S-[ıiuüyı]\s|\S-[ıiuü]$|\S-yi\s| ü | u |-ı |-i ")
ARAP = re.compile(r"[؀-ۿ]")
BATI = {"Fransızca", "İtalyanca", "İngilizce", "Almanca", "Latince", "Yunanca", "Eski Yunanca", "İspanyolca",
        "Portekizce", "Rusça", "Lehçe", "Macarca", "Felemenkçe", "Pontus Rumcası", "Bulgarca", "Sırpça"}
TURKCE = {"Eski Türkçe", "Ana Türkçe", "Osmanlı Türkçesi", "Eski Anadolu Türkçesi", "Türkçe", "Moğolca"}


def koken_bul(kategoriler):
    """'Arapça kökenli Türkçe sözcükler' gibi kategorilerden köken çıkarır."""
    diller = []
    for c in kategoriler:
        m = re.match(r"(.+?) kökenli (Türkçe|Osmanlı Türkçesi) sözcükler$", c)
        if m:
            diller.append(m.group(1))
    if not diller:
        return None, None
    ayr = ", ".join(dict.fromkeys(diller))
    if "Arapça" in diller:
        return "Ar", ayr
    if "Farsça" in diller:
        return "Fa", ayr
    if any(d in BATI for d in diller):
        return "Bt", ayr
    if all(d in TURKCE for d in diller):
        return "T", ayr
    return "Diğer", ayr


def koken_ing(ety):
    """İngilizce Vikisözlük etimoloji metninden köken."""
    if not ety:
        return None
    ilk = ety.split(".")[0]
    for anahtar, kod in (("Arabic", "Ar"), ("Persian", "Fa"), ("French", "Bt"), ("Italian", "Bt"),
                         ("Greek", "Bt"), ("Latin", "Bt"), ("Proto-Turkic", "T"), ("Old Anatolian Turkish", "T"),
                         ("Old Turkic", "T"), ("Inherited", "T")):
        if anahtar in ilk:
            return kod
    return None


def donemler(dil, koken, ayr):
    """Otomatik dönem ataması (kaba sezgisel; uzman düzeltmesine açık)."""
    if dil == "otk":
        return ["islam-oncesi"]
    if dil == "ota":
        return ["islami"]
    d = []
    if ayr and ("Eski Türkçe" in ayr or "Ana Türkçe" in ayr):
        d.append("islam-oncesi")
    if koken in ("Ar", "Fa") or (ayr and "Osmanlı Türkçesi" in ayr):
        d.append("islami")
    if koken == "Bt":
        d.append("bati")
    return d or ["gunumuz"]


def ref_ayir(ref):
    if not ref:
        return None, None
    p = [x.strip() for x in ref.split(",")]
    return p[0] or None, (p[1] if len(p) > 1 else None)


class Yazici:
    def __init__(self, db):
        self.db = db
        self.sayac = 0

    def kayit(self, *, baslik, dil, tur, kaynak, soz_turu=None, koken=None, koken_ayrinti=None, osmanli=None,
              ceviri=None, eski_yazi=None, aciklama_dili="tr", anlamlar=(), ornekler=(), ilgililer=(), donem=()):
        c = self.db.execute(
            "INSERT INTO kayit (baslik,norm,ascii,dil,tur,soz_turu,koken,koken_ayrinti,osmanli,ceviri,eski_yazi,kaynak_id,aciklama_dili)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (baslik, normal(baslik), ascii_(baslik), dil, tur, soz_turu, koken, koken_ayrinti, osmanli, ceviri,
             eski_yazi, kaynak, aciklama_dili))
        kid = c.lastrowid
        self.db.executemany("INSERT INTO kayit_donem VALUES (?,?)", [(kid, d) for d in dict.fromkeys(donem)])
        self.db.executemany("INSERT INTO anlam VALUES (?,?,?,?)", [(kid, i, m, e) for i, (m, e) in enumerate(anlamlar)])
        self.db.executemany("INSERT INTO ornek VALUES (?,?,?,?,?,?,?,?,?)", [(kid, *o) for o in ornekler])
        self.db.executemany("INSERT INTO ilgili VALUES (?,?,?)", [(kid, b, t) for b, t in ilgililer])
        metin = " ".join([baslik, ceviri or ""] + [m for m, _ in anlamlar] + [o[1] or "" for o in ornekler] +
                         [o[3] or "" for o in ornekler])
        self.db.execute("INSERT INTO kayit_fts(rowid, icerik) VALUES (?,?)", (kid, ascii_(metin)))
        self.sayac += 1
        return kid


def aktar_derleme(y: Yazici, db):
    maddeler = json.loads((DERLEME / "maddeler.json").read_text(encoding="utf-8"))
    idden = {m["id"]: m["madde"] for m in maddeler}
    for m in maddeler:
        dil = "otk" if m["donem"] == ["islam-oncesi"] else "tr"
        yz = m.get("yazilis", {})
        ornekler = [(0, o["metin"], o.get("aciklama"), None, o["kaynak"]["yazar"], o["kaynak"]["eser"],
                     o["kaynak"]["yuzyil"], o["kaynak"]["tur"]) for o in m.get("ornekler", [])]
        ilg = [(t, "tamlama") for t in m.get("tamlamalar", [])] + [(d, "deyim") for d in m.get("deyimler", [])] + \
              [(idden[i], "ilgili") for i in m.get("ilgili", []) if i in idden]
        y.kayit(baslik=m["madde"], dil=dil, tur=m["tur"], kaynak="bengu", koken=m["koken"],
                osmanli=yz.get("osmanli"), ceviri=yz.get("ceviri") or yz.get("eski"),
                anlamlar=[(a, None) for a in m["anlamlar"]], ornekler=ornekler, ilgililer=ilg, donem=m["donem"])
    tum_yazarlar = json.loads((DERLEME / "yazarlar.json").read_text(encoding="utf-8")) + \
        json.loads((DERLEME / "yazarlar_ek.json").read_text(encoding="utf-8"))
    for y_ in tum_yazarlar:
        db.execute("INSERT INTO yazar VALUES (?,?,?,?,?,?,?,?)",
                   (y_["id"], y_["ad"], y_.get("gorunen"), y_["yasam"], y_["donem"], y_["gelenek"],
                    ",".join(y_["tur"]), y_["biyografi"]))
        db.executemany("INSERT INTO eser VALUES (?,?,?,?,?,?)",
                       [(y_["id"], i, e["ad"], e["tarih"], e["tur"], e.get("not")) for i, e in enumerate(y_["eserler"])])
    print(f"  Bengü derlemesi: {len(maddeler)} madde")


def aktar_trwikt(y: Yazici, db, osm_harita):
    yol = HAM / "trwiktionary" / "trwiktionary.jsonl.gz"
    n = cekim = ota = 0
    cekimler, ingilizce = [], []
    with gzip.open(yol, "rt", encoding="utf-8") as f:
        for satir in f:
            d = json.loads(satir)
            lc = d.get("lang_code")
            if lc not in ("tr", "ota"):
                continue
            kelime = d.get("word", "").strip()
            anlamlar_ham = d.get("senses", [])
            if not kelime or BOZUK.search(kelime):
                continue
            if lc == "tr":
                for t in d.get("translations", []):
                    if t.get("lang_code") == "en" and t.get("word"):
                        ingilizce.append((normal(kelime), t["word"].strip().lower()))
            # Çekimli biçim maddeleri → kök bulma sözlüğü
            if lc == "tr" and anlamlar_ham and all(s.get("form_of") for s in anlamlar_ham):
                for s in anlamlar_ham:
                    for fo in s["form_of"]:
                        if fo.get("word"):
                            cekimler.append((normal(kelime), fo["word"]))
                cekim += 1
                continue
            pt = d.get("pos_title") or ""
            if pt in ATLA_TUR:
                continue
            anlamlar, ornekler = [], []
            for i, s in enumerate(anlamlar_ham):
                gl = "; ".join(g for g in s.get("glosses", []) if g)
                if not gl:
                    continue
                etk = ", ".join(s.get("raw_tags", []) + [c.replace("Türkçede ", "").replace("Türkçe ", "")
                                                          for c in s.get("categories", [])][:2]) or None
                anlamlar.append((gl, etk))
                for e in s.get("examples", [])[:3]:
                    if not e.get("text"):
                        continue
                    yz, es = ref_ayir(e.get("ref"))
                    ornekler.append((len(anlamlar) - 1, e["text"], e.get("translation"), e.get("ref"), yz, es, None, None))
            if not anlamlar:
                continue
            koken, ayr = koken_bul(d.get("categories", []))
            ilg = []
            for anahtar, tip in (("idioms", "deyim"), ("proverbs", "atasözü"), ("derived", "türev"),
                                 ("related", "ilgili"), ("synonyms", "eş anlamlı"), ("antonyms", "zıt anlamlı")):
                ilg += [(x["word"], tip) for x in d.get(anahtar, [])[:25] if x.get("word")]
            tur = TUR_ESLE.get(pt)
            if not tur:
                tur = "tamlama" if IZAFET.search(kelime + " ") else ("söz öbeği" if " " in kelime else "kelime")
            if lc == "ota":
                cev = next((fm["form"] for fm in d.get("forms", []) if "transliteration" in fm.get("tags", [])), None)
                arap = kelime if ARAP.search(kelime) else next(
                    (fm["form"] for fm in d.get("forms", []) if ARAP.search(fm.get("form", ""))), None)
                baslik = cev or (kelime if not ARAP.search(kelime) else None)
                if not baslik:
                    continue
                if arap:
                    osm_harita.setdefault(normal(baslik), arap)
                y.kayit(baslik=baslik, dil="ota", tur=tur, kaynak="trwikt", soz_turu=pt, koken=koken, koken_ayrinti=ayr,
                        osmanli=arap, anlamlar=anlamlar, ornekler=ornekler, ilgililer=ilg,
                        donem=donemler("ota", koken, ayr))
                ota += 1
            else:
                arap = next((fm["form"] for fm in d.get("forms", []) if ARAP.search(fm.get("form", ""))), None)
                y.kayit(baslik=kelime, dil="tr", tur=tur, kaynak="trwikt", soz_turu=pt, koken=koken, koken_ayrinti=ayr,
                        osmanli=arap, anlamlar=anlamlar, ornekler=ornekler, ilgililer=ilg,
                        donem=donemler("tr", koken, ayr))
                n += 1
            if (n + ota) % 50000 == 0:
                print(f"    … {n + ota} kayıt")
    db.executemany("INSERT INTO cekim VALUES (?,?)", cekimler)
    db.executemany("INSERT INTO ingilizce VALUES (?,?)", ingilizce)
    print(f"  Türkçe Vikisözlük: {n} Türkçe, {ota} Osmanlıca kayıt; {len(cekimler)} çekimli biçim")


def aktar_enwikt_ota(y: Yazici, osm_harita, koken_harita):
    n = 0
    with open(HAM / "kaikki-ota" / "ota.jsonl", encoding="utf-8") as f:
        for satir in f:
            d = json.loads(satir)
            if d.get("pos") in ("romanization", "character", "symbol"):
                continue
            arap = d.get("word", "")
            if not ARAP.search(arap):
                continue
            latin = next((fm["form"] for fm in d.get("forms", []) if "romanization" in fm.get("tags", [])), None)
            if not latin:
                continue
            kk = koken_ing(d.get("etymology_text"))
            hedefler = {normal(latin)} | {normal(x["word"]) for x in d.get("descendants", [])
                                          if x.get("lang_code") == "tr" and x.get("word")}
            for h in hedefler:
                osm_harita.setdefault(h, arap)
                if kk:
                    koken_harita.setdefault(h, kk)
            anlamlar = [("; ".join(s.get("glosses", [])), "İngilizce açıklama") for s in d.get("senses", [])
                        if s.get("glosses") and "form-of" not in s.get("tags", [])]
            if not anlamlar:
                continue
            ayr = (d.get("etymology_text") or "").split("\n")[-1][:300] or None
            y.kayit(baslik=latin, dil="ota", tur="kelime", kaynak="enwikt-ota", soz_turu=d.get("pos"), koken=kk,
                    koken_ayrinti=ayr, osmanli=arap, ceviri=latin, aciklama_dili="en", anlamlar=anlamlar,
                    donem=["islami"])
            n += 1
    print(f"  İngilizce Vikisözlük (Osmanlıca): {n} kayıt")


def aktar_enwikt_otk(y: Yazici):
    n = 0
    with open(HAM / "kaikki-otk" / "otk.jsonl", encoding="utf-8") as f:
        for satir in f:
            d = json.loads(satir)
            if d.get("pos") in ("romanization", "character", "symbol"):
                continue
            yazi = d.get("word", "")
            latin = next((fm["form"] for fm in d.get("forms", []) if "romanization" in fm.get("tags", [])), None)
            if not latin:
                latin = next((t["args"].get("tr") for t in d.get("head_templates", []) if t.get("args", {}).get("tr")), None)
            if not latin:
                if re.search(r"[\U00010C00-\U00010C4F]", yazi):
                    continue
                latin, yazi = yazi, None
            anlamlar = [("; ".join(s.get("glosses", [])), "İngilizce açıklama") for s in d.get("senses", [])
                        if s.get("glosses") and "form-of" not in s.get("tags", [])]
            if not anlamlar:
                continue
            y.kayit(baslik=latin, dil="otk", tur="kelime", kaynak="enwikt-otk", soz_turu=d.get("pos"), koken="T",
                    eski_yazi=yazi, ceviri=latin, aciklama_dili="en", anlamlar=anlamlar, donem=["islam-oncesi"])
            n += 1
    print(f"  İngilizce Vikisözlük (Eski Türkçe): {n} kayıt")


def zenginlestir(db, osm_harita, koken_harita):
    """Arap harfli yazılışı ya da kökeni olmayan Türkçe kayıtları Osmanlıca kaynaklardan tamamlar."""
    s1 = s2 = 0
    satirlar = db.execute("SELECT id, norm, koken FROM kayit WHERE dil='tr' AND kaynak_id='trwikt' AND tur!='özel ad' AND (osmanli IS NULL OR koken IS NULL)").fetchall()
    for kid, norm, koken in satirlar:
        if norm in osm_harita:
            s1 += db.execute("UPDATE kayit SET osmanli=? WHERE id=? AND osmanli IS NULL", (osm_harita[norm], kid)).rowcount
        if koken is None and norm in koken_harita:
            kk = koken_harita[norm]
            db.execute("UPDATE kayit SET koken=?, koken_ayrinti=COALESCE(koken_ayrinti,'Wiktionary etimolojisinden') WHERE id=?", (kk, kid))
            if kk in ("Ar", "Fa"):
                db.execute("DELETE FROM kayit_donem WHERE kayit_id=? AND donem='gunumuz'", (kid,))
                db.execute("INSERT INTO kayit_donem VALUES (?, 'islami')", (kid,))
            s2 += 1
    print(f"  Zenginleştirme: {s1} kayda Arap harfli yazılış, {s2} kayda köken eklendi")


def kur_osmanli_dizin(db):
    satirlar = db.execute("SELECT id, osmanli FROM kayit WHERE osmanli IS NOT NULL").fetchall()
    db.executemany("INSERT INTO osmanli_dizin VALUES (?,?)", [(arap_normal(o), i) for i, o in satirlar])
    print(f"  Arap harfi dizini: {len(satirlar)} kayıt")


def kur_karsilik(db):
    """Günümüz Türkçesi kelimesi → Osmanlıca (Osmanlı Türkçesi, Arapça/Farsça kökenli) kayıt eşleştirmesi.

    yol: 'tanım'      — kaydın Türkçe tanımında kelime doğrudan geçiyor ("hasret: özlem")
         'eş anlamlı' — Vikisözlük eş anlamlı bağlantısı
         'İngilizce'  — İngilizce köprü (özlem → longing → iştiyak); en düşük güven
    """
    # Kökeni boş ama Osmanlıca yazılışı belgelenmiş kelimeler de Osmanlıca karşılık sayılır (firâk, firkat …)
    osm_kosul = ("(k.dil='ota' OR k.koken IN ('Ar','Fa') OR (k.koken IS NULL AND k.osmanli IS NOT NULL AND k.dil='tr'))"
                 " AND k.tur NOT IN ('özel ad','kısaltma','ek')")
    satirlar = []
    # 1) Tanımlar
    for kid, sira, metin in db.execute(f"""SELECT k.id, a.sira, a.metin FROM kayit k JOIN anlam a ON a.kayit_id=k.id
                                         WHERE {osm_kosul} AND k.aciklama_dili='tr'"""):
        parcalar = tanim_parcalari(metin)
        for j, p in enumerate(parcalar):
            puan = 3.0 if len(parcalar) == 1 else 2.6 - 0.1 * min(j, 5)
            if sira > 0:
                puan -= 0.3
            satirlar.append((p, kid, puan, "tanım"))
    # 2) Eş anlamlılar (iki yönlü)
    norm_id = {}
    for kid, norm, osm in db.execute(f"SELECT k.id, k.norm, ({osm_kosul}) FROM kayit k WHERE k.tur!='özel ad'"):
        norm_id.setdefault(norm, []).append((kid, osm))
    for kid, norm, osm, es in db.execute(f"""SELECT k.id, k.norm, ({osm_kosul}), i.baslik FROM ilgili i JOIN kayit k ON k.id=i.kayit_id
                                           WHERE i.tip='eş anlamlı'"""):
        en = normal(es)
        if osm:
            satirlar.append((en, kid, 2.4, "eş anlamlı"))
        for kid2, osm2 in norm_id.get(en, []):
            if osm2:
                satirlar.append((norm, kid2, 2.4, "eş anlamlı"))
    # 3) İngilizce köprü: İngilizce açıklamalı Osmanlıca kayıtların açıklama parçaları
    en_harita = {}
    for kid, metin in db.execute("""SELECT k.id, a.metin FROM kayit k JOIN anlam a ON a.kayit_id=k.id
                                    WHERE k.kaynak_id='enwikt-ota' AND a.sira < 3"""):
        for p in re.split(r"[;,]", re.sub(r"\([^)]*\)", "", metin)):
            p = p.strip().lower().removeprefix("to ").removeprefix("a ").removeprefix("an ").removeprefix("the ")
            if p and len(p.split()) <= 2:
                en_harita.setdefault(p, set()).add(kid)
    kopru = 0
    for tr_norm, en in db.execute("SELECT DISTINCT tr_norm, en FROM ingilizce"):
        en = en.removeprefix("to ")
        ids = en_harita.get(en, ())
        if 0 < len(ids) <= 8:  # çok anlamlı İngilizce kelimeler gürültü üretir
            for kid in ids:
                satirlar.append((tr_norm, kid, 1.2, "İngilizce"))
                kopru += 1
    # Aynı kelimenin kendisini karşılık sayma
    kendi = {kid: norm for norm, l in norm_id.items() for kid, _ in l}
    satirlar = [s for s in satirlar if kendi.get(s[1]) != s[0] and s[0]]
    db.executemany("INSERT INTO karsilik VALUES (?,?,?,?)", satirlar)
    print(f"  Karşılık tablosu: {len(satirlar)} eşleşme (İngilizce köprü: {kopru})")


def aktar_vikisoz(y: Yazici, db):
    """Vikisöz 'Türkçe atasözleri/A…Z' listeleri: veritabanında olmayan atasözü ve deyimler eklenir (açıklamasız)."""
    import xml.etree.ElementTree as ET
    import bz2
    var = {r[0] for r in db.execute("SELECT norm FROM kayit WHERE tur IN ('atasözü','deyim','söz öbeği')")}
    n = 0
    for _, el in ET.iterparse(bz2.open(HAM / "vikisoz" / "trwikiquote.xml.bz2"), events=("end",)):
        if not el.tag.endswith("}page"):
            continue
        baslik = el.find("{*}title").text
        txt = el.find("{*}revision/{*}text").text or ""
        el.clear()
        if not re.match(r"Türkçe atasözleri/", baslik):
            continue
        for satir in re.findall(r"^\*\s*(.+)$", txt, flags=re.M):
            s = re.sub(r"\{\{[^}]*\}\}", "", satir)
            s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
            s = re.sub(r"'{2,}|<[^>]+>", "", s).strip(" -–")
            if not (4 <= len(s) <= 160) or ":" in s or "http" in s or normal(s) in var:
                continue
            var.add(normal(s))
            tur = "atasözü" if s.rstrip()[-1:] in ".?!" else "deyim"
            y.kayit(baslik=s, dil="tr", tur=tur, kaynak="vikisoz", anlamlar=[], donem=["gunumuz"])
            n += 1
    print(f"  Vikisöz: {n} yeni atasözü / deyim")


KELIME = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîûÊêÔôÑñŊŋ]+")


def aktar_vikikaynak(db):
    """Vikikaynak tanık derlemi + kelime → satır dizini (çekimli biçimler sözlük biçimine bağlanır)."""
    import urllib.parse
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import vikikaynak
    lemma = {}
    for form, lem in db.execute("SELECT norm, lemma FROM cekim"):
        lemma.setdefault(form, set()).add(normal(lem))
    gecerli = {r[0] for r in db.execute("SELECT DISTINCT norm FROM kayit WHERE norm NOT LIKE '% %'")}
    sayfa = satir_say = 0
    dizin = []
    for ad, yid, donem, gelenek, eser, baslik, satirlar in vikikaynak.metinler():
        url = "https://tr.wikisource.org/wiki/" + urllib.parse.quote(baslik.replace(" ", "_"))
        mid = db.execute("INSERT INTO metin (yazar_id,eser,sayfa,donem,gelenek,kaynak_id,url) VALUES (?,?,?,?,?,?,?)",
                         (yid, eser, baslik, donem, gelenek, "vikikaynak", url)).lastrowid
        sayfa += 1
        for i, s in enumerate(satirlar):
            kita, metin = s[0], s[1]
            ceviri = s[2] if len(s) > 2 else None
            yazi = s[3] if len(s) > 3 else None
            if len(s) > 2:
                metin = metin.lower().replace("i̇", "i")  # Orhun çeviri yazısı büyük harfli
            sid = db.execute("INSERT INTO satir (metin_id,sira,kita,metin,ceviri,eski_yazi) VALUES (?,?,?,?,?,?)",
                             (mid, i, kita, metin, ceviri, yazi)).lastrowid
            satir_say += 1
            normlar = set()
            for k in KELIME.findall(metin):
                n = normal(k)
                if len(n) < 2:
                    continue
                normlar.add(n)
                if "ñ" in k.lower() or "ŋ" in k.lower():  # Eski Türkçe: teñri → tengri
                    normlar.add(normal(k.lower().replace("ñ", "ng").replace("ŋ", "ng")))
                normlar |= lemma.get(n, set())
            dizin += [(n, sid) for n in normlar if n in gecerli]
            db.execute("INSERT INTO satir_fts(rowid, icerik) VALUES (?,?)", (sid, ascii_(metin)))
    db.executemany("INSERT INTO satir_dizin VALUES (?,?)", dizin)
    print(f"  Vikikaynak: {sayfa} eser sayfası, {satir_say} satır, {len(dizin)} kelime bağlantısı")


def main():
    t0 = time.time()
    gecici = HEDEF.with_suffix(".db.yeni")
    gecici.unlink(missing_ok=True)
    db = sqlite3.connect(gecici)
    db.executescript("PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;" + SEMA)
    db.executemany("INSERT INTO kaynak VALUES (?,?,?,?,?,?,?)", KAYNAKLAR)
    y = Yazici(db)
    osm_harita, koken_harita = {}, {}
    print("Aktarım başladı…")
    aktar_derleme(y, db)
    aktar_trwikt(y, db, osm_harita)
    aktar_enwikt_ota(y, osm_harita, koken_harita)
    aktar_enwikt_otk(y)
    zenginlestir(db, osm_harita, koken_harita)
    aktar_vikisoz(y, db)
    kur_osmanli_dizin(db)
    kur_karsilik(db)
    aktar_vikikaynak(db)
    print("  Dizinler oluşturuluyor…")
    db.executescript(DIZINLER)
    db.execute("INSERT INTO kayit_fts(kayit_fts) VALUES ('optimize')")
    db.execute("INSERT INTO bilgi VALUES ('olusturma', ?)", (time.strftime("%Y-%m-%d %H:%M"),))
    db.commit()
    db.execute("VACUUM")
    db.close()
    HEDEF.unlink(missing_ok=True)
    gecici.rename(HEDEF)
    print(f"Bitti: {y.sayac} kayıt, {HEDEF.stat().st_size / 1e6:.0f} MB, {time.time() - t0:.0f} sn")


if __name__ == "__main__":
    main()
