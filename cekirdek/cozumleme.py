"""Bengü — beyit / tamlama çözümleyici.

Bir mısra, beyit ya da Osmanlıca ifadeyi kelime kelime sözlükte arar:
  - Önce 3 ve 2 kelimelik dizileri bütün olarak dener (serv-i revân, dil-i nâşâd, kîl ü kāl …)
  - Tek kelimede: tam eşleşme → çekim sözlüğü → bilinen ekleri atma (Türkçe ve eski Anadolu Türkçesi ekleri,
    Farsça/Arapça çoğul ekleri)
  - Farsça tamlama (izafet) ekini "-i / -ı / -yi" ve bağlama "ü / u" ayrıca işaretler
Metin üretmez: her satırdaki anlam, sözlükteki bir kaydın ilk tanımıdır.
"""
import re

from .normal import normal

KELIME = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîûÊêĀāĪīŪūḤḥḲḳṬṭṢṣẒẓʿʾ’'‘ñŋ]+(?:-[A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîûĀāĪīŪūʿʾ’'‘]+)*")
IZAFET = {"i", "ı", "u", "ü", "yi", "yı", "yu", "yü"}
BAGLAMA = {"ü", "u", "vü", "vu"}  # Farsça "ve" bağlacı: kîl ü kāl
# En uzundan kısaya: Türkiye Türkçesi ekleri + eski Anadolu Türkçesi + Farsça/Arapça çoğul
EKLER = sorted(set("""
    lar ler ları leri ların lerin larda lerde lardan lerden larına lerine larını lerini
    ım im um üm ın in un ün ı i u ü sı si su sü yı yi yu yü a e ya ye na ne da de ta te dan den tan ten nda nde ndan nden
    ımız imiz umuz ümüz ınız iniz unuz ünüz mız miz muz müz nız niz nuz nüz
    la le yla yle ca ce ça çe ki dır dir dur dür tır tir tur tür
    mak mek mış miş muş müş dı di du dü tı ti tu tü sın sin sun sün
    ub üb ıb ib up üp ıp ip ıcak icek ucak ücek dukça dükçe dıkça dikçe
    uñ üñ ıñ iñ nuñ nüñ nıñ niñ uñuz üñüz ıñız iñiz idi ıdı udu üdü imiş ımış umuş
    an ân hâ ha ât at ın ine ına ünü unu ını ini ısı isi usu üsü sına sine
    uz üz ız iz yuz yüz yız yiz elim alım elüm alum eyim ayım dım dim dum düm sun sün
    """.split()), key=len, reverse=True)
YUMUSAMA = {"b": "p", "c": "ç", "d": "t", "ğ": "k", "g": "k"}
KISA_EKLER = ["ye", "ya", "e", "a", "yi", "yı", "i", "ı", "de", "da", "den", "dan", "in", "ın", "ım", "im", "um", "üm", "un", "ün"]

# Eski Anadolu / Azerbaycan sahası Türkçesinde sık geçen biçimler (Bengü derlemesi; yaygın bilinen karşılıklar)
ESKI_BICIM = {
    "men": ("ben", "birinci tekil şahıs zamiri"), "menüm": ("benim", "ben zamirinin ilgi hâli"),
    "menim": ("benim", "ben zamirinin ilgi hâli"), "mana": ("bana", "ben zamirinin yönelme hâli"),
    "meni": ("beni", "ben zamirinin belirtme hâli"), "senüñ": ("senin", "sen zamirinin ilgi hâli"),
    "ol": ("o", "üçüncü tekil şahıs zamiri / işaret sıfatı"), "anı": ("onu", "o zamirinin belirtme hâli"),
    "aña": ("ona", "o zamirinin yönelme hâli"), "anuñ": ("onun", "o zamirinin ilgi hâli"), "anlar": ("onlar", "çokluk üçüncü şahıs"),
    "yoh": ("yok", "var olmayan"), "degül": ("değil", "olumsuzluk"), "değül": ("değil", "olumsuzluk"),
    "kamu": ("hep, bütün", "topluluk bildiren söz"), "bile": ("ile, birlikte", "birliktelik edatı"),
    "dahı": ("dahi, da", "pekiştirme / ekleme bağlacı"), "kim": ("ki", "bağlaç (eski metinlerde sıklıkla)"),
    "imdi": ("şimdi, öyleyse", "zaman / sonuç bildiren söz"), "nice": ("nasıl; ne kadar çok", "soru / miktar sözü"),
}


