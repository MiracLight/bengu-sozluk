"""Bengü Rehber — doğal dildeki soruyu anlayıp doğru aramaya çeviren katman.

İki parçadan oluşur:
  1. Kural tabanlı çözümleyici (her bilgisayarda, modelsiz, anında): niyet + kavram + süzgeçler (köken, tür, yazar, dönem)
  2. Anlamsal arama (cekirdek/anlam.py, isteğe bağlı): kavramı sözlükteki tanımıyla genişletip anlamca yakın
     kayıtları / beyitleri bulur.
Rehber hiçbir zaman tanım ya da metin üretmez; döndürdüğü her şey sözlükteki kaynaklı kayıtlardır.
"""
import re
import sqlite3

from . import anlam, arama, ceviri, cozumleme
from .normal import normal, arap_mi, tanim_parcalari

KOKEN_SOZ = [(r"\bfarsca\b|\bfarsi\b|\bacemce\b", "Fa"), (r"\barapca\b", "Ar"),
             (r"\boz turkce\b|\bturkce kokenli\b|\bturk kokenli\b", "T"),
             (r"\bfransizca\b|\bbati dil|\bitalyanca\b|\bingilizce kokenli\b", "Bt")]
TUR_SOZ = [(r"\batasoz", "atasözü"), (r"\bdeyim", "deyim"), (r"\btamlama", "tamlama")]
TANIK_SOZ = r"\bbeyit|\bbeyti|\bdize|\bmisra|\bsiir|\bgecen\b|\bgectigi\b|\bgecti\b|\bkullandigi\b|\btanik|\bdortluk|\byazit"
DONEM_SOZ = [(r"islamiyet oncesi\w*|islam oncesi\w*|gokturk\w*|orhun( yazit\w*)?|eski turk\w*|\byazit\w*", ("donem", "islam-oncesi")),
             (r"\bkarahanli\w*|kutadgu|gecis donem\w*", ("donem", "gecis")),
             (r"\bdivan (siir|edebiyat)\w*|\bdivan\b|\bklasik (siir|edebiyat)\w*", ("gelenek", "Divan")),
             (r"\bhalk (siir|edebiyat|ozan)\w*|\basik\b", ("gelenek", "Halk")),
             (r"\btekke\w*|\btasavvuf\w*|\bsufi\b|\balevi\w*|\bbektasi\w*", ("gelenek", "Tekke")),
             (r"\btanzimat\w*|servet.i funun\w*|\bfecr\w*|\bmilli edebiyat\w*|\bbati etkisi\w*|\bmesrutiyet\w*", ("donem", "bati")),
             (r"\bcumhuriyet\w*|\bgunumuz\w*", ("donem", "gunumuz"))]
OSM_KARSILIK = r"osmanlica(si|sini|ca)?\b|osmanlica karsilig|eski (dilde|turkcede|soyleyis)|karsilig|yerine kullan"
# Yeni niyetler
COZUMLE_SOZ = (r"^(cozumle|coz|acikla|sadelestir|tahlil et)\b|\b(beyti|beytin|misrayi|misrain|dizeyi|ifadeyi|tamlamayi|siiri) "
               r"(cozumle|acikla|sadelestir|tahlil)|gunumuz turkcesine (cevir|aktar)|ne anlatiyor")
KAFIYE_DESEN = [
    (r"[\"“]?-?([^\s\"”]+)[\"”]? (?:ile|iyle|yla|la|le|ekiyle|hecesiyle) (?:biten|sonlanan|biter)", "son"),
    (r"[\"“]?-?([^\s\"”]+)[\"”]? (?:ile|iyle|yla|la|le) (?:baslayan|baslar)", "bas"),
    (r"[\"“]?([^\s\"”]+)[\"”]? (?:ile |kelimesiyle |kelimesine |sozcugune |ya |ye |a |e )?(?:kafiyeli|uyakli|kafiye|uyak)", "kafiye"),
]
KARSILASTIR = [r"(\S+) (?:ile|ve) (\S+?) (?:arasindaki fark|arasinda ne fark|arasindaki ayrim|farki\b|farklari|nasil ayrilir|karsilastir)",
               r"(\S+) (?:ile|ve) (\S+?)(?:yi|yı|i|ı|u|ü)? karsilastir"]
KOKEN_DESEN = r"(\S+?)(?: kelimesinin| sozcugunun)? (?:kokeni|koken|etimoloji|nereden gel|hangi dilden|asli ne|aslı ne)"
ILGILI_DESEN = r"(\S+?)(?: kelimesinin| sozcugunun)? (es ?anlamli|zit ?anlamli|karsit ?anlamli|karsiti|ziddi|benzer anlamli)"
YAZAR_SORU = r"\bkimdir\b|\bhayati\b|\bbiyografi|\beserleri\b|\bne yazmis|\bnerede dog|\bkim\b"
YAZARLAR_SORU = r"\b(sairleri|sairler|yazarlari|yazarlar|ozanlari|ozanlar|edebiyatcilari|temsilcileri)\b"
ANLAM_SORU = (r"\bne demek|\banlami\b|\banlamini\b|\banlamlari\b|\bmanasi\b|\bnedir\b|\bne anlama gel|gunumuz turkcesi|"
              r"bugunku karsilig|turkcesi (ne|nedir)")
ANLAMINDA = r"(.+?)\s+(?:anlamina gelen|anlamina gelir|anlamindaki|anlaminda|manasina gelen|manasinda|demek olan|karsiligi olan)"
KONULU = r"(.+?)\s+(?:ile ilgili|hakkinda|konulu|temali|uzerine|anlatan|islenen|isleyen|uzerineki)"
DOLGU = set("""bir bu su o ve ile icin gibi kadar en cok daha hangi ne neler nedir nelerdir mi mu mı mü var mi
    bana bize lutfen goster listele bul ara soyle yaz verir misin ver olan olarak kelime kelimeler kelimesi sozcuk sozcukler
    sozcugu soz sozler sozleri ifade ifadeler ornek ornekler ornekleri tane birkac bazi tum butun nasil denir der dendi
    turkce turkcede edebiyat edebiyatta edebiyatinda siir siiri siirleri siirlerinde siirde beyit beyitler beyitleri beyti dize dizeler
    misra misralar kelimeyi geceni gecen gectigi gecti kullandigi kullanilan karsiligi karsiliklari osmanlica osmanlicasi osmanlicada
    farsca arapca kokenli koken kokenden ozturkce oz atasozu atasozleri atasozunu deyim deyimler deyimleri tamlama tamlamalar
    anlami anlamina anlaminda anlamindaki gelen gelir demek ne nedir yazari sairi sairin yazarin divan halk tekke tanzimat
    donem doneminde donemi dair hakkinda ilgili konulu temali uzerine anlatan kelimesinin kelimesi sozcugunun sozcugu
    siirlerinde siirlerindeki siirinde metinlerde metinlerinde eserlerinde eserinde manasi anlamini anlamlari""".split())