def _kayit(db, n, yazilan=None, ozel=False):
    """Bir biçim için en uygun kayıt: Türkçe açıklamalı; birebir yazılışı tutan, sonra Osmanlıca/Ar/Fa öncelikli."""
    return db.execute(f"""
        SELECT k.baslik, k.osmanli, k.koken, k.dil, k.tur,
               (SELECT metin FROM anlam WHERE kayit_id=k.id ORDER BY sira LIMIT 1) AS anlam
        FROM kayit k WHERE k.norm=? AND k.tur NOT IN ({"'kısaltma'" if ozel else "'özel ad','kısaltma'"}) AND k.aciklama_dili='tr'
          AND EXISTS(SELECT 1 FROM anlam WHERE kayit_id=k.id)
        ORDER BY k.kaynak_id='bengu' DESC, (lower(k.baslik)=lower(?)) DESC, (k.baslik NOT LIKE '%’%' AND k.baslik NOT LIKE '%''%') DESC,
                 (k.dil='ota' OR k.koken IN ('Ar','Fa')) DESC, k.tur='kelime' DESC, k.osmanli IS NOT NULL DESC, k.id LIMIT 1""",
                      (n, yazilan or n)).fetchone()


def _bul(db, kelime):
    """Tek kelime → (kayıt, sözlük biçimi, yol)"""
    n = normal(kelime)
    if len(n) < 2:
        return None, n, None
    k = _kayit(db, n, kelime)
    if k:
        return k, n, "tam"
    k, b, y = _bul_ekli(db, n)
    if k:
        return k, b, y
    k = _kayit(db, n, kelime, ozel=True)  # son çare: özel ad (Sa'dâbâd …)
    return (k, n, "özel ad") if k else (None, n, None)


def _fiil(db, aday):
    """Fiil kökü → mastar kaydı (gid → gitmek, bahşed → bahşetmek)."""
    for kok in (aday, aday[:-1] + YUMUSAMA.get(aday[-1], aday[-1])):
        for mastar in (kok + "mek", kok + "mak"):
            k = _kayit(db, mastar)
            if k:
                return k, mastar
    return None, None


def _bul_ekli(db, n):
    for (lem,) in db.execute("SELECT DISTINCT lemma FROM cekim WHERE norm=? LIMIT 3", (n,)):
        k = _kayit(db, normal(lem))
        if k:
            return k, normal(lem), "çekim"
    # Ekleri sırayla at (iki kata kadar: gönüllerimizde → gönüller+imiz+de)
    adaylar = [n]
    for _ in range(3):
        yeni = []
        for a in adaylar:
            for ek in EKLER:
                if a.endswith(ek) and len(a) - len(ek) >= 2:
                    kok = a[:-len(ek)]
                    for aday in (kok, kok[:-1] + YUMUSAMA.get(kok[-1], kok[-1])):
                        k = _kayit(db, aday) if len(aday) >= 2 else None
                        if k and len(aday) >= 3 or (k and len(n) <= 4):
                            return k, aday, "ek"
                        # ünlü düşmesi: gönlüm → gönül, ağzı → ağız
                        if len(aday) >= 3:
                            for u in "ıiuü":
                                dusme = aday[:-1] + u + aday[-1]
                                k = _kayit(db, dusme)
                                if k:
                                    return k, dusme, "ek"
                            fk, fm = _fiil(db, aday)
                            if fk:
                                return fk, fm, "ek"
                    yeni.append(kok)
        adaylar = [a for a in dict.fromkeys(yeni) if len(a) >= 3][:12]
        if not adaylar:
            break
    return None, n, None


def _baska_okuma(db, n, secilen):
    """Ekli okunuşu da olası kelimeler: aşkın = 'aşkın' (aşan) ya da aşk + -ın. Derlemde kökü daha sık geçiyorsa gösterilir."""
    for ek in KISA_EKLER:
        if n.endswith(ek) and len(n) - len(ek) >= 3:
            kok = n[:-len(ek)]
            k = _kayit(db, kok)
            if k and normal(k["baslik"]) != normal(secilen):
                f_kok = db.execute("SELECT count(*) FROM satir_dizin WHERE norm=?", (kok,)).fetchone()[0]
                f_tam = db.execute("SELECT count(*) FROM satir_dizin WHERE norm=?", (n,)).fetchone()[0]
                if f_kok >= 3 * max(f_tam, 1) and f_kok >= 10:
                    return {"bicim": k["baslik"], "ek": "-" + ek, "anlam": k["anlam"]}
    # Fiil okuması: yürü (emir) → yürümek
    fk, fm = _fiil(db, n)
    if fk and normal(fm) != normal(secilen):
        return {"bicim": fk["baslik"], "ek": "(fiil)", "anlam": fk["anlam"]}
    return None