def _yazar_bul(db, q):
    """Sorgudaki yazar adını (tam ad, görünen ad ya da kısa adı) bulur."""
    adaylar = []
    for y in db.execute("SELECT id, ad, gorunen FROM yazar"):
        adlar = {normal(y["ad"]), normal(y["gorunen"] or "")}
        adlar |= {normal(re.sub(r"\(.*?\)", "", a)).strip() for a in (y["ad"], y["gorunen"] or "")}
        kisa = {"yunus-emre": "yunus", "mehmet-akif": "akif", "pir-sultan": "pir sultan", "namik-kemal": "namik kemal",
                "tevfik-fikret": "fikret", "seyh-galib": "galib", "yollug-tigin": "kul tigin", "dede-korkut": "dede korkut",
                "kanuni": "muhibbi", "fatih": "avni", "hatayi": "hatayi", "ahmet-hasim": "hasim", "orhan-veli": "orhan veli",
                "omer-seyfettin": "omer seyfettin", "ziya-gokalp": "gokalp", "yusuf-has-hacib": "yusuf has hacib",
                "kasgarli-mahmud": "kasgarli"}.get(y["id"])
        if kisa:
            adlar.add(kisa)
        for a in adlar:
            a = _asc(a)
            if a and len(a) >= 3 and re.search(r"\b" + re.escape(a), q):
                adaylar.append((len(a), y["id"], y["gorunen"] or y["ad"], a))
    if not adaylar:
        return None
    adaylar.sort(reverse=True)
    return adaylar[0][1:]


def _kavram(q, sil):
    """Süzgeç kelimeleri ve dolgu kelimeleri atıldıktan sonra kalan içerik: aranan kavram."""
    for s in sil:
        q = re.sub(re.escape(s), " ", q)
    q = re.sub(r"\b(in|nin|nun|nün|un|ün|ın|nın|da|de|ta|te|dan|den|tan|ten|a|e|ya|ye|yi|yı|yu|yü|i|ı|u|ü)\b", " ", q)
    kelimeler = [k for k in q.split() if k not in DOLGU and len(k) > 1]
    return " ".join(kelimeler).strip()


EKLER = sorted("""la le yla yle nin nın nun nün in ın un ün si sı su sü yi yı yu yü i ı u ü a e ya ye da de ta te dan den
    tan ten lar ler ları leri ların lerin larda lerde lardan lerden larında lerinde ında inde unda ünde sında sinde
    ını ini unu ünü sını sini nda nde ndan nden yla yle ca ce ça çe""".split(), key=len, reverse=True)


def _sozluk_bicimi(db, k):
    """'sabırla' → sabır, 'savaşın' → savaş, 'yazıtlarında' → yazıt. Önce sözlükte, sonra çekim sözlüğünde,
    en son bilinen ekleri atarak (sonuç sözlükte varsa) dener."""
    n = normal(k)
    if db.execute("SELECT 1 FROM kayit WHERE norm=? AND tur!='özel ad' LIMIT 1", (n,)).fetchone():
        return n
    r = db.execute("SELECT lemma FROM cekim WHERE norm=? LIMIT 1", (n,)).fetchone()
    if r:
        return normal(r[0])
    for ek in EKLER:
        if n.endswith(ek) and len(n) - len(ek) >= 3:
            kok = n[:-len(ek)]
            for aday in (kok, kok[:-1] + {"b": "p", "c": "ç", "d": "t", "ğ": "k"}.get(kok[-1], kok[-1])):  # ünsüz yumuşaması
                if db.execute("SELECT 1 FROM kayit WHERE norm=? AND tur!='özel ad' LIMIT 1", (aday,)).fetchone():
                    return aday
                # sabırla → sabr+la? ünlü düşmesi: sabır
                if len(aday) >= 3 and db.execute("SELECT 1 FROM kayit WHERE norm=? LIMIT 1", (aday[:-1] + "ı" + aday[-1],)).fetchone():
                    return aday[:-1] + "ı" + aday[-1]
    return n


def cozumle(db, soru):
    """Soru → {niyet, kavram, suzgec, anlasilan(etiketler)}"""
    ham = re.sub(r"['’‘`]", " ", soru.strip())  # kesme işareti: Fuzûlî'nin → Fuzûlî nin
    q = _asc(normal(ham))
    suzgec, anlasilan, sil = {}, [], []

    for desen, kod in KOKEN_SOZ:
        m = re.search(desen, q)
        if m:
            suzgec["koken"] = kod
            anlasilan.append({"tip": "koken", "deger": kod, "etiket": "Köken: " + {"Fa": "Farsça", "Ar": "Arapça", "T": "Türkçe", "Bt": "Batı dilleri"}[kod]})
            sil.append(m.group(0))
            break
    for desen, tur in TUR_SOZ:
        if re.search(desen, q):
            suzgec["tur"] = tur
            anlasilan.append({"tip": "tur", "deger": tur, "etiket": "Tür: " + tur})
            break
    for desen, (alan, deger) in DONEM_SOZ:
        m = re.search(desen, q)
        if m:
            suzgec[alan] = deger
            etk = {"islam-oncesi": "İslamiyet öncesi", "gecis": "Geçiş dönemi", "bati": "Batı etkisi", "gunumuz": "Günümüz",
                   "Divan": "Divan şiiri", "Halk": "Halk şiiri", "Tekke": "Tekke / Tasavvuf"}[deger]
            anlasilan.append({"tip": alan, "deger": deger, "etiket": ("Dönem: " if alan == "donem" else "Gelenek: ") + etk})
            sil.append(m.group(0))
            break
    if re.search(r"\bosmanlica\b|\beski (kelime|sozcuk|turkce)", q) and "koken" not in suzgec:
        suzgec["osm"] = True
        anlasilan.append({"tip": "osm", "deger": True, "etiket": "Dil: Osmanlıca (Arapça/Farsça kökenli dahil)"})
    y = _yazar_bul(db, q)
    if y:
        suzgec["yazar"] = y[0]
        anlasilan.append({"tip": "yazar", "deger": y[0], "etiket": "Yazar: " + y[1]})
        sil.append(y[2])

    # --- Yeni niyetler (öncelikli) ---
    ek = {}
    m_coz = re.search(COZUMLE_SOZ, q)
    izafetli = len(re.findall(r"\w-[ıiuü]\b|[âîûÂÎÛ]", soru)) >= 2 and len(soru.split()) >= 4
    if m_coz or (izafetli and not re.search(TANIK_SOZ + "|" + ANLAM_SORU + "|" + OSM_KARSILIK, q)):
        metin = soru.split(":", 1)[1] if ":" in soru else (re.search(r"[\"“](.+?)[\"”]", soru).group(1) if re.search(r"[\"“](.+?)[\"”]", soru) else
                re.sub(r"(?i)^\s*(çözümle|çöz|açıkla|sadeleştir|tahlil et)\s*", "", soru))
        return {"niyet": "cozumle", "kavram": metin.strip(), "suzgec": suzgec, "anlasilan": anlasilan, "konulu": False, "ek": {"metin": metin.strip()}}
    if not arap_mi(ham):
        for desen, kip in KAFIYE_DESEN:
            m = re.search(desen, q)
            if m and normal(m.group(1)) not in DOLGU:
                ek = {"kip": kip, "parca": _turkce_geri(ham, m.group(1).strip("-")) if kip == "kafiye" else _turkce_geri(ham, m.group(1).strip("-"))}
                return {"niyet": "kafiye", "kavram": ek["parca"], "suzgec": suzgec, "anlasilan": anlasilan, "konulu": False, "ek": ek}
        for desen in KARSILASTIR:
            m = re.search(desen, q)
            if m:
                k1, k2 = (_sozluk_bicimi(db, _turkce_geri(ham, m.group(i))) for i in (1, 2))
                return {"niyet": "karsilastir", "kavram": f"{k1} / {k2}", "suzgec": suzgec, "anlasilan": anlasilan, "konulu": False,
                        "ek": {"k1": k1, "k2": k2}}
        m = re.search(KOKEN_DESEN, q)
        if m and m.group(1) not in DOLGU:
            k = _sozluk_bicimi(db, _turkce_geri(ham, m.group(1)))
            return {"niyet": "koken", "kavram": k, "suzgec": suzgec, "anlasilan": anlasilan, "konulu": False, "ek": {}}
        m = re.search(ILGILI_DESEN, q)
        if m and m.group(1) not in DOLGU:
            k = _sozluk_bicimi(db, _turkce_geri(ham, m.group(1)))
            tip = "zıt anlamlı" if re.match(r"zit|karsit|ziddi", m.group(2)) else "eş anlamlı"
            return {"niyet": "ilgili", "kavram": k, "suzgec": suzgec, "anlasilan": anlasilan + [{"tip": "ilgili", "deger": tip, "etiket": "İlişki: " + tip}],
                    "konulu": False, "ek": {"tip": tip}}

    # Niyet
    if arap_mi(ham):
        niyet = "anlam"
    elif suzgec.get("yazar") and re.search(YAZAR_SORU, q):
        niyet = "yazar"
    elif re.search(YAZARLAR_SORU, q) and (suzgec.get("gelenek") or suzgec.get("donem")):
        niyet = "yazarlar"
    elif re.search(TANIK_SOZ, q) or (y and not suzgec.get("tur")):
        niyet = "tanik"
    elif re.search(ANLAM_SORU, q):
        niyet = "anlam"
    elif re.search(ANLAMINDA, q) or re.search(KONULU, q) or suzgec.get("tur") in ("atasözü", "deyim"):
        niyet = "kavram"
    elif re.search(OSM_KARSILIK, q) or suzgec.get("koken") in ("Fa", "Ar"):
        niyet = "karsilik"
    else:
        niyet = "ara"

    # Kavram
    m = re.search(ANLAMINDA, q) or re.search(KONULU, q)
    kavram = _kavram(m.group(1) if m else q, sil)
    if niyet == "tanik":
        kavram = re.sub(r"\b(temali|konulu)\b", "", kavram).strip()
    if arap_mi(ham):
        kavram_tr = re.sub(r"[^؀-ۿ\s]", "", ham).strip()
    else:
        # Kullanıcının asıl yazımını geri kazan (ascii'leştirmeden önceki Türkçe harfler), sonra sözlük biçimine indir
        kavram_tr = " ".join(_sozluk_bicimi(db, k) for k in _turkce_geri(ham, kavram).split())
    if niyet in ("yazar", "yazarlar"):
        kavram_tr = ""
    return {"niyet": niyet, "kavram": kavram_tr, "suzgec": suzgec, "anlasilan": anlasilan,
            "konulu": bool(re.search(KONULU, q)), "ek": {}}


def _turkce_geri(ham, kavram):
    """ascii'leştirilmiş kavramı, sorudaki Türkçe harfli asıl kelimelerle değiştirir."""
    if not kavram:
        return kavram
    # ascii'leştirme harf harf yapıldığından uzunluk korunur: baş kısmı aynen alınabilir
    asil = [(_asc(normal(k)), normal(k)) for k in re.findall(r"[\wâîûÂÎÛ]+", ham)]
    out = []
    for k in kavram.split():
        bas = next((v for a, v in asil if a == k), None) or next((v[:len(k)] for a, v in asil if a.startswith(k) and len(a) == len(v)), None)
        out.append(bas or k)
    return " ".join(out)


def _asc(s):
    return s.replace("ı", "i").replace("ş", "s").replace("ç", "c").replace("ğ", "g").replace("ö", "o").replace("ü", "u")