def cozumle(db, metin, sinir=60):
    jetonlar = KELIME.findall(metin or "")[:sinir]
    out, i = [], 0
    while i < len(jetonlar):
        # 1) Çok kelimeli kalıp: 3 ve 2 kelimelik diziler (son kelime ekli olabilir)
        bulundu = False
        for uzunluk in (3, 2):
            if i + uzunluk > len(jetonlar):
                continue
            dizi = jetonlar[i:i + uzunluk]
            aday_metinler = [" ".join(dizi)]
            son = normal(dizi[-1])
            # son kelimenin kısa durum/iyelik ekini atarak dene: dil-i nâşâde → dil-i nâşâd
            aday_metinler += [" ".join(dizi[:-1] + [son[:-len(e)]]) for e in KISA_EKLER if son.endswith(e) and len(son) - len(e) >= 3]
            son_k, son_b, _ = _bul(db, dizi[-1])
            if son_k:
                aday_metinler.append(" ".join(dizi[:-1] + [son_k["baslik"]]))
            for a in aday_metinler:
                k = _kayit(db, normal(a))
                if k and k["tur"] != "kelime" or (k and len(normal(a).split()) > 1):
                    out.append({"yazilan": " ".join(dizi), "bicim": k["baslik"], "anlam": k["anlam"], "osmanli": k["osmanli"],
                                "koken": k["koken"], "dil": k["dil"], "tur": k["tur"], "bulundu": True, "kalip": True})
                    i += uzunluk
                    bulundu = True
                    break
            if bulundu:
                break
        if bulundu:
            continue
        # 2) Tek kelime (izafetli yazım: dil-i, serv-i)
        j = jetonlar[i]
        parcalar = j.split("-")
        govde, izafet = parcalar[0], None
        if len(parcalar) > 1 and normal(parcalar[-1]) in IZAFET:
            izafet = parcalar[-1]
            govde = "-".join(parcalar[:-1])
        elif len(parcalar) > 1:  # bileşik: pây-bend, dil-âşûb → önce bütün, sonra parçalar
            k = _kayit(db, normal(j))
            if k:
                out.append(_satir(j, k["baslik"], k, "tam"))
                i += 1
                continue
        if normal(j) in BAGLAMA and 0 < i < len(jetonlar) - 1:
            out.append({"yazilan": j, "bicim": "ü / u", "anlam": "Farsça bağlaç: ve (kîl ü kāl: dedikodu ve söz)", "bulundu": True, "ek": True})
            i += 1
            continue
        eski = ESKI_BICIM.get(normal(govde).replace("ı", "ı"))
        if eski:
            out.append({"yazilan": govde, "bicim": eski[0], "anlam": f"Eski Anadolu Türkçesi biçimi: {eski[0]} ({eski[1]})",
                        "bulundu": True, "yol": "eski biçim", "koken": "T"})
            i += 1
            continue
        k, bicim, yol = _bul(db, govde)
        satir = _satir(govde, k["baslik"] if k else bicim, k, yol)
        if k and yol == "tam" and not izafet:
            satir["baska"] = _baska_okuma(db, normal(govde), k["baslik"])
        out.append(satir)
        if izafet:
            out.append({"yazilan": "-" + izafet, "bicim": "izafet", "bulundu": True, "ek": True,
                        "anlam": "Farsça tamlama eki: önceki kelimeyi sonrakine bağlar (dil-i nâşâd = neşesiz gönül; sıra Türkçenin tersidir)"})
        i += 1
    bulunan = sum(1 for o in out if o["bulundu"] and not o.get("ek"))
    toplam = sum(1 for o in out if not o.get("ek"))
    return {"metin": metin, "kelimeler": out, "bulunan": bulunan, "toplam": toplam,
            "kalip": sum(1 for o in out if o.get("kalip"))}


def _satir(yazilan, bicim, k, yol):
    if not k:
        return {"yazilan": yazilan, "bicim": bicim, "anlam": None, "bulundu": False}
    return {"yazilan": yazilan, "bicim": bicim, "anlam": k["anlam"], "osmanli": k["osmanli"], "koken": k["koken"],
            "dil": k["dil"], "tur": k["tur"], "bulundu": True, "yol": yol}