# ---------------- Anlamsal yardımcılar ----------------
def genislet(db, kavram):
    """Kavramı sözlükteki kendi tanımıyla genişletir (küçük model tek kelimede zayıf; tanım bağlam verir)."""
    if not kavram or len(kavram.split()) > 3:
        return kavram
    r = db.execute("""SELECT group_concat(metin, '; ') FROM (
                        SELECT a.metin FROM kayit k JOIN anlam a ON a.kayit_id=k.id
                        WHERE k.norm=? AND k.aciklama_dili='tr' AND k.tur!='özel ad' ORDER BY k.kaynak_id='bengu' DESC, a.sira LIMIT 3)""",
                   (normal(kavram),)).fetchone()[0]
    if not r:
        return kavram
    if len(r) < 18 and " " not in r.strip(" ."):  # "hasret: Özlem" → özlem'in tanımını da ekle
        r2 = db.execute("""SELECT group_concat(metin, '; ') FROM (SELECT a.metin FROM kayit k JOIN anlam a ON a.kayit_id=k.id
                           WHERE k.norm=? AND k.aciklama_dili='tr' AND k.tur!='özel ad' ORDER BY a.sira LIMIT 2)""",
                        (normal(r.strip(" .")),)).fetchone()[0]
        if r2:
            r += "; " + r2
    return f"{kavram}: {r[:300]}"


def _kayit_ozet(db, ids_puan, yol):
    out = []
    for kid, p in ids_puan:
        k = db.execute("""SELECT k.baslik, k.osmanli, k.koken, k.tur, k.dil,
                                 (SELECT metin FROM anlam WHERE kayit_id=k.id ORDER BY sira LIMIT 1) AS anlam
                          FROM kayit k WHERE k.id=?""", (kid,)).fetchone()
        if k:
            d = dict(k)
            d.update(puan=round(p, 3), yol=yol)
            out.append(d)
    return out


def _aday_kayitlar(db, suzgec):
    kosul, arg = ["k.tur NOT IN ('özel ad','kısaltma','ek')"], []
    if suzgec.get("osm") and not suzgec.get("koken"):
        kosul.append("(k.dil='ota' OR k.koken IN ('Ar','Fa'))")
    if suzgec.get("koken"):
        kosul.append("k.koken=?")
        arg.append(suzgec["koken"])
    if suzgec.get("tur"):
        kosul.append("k.tur=?")
        arg.append(suzgec["tur"])
    if suzgec.get("donem"):
        kosul.append("k.id IN (SELECT kayit_id FROM kayit_donem WHERE donem=?)")
        arg.append(suzgec["donem"])
    if len(kosul) == 1:
        return None
    return {r[0] for r in db.execute(f"SELECT k.id FROM kayit k WHERE {' AND '.join(kosul)}", arg)}


def _aday_satirlar(db, suzgec):
    kosul, arg = [], []
    if suzgec.get("yazar"):
        kosul.append("m.yazar_id=?")
        arg.append(suzgec["yazar"])
    if suzgec.get("donem"):
        kosul.append("m.donem=?")
        arg.append(suzgec["donem"])
    if suzgec.get("gelenek"):
        kosul.append("m.gelenek=?")
        arg.append(suzgec["gelenek"])
    if not kosul:
        return None
    return {r[0] for r in db.execute(f"SELECT s.id FROM satir s JOIN metin m ON m.id=s.metin_id WHERE {' AND '.join(kosul)}", arg)}


def _satir_ozet(db, ids_puan):
    out = []
    for sid, p in ids_puan:
        r = db.execute("""SELECT s.metin, s.ceviri, s.metin_id, s.sira, s.kita, m.eser, m.url, m.donem, m.yazar_id,
                                 COALESCE(y.gorunen, y.ad, m.yazar_id) AS yazar
                          FROM satir s JOIN metin m ON m.id=s.metin_id LEFT JOIN yazar y ON y.id=m.yazar_id WHERE s.id=?""", (sid,)).fetchone()
        if not r:
            continue
        d = dict(r)
        if not r["ceviri"]:
            k = db.execute("SELECT metin FROM satir WHERE metin_id=? AND kita=? AND sira=?",
                           (r["metin_id"], r["kita"], r["sira"] + 1 if r["sira"] % 2 == 0 else r["sira"] - 1)).fetchone()
            if k:
                d["sonra" if r["sira"] % 2 == 0 else "once"] = k[0]
        d["puan"] = round(p, 3)
        d["vurgu"] = []
        out.append(d)
    return out


_DURAK = set("bir ve ile ya da veya olan olarak icin gibi kimse sey seyi yapma etme olma durumu hali birine bir seyi "
             "turlu cok az daha en bu su o".split())


def _kokler(metin, uzunluk=5):
    """Metnin içerik kelimelerinin kaba kökleri (ilk 5 harf, ascii): sözcük örtüşmesi puanı için."""
    out = set()
    for k in re.findall(r"\w+", _asc(normal(metin))):
        if len(k) >= 3 and k not in _DURAK:
            out.add(k[:uzunluk])
    return out


def karma_kayit(db, kavram, sz, n=20):
    """Anlamsal benzerlik + sözcük örtüşmesi. Küçük modelin puanları dar aralıkta toplandığından, tanımında kavramın
    (ya da sözlükteki tanımının) kelimeleri geçen kayıtlar öne alınır; eşiğin altındakiler elenir."""
    gen = genislet(db, kavram)
    kavram_k = _kokler(kavram)
    gen_k = _kokler(gen) - kavram_k
    aday = _aday_kayitlar(db, sz)
    puan = {}
    if anlam.hazir():
        try:
            for kid, p in anlam.benzer(gen, "kayit", 80, aday):
                puan[kid] = p
        except Exception:  # model sorunu: sözcük temelli sonuçlarla devam et
            anlam.devre_disi()
    # Sözcük adayları: tanımında kavram geçen kayıtlar (tam metin dizini)
    jeton = _asc(normal(kavram)).split()
    if jeton:
        ifade = " ".join(f'"{j[:max(4, len(j) - 2)]}"*' for j in jeton)
        try:
            for (kid,) in db.execute("SELECT rowid FROM kayit_fts WHERE kayit_fts MATCH ? LIMIT 400", (ifade,)):
                if aday is None or kid in aday:
                    puan.setdefault(kid, min(puan.values(), default=0.85) - 0.01)
        except Exception:
            pass
    sonuc = []
    for kid, p in puan.items():
        k = db.execute("""SELECT k.baslik, k.norm, k.osmanli, k.koken, k.tur, k.dil, k.aciklama_dili,
                                 (SELECT group_concat(metin, '; ') FROM (SELECT metin FROM anlam WHERE kayit_id=k.id ORDER BY sira LIMIT 3)) AS anlamlar
                          FROM kayit k WHERE k.id=?""", (kid,)).fetchone()
        if not k or k["tur"] in ("özel ad", "kısaltma", "ek") or k["norm"] == normal(kavram):
            continue
        metin_k = _kokler((k["anlamlar"] or ""))
        baslik_k = _kokler(k["baslik"])
        ortusme = 2 * len(kavram_k & metin_k) + len(gen_k & (metin_k | baslik_k))
        if aday is None and not sz.get("tur") and k["tur"] not in ("kelime", "tamlama"):
            ortusme -= 1  # kelime sorulduysa deyimleri biraz geri al
        sonuc.append({"baslik": k["baslik"], "osmanli": k["osmanli"], "koken": k["koken"], "tur": k["tur"], "dil": k["dil"],
                      "anlam": (k["anlamlar"] or "").split("; ")[0], "ingilizce": k["aciklama_dili"] == "en",
                      "puan": round(p + 0.025 * max(min(ortusme, 4), -1), 3), "ortusme": ortusme,
                      "yol": "tanımda geçiyor" if kavram_k & metin_k else ("anlam benzerliği" if kid in puan else "")})
    sonuc.sort(key=lambda s: -s["puan"])
    if sonuc:
        # Tanımı kavramla örtüşmeyenler yalnız en iyiye çok yakınsa kalır (küçük modelin gürültüsünü keser)
        en_iyi = sonuc[0]["puan"]
        sonuc = [s for i, s in enumerate(sonuc) if s["ortusme"] >= 2 or (s["ortusme"] >= 1 and s["puan"] >= en_iyi - 0.045)
                 or (i < 3 and s["puan"] >= en_iyi - 0.02)]
    # Aynı başlığı tekrarlama
    gorulen, tekil = set(), []
    for s in sonuc:
        if normal(s["baslik"]) not in gorulen:
            gorulen.add(normal(s["baslik"]))
            tekil.append(s)
    return tekil[:n]


def tanimi_esit(db, kavram, sinir=30):
    """Tanım parçalarından biri tam olarak kavram olan (özel ad olmayan) kayıtların başlıkları."""
    from .normal import tanim_parcalari
    n = normal(kavram)
    out = []
    from .normal import ascii_
    jeton = " ".join(f'"{j}"' for j in ascii_(kavram).split() if j)
    if not jeton:
        return []
    try:  # tam metin dizininden adaylar (tanım tablosunu baştan sona taramaktan ~20 kat hızlı)
        ids = [r[0] for r in db.execute("SELECT rowid FROM kayit_fts WHERE kayit_fts MATCH ? LIMIT 3000", (jeton,))]
    except sqlite3.OperationalError:
        ids = []
    if not ids:
        return []
    yer = ",".join("?" * len(ids))
    for baslik, metin in db.execute(f"""SELECT k.baslik, a.metin FROM anlam a JOIN kayit k ON k.id=a.kayit_id
                                        WHERE k.id IN ({yer}) AND k.tur IN ('kelime','tamlama') AND k.aciklama_dili='tr'""", ids):
        if n in tanim_parcalari(metin) and normal(baslik) != n:
            out.append(baslik)
    return list(dict.fromkeys(out))[:sinir]


def karma_tanik(db, kavram, sz):
    """Tema araması: kavram + Osmanlıca eş anlamlıları (ayrılık → hicr, cüdâyî …) geçen satırlar, sözcük düzeyinde."""
    kelimeler = [kavram]
    if len(kavram.split()) == 1:
        adaylar = []
        r = ceviri.turkceden_osmanlicaya(db, kavram, sinir=12)
        adaylar += [b for o in r["oneriler"] if o["guven"] != "yakın anlam" for b in o["basliklar"]]
        # Tanımının bir parçası tam olarak kavram olan kelimeler (firâk: "Ayrılış, ayrılık"; hicrân: "ayrılık");
        # kökeni boş ya da yanlış etiketli olsalar bile. "gitmek: bir yerden ayrılmak" gibiler girmez.
        adaylar += tanimi_esit(db, kavram)
        siklik = {}
        for a in dict.fromkeys(adaylar):
            n_ = db.execute("SELECT count(*) FROM satir_dizin WHERE norm=?", (normal(a),)).fetchone()[0]
            if n_ and normal(a) != normal(kavram):
                siklik[a] = n_
        kelimeler += sorted(siklik, key=lambda a: -siklik[a])[:6]
    birlesik, say = [], {}
    for k in kelimeler:
        r = arama.tanik(db, k, yazar=sz.get("yazar", ""), donem=sz.get("donem", ""), boyut=40)
        satirlar = [s for s in r["satirlar"] if not sz.get("gelenek") or s["gelenek"] == sz["gelenek"]]
        if satirlar:
            say[k] = len(satirlar)
            for s in satirlar:
                s["kelime"] = k
            birlesik += satirlar
    # Kelime çeşitliliği: her kelimeden sırayla al
    kuyruk = {k: [s for s in birlesik if s["kelime"] == k] for k in say}
    sirali = []
    while any(kuyruk.values()) and len(sirali) < 30:
        for k in list(kuyruk):
            if kuyruk[k]:
                sirali.append(kuyruk[k].pop(0))
    return sirali, say


# ---------------- Ana giriş ----------------
def sor(db, soru):
    c = cozumle(db, soru)
    niyet, kavram, sz = c["niyet"], c["kavram"], c["suzgec"]
    yanit = {"soru": soru, **c, "anlamsal": anlam.hazir(), "bolumler": []}
    if not kavram and niyet not in ("tanik", "yazar", "yazarlar"):
        yanit["niyet"] = "ara"
        return yanit
    _yeni_niyetler(db, yanit)
    if not yanit["bolumler"]:
        _eski_niyetler(db, yanit)
    yanit["ozet"] = _ozet(yanit)
    yanit["oneriler"] = _soru_onerileri(db, yanit)
    return yanit


def _yeni_niyetler(db, yanit):
    niyet, kavram, sz, ek = yanit["niyet"], yanit["kavram"], yanit["suzgec"], yanit.get("ek") or {}
    if niyet == "cozumle":
        yanit["bolumler"].append({"tip": "cozumleme", "baslik": "Kelime kelime çözümleme", "veri": cozumleme.cozumle(db, ek["metin"])})
    elif niyet == "kafiye":
        yanit["bolumler"].append({"tip": "kafiye", "baslik": _kafiye_baslik(ek), "veri": kafiye(db, ek["parca"], ek["kip"], sz)})
    elif niyet == "koken":
        m = arama.madde(db, kavram)
        if m:
            yanit["bolumler"].append({"tip": "koken", "baslik": f"“{m['baslik']}” kelimesinin kökeni", "veri": _koken_ozet(m)})
    elif niyet == "ilgili":
        yanit["bolumler"].append({"tip": "kelimeler", "baslik": f"“{kavram}” için {ek['tip']} kelimeler",
                                  "veri": ilgili_kelimeler(db, kavram, ek["tip"], sz)})
    elif niyet == "karsilastir":
        yanit["bolumler"].append({"tip": "karsilastir", "baslik": f"“{ek['k1']}” ile “{ek['k2']}”", "veri": karsilastir(db, ek["k1"], ek["k2"])})
    elif niyet == "yazar":
        y = arama.yazar(db, sz["yazar"])
        if y:
            y["metinler"] = y["metinler"][:12]
            yanit["bolumler"].append({"tip": "yazar", "baslik": y.get("gorunen") or y["ad"], "veri": y})
    elif niyet == "yazarlar":
        ys = [y for y in arama.yazarlar(db) if (not sz.get("gelenek") or y["gelenek"] == sz["gelenek"])
              and (not sz.get("donem") or y["donem"] == sz["donem"])]
        yanit["bolumler"].append({"tip": "yazarlar", "baslik": "Yazarlar", "veri": ys})


def _kafiye_baslik(ek):
    return {"son": f"“-{ek['parca']}” ile biten kelimeler", "bas": f"“{ek['parca']}” ile başlayan kelimeler",
            "kafiye": f"“{ek['parca']}” ile kafiyeli olabilecek kelimeler"}[ek["kip"]]


def kafiye(db, parca, kip, sz, sinir=60):
    """Kafiye / uyak bulucu. Derlemde (şiirde) sık geçenler önde; köken / Osmanlıca süzgeci uygulanır."""
    n = normal(parca)
    if kip == "kafiye":  # son hece(ler): gül → -ül, dildâr → -dâr
        son = n[-3:] if len(n) >= 4 else n[-2:]
        desen, haric = "%" + son, n
    elif kip == "son":
        desen, haric = "%" + n, None
    else:
        desen, haric = n + "%", None
    kosul, arg = ["k.norm LIKE ?", "k.tur IN ('kelime','tamlama')", "k.norm NOT LIKE '% %'", "k.aciklama_dili='tr'"], [desen]
    if sz.get("koken"):
        kosul.append("k.koken=?")
        arg.append(sz["koken"])
    elif sz.get("osm"):
        kosul.append("(k.dil='ota' OR k.koken IN ('Ar','Fa'))")
    rows = db.execute(f"""SELECT k.baslik, k.norm, k.osmanli, k.koken, k.dil,
                                 (SELECT metin FROM anlam WHERE kayit_id=k.id ORDER BY sira LIMIT 1) AS anlam,
                                 (SELECT count(*) FROM satir_dizin d WHERE d.norm=k.norm) AS siklik
                          FROM kayit k WHERE {' AND '.join(kosul)} AND EXISTS(SELECT 1 FROM anlam WHERE kayit_id=k.id)
                          ORDER BY siklik DESC, k.osmanli IS NOT NULL DESC, length(k.norm) LIMIT 400""", arg).fetchall()
    out, gorulen = [], {haric}
    for r in rows:
        if r["norm"] in gorulen:
            continue
        gorulen.add(r["norm"])
        d = dict(r)
        d["yol"] = f"şiirde {r['siklik']} kez" if r["siklik"] else ""
        d["tur"] = "kelime"
        out.append(d)
    return out[:sinir]


def _koken_ozet(m):
    kayitlar = [k for k in m["kayitlar"] if k["tur"] != "özel ad"] or m["kayitlar"]
    out = {"baslik": m["baslik"], "osmanli": next((k["osmanli"] for k in kayitlar if k["osmanli"]), None), "kaynaklar": []}
    for k in kayitlar:
        if k["koken"] or k["koken_ayrinti"]:
            out["kaynaklar"].append({"kaynak": k["kaynak_ad"], "koken": k["koken"], "ayrinti": k["koken_ayrinti"], "dil": k["dil"],
                                     "donem": k["donem"]})
    out["koken"] = next((k["koken"] for k in kayitlar if k["koken"]), None)
    return out


def ilgili_kelimeler(db, kavram, tip, sz):
    n = normal(kavram)
    out, gorulen = [], {n}

    def ekle(baslik, yol):
        nb = normal(baslik)
        if nb in gorulen:
            return
        k = db.execute("""SELECT k.baslik, k.osmanli, k.koken, k.dil, k.tur,
                                 (SELECT metin FROM anlam WHERE kayit_id=k.id ORDER BY sira LIMIT 1) AS anlam
                          FROM kayit k WHERE k.norm=? AND k.tur!='özel ad' ORDER BY k.aciklama_dili='tr' DESC LIMIT 1""", (nb,)).fetchone()
        if sz.get("koken") and (not k or k["koken"] != sz["koken"]):
            return
        gorulen.add(nb)
        d = dict(k) if k else {"baslik": baslik, "osmanli": None, "koken": None, "dil": None, "tur": "kelime", "anlam": None}
        d["yol"] = yol
        out.append(d)

    # Vikisözlük bağlantıları (iki yönlü)
    for (b,) in db.execute("SELECT i.baslik FROM ilgili i JOIN kayit k ON k.id=i.kayit_id WHERE k.norm=? AND i.tip=?", (n, tip)):
        ekle(b, "Vikisözlük bağlantısı")
    for (b,) in db.execute("SELECT k.baslik FROM ilgili i JOIN kayit k ON k.id=i.kayit_id WHERE i.tip=? AND i.baslik=?", (tip, kavram)):
        ekle(b, "Vikisözlük bağlantısı (karşı yön)")
    if tip == "eş anlamlı":
        for b in tanimi_esit(db, kavram):  # tanımı doğrudan bu kelime olanlar
            ekle(b, "tanımı bu kelime")
        tanimlar = db.execute("""SELECT a.metin FROM anlam a JOIN kayit k ON k.id=a.kayit_id
                                 WHERE k.norm=? AND k.tur!='özel ad' AND k.aciklama_dili='tr' AND a.sira<2""", (n,)).fetchall()
        for (metin,) in tanimlar:
            for parca in tanim_parcalari(metin):
                if len(parca.split()) == 1 and db.execute("SELECT 1 FROM kayit WHERE norm=? AND tur='kelime' LIMIT 1", (parca,)).fetchone():
                    ekle(parca, "kendi tanımında geçiyor")
                    # Aynı tanımı paylaşanlar: hasret → "özlem" → tanımı "özlem" olan diğer kelimeler (tahassür …)
                    for b in tanimi_esit(db, parca, sinir=12):
                        # ikinci düzeyde yalnız Osmanlıca olduğu belgelenmiş kelimeler (veri gürültüsünü keser)
                        if db.execute("""SELECT 1 FROM kayit WHERE norm=? AND (osmanli IS NOT NULL OR koken IN ('Ar','Fa') OR dil='ota')
                                         LIMIT 1""", (normal(b),)).fetchone():
                            ekle(b, f"tanımı “{parca}”")
    elif len(out) < 3:
        # Doğrudan zıt anlam bağlantısı azsa: eş anlamlılarının zıt anlamlıları (cesur → yiğit → korkak)
        for es in ilgili_kelimeler(db, kavram, "eş anlamlı", {})[:8]:
            for (b,) in db.execute("SELECT i.baslik FROM ilgili i JOIN kayit k ON k.id=i.kayit_id WHERE k.norm=? AND i.tip=?",
                                   (normal(es["baslik"]), tip)):
                ekle(b, f"eş anlamlısı “{es['baslik']}” üzerinden")
    return out[:40]


def karsilastir(db, k1, k2):
    def ozet(k):
        m = arama.madde(db, k)
        if not m:
            return {"baslik": k, "bulundu": False}
        ks = [x for x in m["kayitlar"] if x["tur"] != "özel ad"] or m["kayitlar"]
        anlamlar = []
        for x in ks:
            for a in x["anlamlar"][:3]:
                if a["metin"] not in anlamlar and x["aciklama_dili"] == "tr":
                    anlamlar.append(a["metin"])
        tanik = arama.tanik(db, m["baslik"], boyut=1)
        return {"baslik": m["baslik"], "bulundu": True, "osmanli": next((x["osmanli"] for x in ks if x["osmanli"]), None),
                "koken": next((x["koken"] for x in ks if x["koken"]), None),
                "koken_ayrinti": next((x["koken_ayrinti"] for x in ks if x["koken_ayrinti"]), None),
                "donem": sorted({d for x in ks for d in x["donem"]}), "anlamlar": anlamlar[:5],
                "tanik_sayisi": tanik.get("genel_toplam", 0), "tanik_ornek": (tanik["satirlar"][:1] or [None])[0]}
    a, b = ozet(k1), ozet(k2)
    ortak = []
    if a["bulundu"] and b["bulundu"]:
        e1 = {normal(x["baslik"]) for x in ilgili_kelimeler(db, a["baslik"], "eş anlamlı", {})}
        e2 = {normal(x["baslik"]) for x in ilgili_kelimeler(db, b["baslik"], "eş anlamlı", {})}
        ortak = sorted(e1 & e2)[:12]
        a["digerinde"] = any(normal(b["baslik"]) in normal(t) for t in a["anlamlar"])
        b["digerinde"] = any(normal(a["baslik"]) in normal(t) for t in b["anlamlar"])
    return {"a": a, "b": b, "ortak": ortak}


def _ozet(y):
    """Şablonla kurulan, sayılara dayalı kısa özet (metin üretimi değil)."""
    kok_adi = {"Ar": "Arapça", "Fa": "Farsça", "T": "Türkçe", "Bt": "Batı dillerinden"}
    for b in y["bolumler"]:
        v, t = b["veri"], b["tip"]
        if t in ("kelimeler", "kafiye") and isinstance(v, list) and v:
            say = {}
            for x in v:
                if x.get("koken"):
                    say[x["koken"]] = say.get(x["koken"], 0) + 1
            kisa = {"Ar": "Arapça", "Fa": "Farsça", "T": "Türkçe", "Bt": "Batı dilleri"}
            dag = ", ".join(f"{kisa[k]} {n}" for k, n in sorted(say.items(), key=lambda s: -s[1]) if k in kisa)
            return f"{len(v)} kayıt bulundu." + (f" Köken dağılımı: {dag}." if dag else "")
        if t == "karsilik":
            n = len(v["oneriler"])
            tam = sum(1 for o in v["oneriler"] if o["guven"] == "tam karşılık")
            return f"{n} Osmanlıca karşılık önerisi; {tam} tanesi tam karşılık." if n else "Osmanlıca karşılık bulunamadı."
        if t == "cozumleme":
            return (f"{v['toplam']} kelimeden {v['bulunan']} tanesi sözlükte bulundu"
                    + (f", {v['kalip']} kalıp/tamlama bütün olarak tanındı" if v["kalip"] else "") + ".")
        if t in ("tanik_tema", "tanik_anlam") and v:
            yazar = len({s["yazar"] for s in v})
            return f"{len(v)} satır, {yazar} farklı yazardan."
        if t == "tanik":
            return f"{v['genel_toplam']} satırda geçiyor, {len(v['yazarlar'])} yazar."
        if t == "koken":
            k = v.get("koken")
            return f"“{v['baslik']}” {kok_adi.get(k, 'kökeni belirsiz')}{' kökenli' if k in kok_adi else ''}" + (f"; Osmanlıca yazılışı {v['osmanli']}." if v.get("osmanli") else ".")
        if t == "karsilastir":
            return f"İki kelimenin {len(v['ortak'])} ortak eş anlamlısı var." if v["ortak"] else "İki kelimenin tanımları ve kaynakları yan yana."
        if t == "yazarlar":
            return f"{len(v)} yazar."
        if t == "yazar":
            return f"{v.get('gorunen') or v['ad']} ({v['yasam']}): {len(v['eserler'])} önemli eser, derlemde {v.get('satir_sayisi', 0)} satır."
        if t == "kelimeler" and not v:
            return "Kayıtlı ilişki bulunamadı."
    return ""


def _soru_onerileri(db, y):
    """Sonraki adım için Rehber'in anlayacağı hazır sorular."""
    k, n = y.get("kavram") or "", y["niyet"]
    if n == "yazar" and y["bolumler"]:
        ad = y["bolumler"][0]["baslik"]
        return [f"{ad} aşk geçen beyitleri", f"{ad} ölüm ile ilgili şiirleri"]
    if not k or " " in k or n in ("cozumle", "karsilastir", "yazarlar") or arap_mi(k):
        return []
    sablon = {"karsilik": f"{k} kelimesinin Osmanlıcası", "tanik": f"{k} geçen beyitler", "kavram": f"{k} anlamına gelen kelimeler",
              "koken": f"{k} kelimesinin kökeni", "es": f"{k} kelimesinin eş anlamlısı", "zit": f"{k} kelimesinin zıt anlamlısı",
              "atasozu": f"{k} ile ilgili atasözleri", "kafiye": f"{k} ile kafiyeli kelimeler"}
    sira = {"karsilik": ["kavram", "tanik", "koken", "atasozu"], "anlam": ["tanik", "koken", "es", "kafiye"],
            "kavram": ["karsilik", "tanik", "atasozu", "zit"], "tanik": ["karsilik", "kavram", "koken", "atasozu"],
            "koken": ["karsilik", "tanik", "es"], "ilgili": ["karsilik", "tanik", "koken"], "kafiye": ["tanik", "karsilik"]}.get(n, [])
    return [sablon[s] for s in sira][:4]


def _eski_niyetler(db, yanit):
    niyet, kavram, sz, c = yanit["niyet"], yanit["kavram"], yanit["suzgec"], yanit
    if niyet == "karsilik":
        r = ceviri.turkceden_osmanlicaya(db, kavram)
        oneriler = [o for o in r["oneriler"] if not sz.get("koken") or o["koken"] == sz["koken"]]
        yanit["bolumler"].append({"tip": "karsilik", "baslik": f"“{kavram}” için Osmanlıca karşılıklar", "veri": {**r, "oneriler": oneriler}})
        if len(oneriler) < 6:  # azsa anlamca yakın Osmanlıca kelimelerle tamamla
            ek = karma_kayit(db, kavram, {**sz, "koken": sz.get("koken") or None, "osm": True}, n=10)
            gorulen = {normal(b) for o in oneriler for b in o["basliklar"]}
            ek = [e for e in ek if normal(e["baslik"]) not in gorulen and (e["koken"] in ("Ar", "Fa") or e["dil"] == "ota")
                  and e["ortusme"] >= 2]  # yalnız tanımı kavramla belirgin örtüşenler: gürültüyü keser
            if ek:
                yanit["bolumler"].append({"tip": "kelimeler", "baslik": "Anlamca yakın başka kelimeler", "veri": ek[:8]})

    elif niyet == "anlam":
        r = ceviri.osmanlicadan_turkceye(db, kavram)
        yanit["bolumler"].append({"tip": "anlam", "baslik": f"“{kavram}” ne demek?", "veri": r})

    elif niyet == "kavram":
        sonuc = []
        if sz.get("koken") in ("Ar", "Fa") and not sz.get("tur"):
            r = ceviri.turkceden_osmanlicaya(db, kavram, sinir=10)
            for o in r["oneriler"]:
                if o["koken"] == sz["koken"]:
                    sonuc.append({"baslik": o["basliklar"][0], "osmanli": o["osmanli"], "koken": o["koken"], "tur": "kelime",
                                  "anlam": o["anlam"], "puan": o["puan"], "yol": o["guven"]})
        ek = karma_kayit(db, kavram, sz, n=25)
        gorulen = {normal(s["baslik"]) for s in sonuc} | {normal(kavram)}
        sonuc += [e for e in ek if normal(e["baslik"]) not in gorulen]
        tur_adi = {"atasözü": "Atasözleri", "deyim": "Deyimler", "tamlama": "Tamlamalar"}.get(sz.get("tur"), "Kelimeler")
        yanit["bolumler"].append({"tip": "kelimeler", "baslik": f"{tur_adi}: “{kavram}”", "veri": sonuc[:25]})

    elif niyet == "tanik":
        # 1) Kelimenin kendisinin geçtiği satırlar (sözlük dizini)
        tek_kelime = kavram and len(kavram.split()) == 1 and not c["konulu"]
        if tek_kelime:
            r = arama.tanik(db, kavram, yazar=sz.get("yazar", ""), donem=sz.get("donem", ""))
            if sz.get("gelenek"):
                r["satirlar"] = [s for s in r["satirlar"] if s["gelenek"] == sz["gelenek"]]
            if r["satirlar"]:
                yanit["bolumler"].append({"tip": "tanik", "baslik": f"“{kavram}” geçen satırlar", "veri": r})
        # 2) Tema: kavram + Osmanlıca eş anlamlıları geçen satırlar (ayrılık → hicr, cüdâyî …)
        if kavram and (c["konulu"] or not yanit["bolumler"]):
            satirlar, say = karma_tanik(db, kavram, sz)
            if satirlar:
                yanit["bolumler"].append({"tip": "tanik_tema", "baslik": "Tema kelimeleri: " + ", ".join(f"{k} ({n})" for k, n in say.items()),
                                          "veri": satirlar})
        # 3) Konusu / anlamı yakın satırlar (anlamsal; eski metinlerde daha zayıf, en sonda)
        bulunan = sum(len(b["veri"]["satirlar"]) if b["tip"] == "tanik" else len(b["veri"]) for b in yanit["bolumler"])
        if anlam.hazir() and kavram and bulunan < 10:
            aday = _aday_satirlar(db, sz)
            try:
                satirlar = _satir_ozet(db, anlam.benzer(genislet(db, kavram) if tek_kelime else kavram, "satir", 15, aday))
            except Exception:
                anlam.devre_disi()
                satirlar = []
            if satirlar:
                yanit["bolumler"].append({"tip": "tanik_anlam", "baslik": f"“{kavram}” temasına yakın satırlar", "veri": satirlar})
        elif not kavram and sz.get("yazar"):
            yanit["bolumler"].append({"tip": "yazar", "baslik": "Yazar", "veri": {"id": sz["yazar"]}})
    return yanit
