"""Bengü — Vikikaynak (tr.wikisource) dökümünden tanık metin derlemi.

Yalnız kamu malı edebî metinler alınır: ölümünün üzerinden 70 yıl geçmiş yazarlar (beyaz liste) ve
anonim klasikler (Orhun Yazıtları, Dede Korkut). Siyasi konuşmalar, resmî belgeler ve çağdaş metinler alınmaz.
Lisans: Vikikaynak metinleri kamu malı / CC BY-SA.
"""
import bz2
import re
import xml.etree.ElementTree as ET
from pathlib import Path

DOKUM = Path(__file__).resolve().parent.parent / "veri" / "ham" / "vikikaynak" / "trwikisource.xml.bz2"

# Vikikaynak'taki yazım biçimi → (Bengü yazar kimliği, dönem, gelenek, ölüm yılı)
YAZARLAR = {
    "Yunus Emre": ("yunus-emre", "islami", "Tekke", 1320), "Bursalı Âşık Yunus": ("yunus-emre", "islami", "Tekke", 1320),
    "Bâkî": ("baki", "islami", "Divan", 1600), "Baki": ("baki", "islami", "Divan", 1600),
    "Fuzûlî": ("fuzuli", "islami", "Divan", 1556), "Fuzuli": ("fuzuli", "islami", "Divan", 1556),
    "Nedîm": ("nedim", "islami", "Divan", 1730), "Nedim": ("nedim", "islami", "Divan", 1730),
    "Şeyh Gâlib": ("seyh-galib", "islami", "Divan", 1799), "Şeyh Galib": ("seyh-galib", "islami", "Divan", 1799),
    "Karacaoğlan": ("karacaoglan", "islami", "Halk", 1700),
    "Namık Kemal": ("namik-kemal", "bati", "Yeni", 1888), "Tevfik Fikret": ("tevfik-fikret", "bati", "Yeni", 1915),
    "Nâbî": ("nabi", "islami", "Divan", 1712), "Nabi": ("nabi", "islami", "Divan", 1712),
    "Nef'î": ("nefi", "islami", "Divan", 1635), "Nefî": ("nefi", "islami", "Divan", 1635), "Nef’î": ("nefi", "islami", "Divan", 1635),
    "Necâtî": ("necati", "islami", "Divan", 1509), "Necati": ("necati", "islami", "Divan", 1509),
    "Ahmed Paşa": ("ahmed-pasa", "islami", "Divan", 1497), "Zâtî": ("zati", "islami", "Divan", 1546),
    "Süleyman Çelebi": ("suleyman-celebi", "islami", "Tekke", 1422),
    "Eşrefoğlu Rumî": ("esrefoglu-rumi", "islami", "Tekke", 1469), "Eşrefoğlu Rûmî": ("esrefoglu-rumi", "islami", "Tekke", 1469),
    "Seyyid Nesimi": ("nesimi", "islami", "Tekke", 1417), "Seyyid Nesîmî": ("nesimi", "islami", "Tekke", 1417), "Nesîmî": ("nesimi", "islami", "Tekke", 1417),
    "Şah Hatayi": ("hatayi", "islami", "Tekke", 1524), "Şah Hatâyî": ("hatayi", "islami", "Tekke", 1524), "Hatayi": ("hatayi", "islami", "Tekke", 1524),
    "Pir Sultan Abdal": ("pir-sultan", "islami", "Halk", 1590), "Kul Himmet": ("kul-himmet", "islami", "Halk", 1600),
    "Kul Nesimi": ("kul-nesimi", "islami", "Tekke", 1700), "Köroğlu": ("koroglu", "islami", "Halk", 1600),
    "Kaygusuz Abdal": ("kaygusuz", "islami", "Tekke", 1444), "Dadaloğlu": ("dadaloglu", "islami", "Halk", 1868),
    "Âşık Ömer": ("asik-omer", "islami", "Halk", 1707), "Erzurumlu Emrah": ("emrah", "islami", "Halk", 1860),
    "Kanuni Sultan Süleyman": ("kanuni", "islami", "Divan", 1566), "II. Mehmed": ("fatih", "islami", "Divan", 1481),
    "Yavuz Sultan Selim": ("yavuz", "islami", "Divan", 1520), "II. Bayezid": ("bayezid2", "islami", "Divan", 1512),
    "Ziya Paşa": ("ziya-pasa", "bati", "Yeni", 1880), "İbrahim Şinâsî": ("sinasi", "bati", "Yeni", 1871), "Şinasi": ("sinasi", "bati", "Yeni", 1871),
    "Abdülhak Hamit Tarhan": ("abdulhak-hamid", "bati", "Yeni", 1937), "Abdülhak Hâmid": ("abdulhak-hamid", "bati", "Yeni", 1937),
    "Recaizade Mahmud Ekrem": ("recaizade", "bati", "Yeni", 1914), "Muallim Naci": ("muallim-naci", "bati", "Yeni", 1893),
    "Cenap Şahabettin": ("cenap", "bati", "Yeni", 1934), "Ahmet Haşim": ("ahmet-hasim", "bati", "Yeni", 1933),
    "Mehmet Âkif Ersoy": ("mehmet-akif", "bati", "Yeni", 1936), "Mehmet Akif Ersoy": ("mehmet-akif", "bati", "Yeni", 1936),
    "Ziya Gökalp": ("ziya-gokalp", "bati", "Yeni", 1924), "Ömer Seyfettin": ("omer-seyfettin", "bati", "Yeni", 1920),
    "Mehmet Emin Yurdakul": ("mehmet-emin", "bati", "Yeni", 1944), "Celâl Sahir Erozan": ("celal-sahir", "bati", "Yeni", 1935),
    "Neyzen Tevfik": ("neyzen-tevfik", "bati", "Yeni", 1953), "Orhan Veli Kanık": ("orhan-veli", "gunumuz", "Yeni", 1950),
    "Halit Ziya Uşaklıgil": ("halit-ziya", "bati", "Yeni", 1945), "Ahmet Mithat Efendi": ("ahmet-mithat", "bati", "Yeni", 1912),
}
ANONIM = [  # (başlık deseni, eser adı, yazar kimliği, dönem, gelenek)
    (re.compile(r"^Orhun Yazıtları"), "Orhun Yazıtları", "yollug-tigin", "islam-oncesi", "Yazıt"),
    (re.compile(r"^(Dede Korkut|Kitâb-ı Dedem Korkut)"), "Dede Korkut Kitabı", "dede-korkut", "islami", "Halk"),
]
ANTOLOJI = re.compile(r"^(Bektaşî Şairleri ve Nefesleri|Bektaşi Şairleri ve Nefesleri|Halk Edebiyatı Antolojisi)/(.+)$")
PARANTEZ = re.compile(r"^(.*?)\s*\(([^()]+)\)\s*$")
YAZAR_ALAN = re.compile(r"\|\s*yazar\s*=\s*([^\n|}]+)", re.I)
BASLIK_ALAN = re.compile(r"\|\s*başlık\s*=\s*([^\n|}]+)", re.I)


def temizle(txt):
    """Viki işaretlemesini atıp düz şiir/metin satırları bırakır."""
    t = re.sub(r"<ref[^>]*?/>|<ref.*?</ref>", "", txt, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"\{\{\s*eser[^{}]*\}\}", "", t, flags=re.S | re.I)
    # {{söz|...}}, {{center|...}} gibi şablonların içeriğini koru
    for _ in range(3):
        t = re.sub(r"\{\{\s*(?:söz|center|ortala|sağ|şiir|poem|block center|kenar boşluğu)[^|{}]*\|([^{}]*)\}\}", r"\1", t, flags=re.I | re.S)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t, flags=re.S)
    t = re.sub(r"\[\[(?:Kategori|Category|Dosya|File|Resim|Image):[^\]]*\]\]", "", t, flags=re.I)
    t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\s*([^\]]*)\]", r"\1", t)
    t = re.sub(r"</?(poem|center|div|span|p|big|small|i|b|sup|sub|br|font|table|tr|td)[^>]*>", "\n", t, flags=re.I)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"^[=:*#;|!{}].*$", "", t, flags=re.M)  # başlık, tablo, liste işaretleri
    return t


def satirlar(txt):
    """Kıtalara (boş satırla ayrılan bloklar) bölünmüş satır listesi: [(kita_no, satir), …]"""
    out, kita = [], 0
    for blok in re.split(r"\n\s*\n", temizle(txt)):
        dolu = False
        for s in blok.split("\n"):
            s = re.sub(r"\s+", " ", s).strip(" \t ")
            if 3 <= len(s) <= 220 and re.search(r"[A-Za-zÇĞİÖŞÜçğıöşüâîû]{2,}", s) and not s.startswith(("http", "Kaynak", "Not:")):
                out.append((kita, s))
                dolu = True
        if dolu:
            kita += 1
    return out


def orhun_satirlari(txt):
    """Orhun Yazıtları tablosu: | no | kod | Göktürk harfli | harf çevirisi | çeviri yazı | Türkiye Türkçesi |
    → [(kita, çeviri_yazı, türkçe_çeviri, göktürk), …]"""
    out = []
    kita = 0
    for bolum in re.split(r"\n==+[^=\n]+==+\n", txt):
        for satir in re.split(r"\n\|-", bolum):
            hucreler = []
            for s in satir.split("\n"):
                if s.startswith("|") and not s.startswith(("|+", "|}", "|-")):
                    h = s[1:]
                    if re.match(r"\s*style\s*=", h) and "|" in h:
                        h = h.split("|", 1)[1]
                    hucreler.append(h.strip())
            if len(hucreler) >= 6:
                yazi, cev, tr = hucreler[2], hucreler[4] or hucreler[3], hucreler[5]
                cev = re.sub(r"\s*:\s*", " ", cev).strip()
                if cev and tr:
                    out.append((kita, cev, re.sub(r"'{2,}", "", tr), re.sub(r"\s*:\s*", " ", yazi).strip()))
        kita += 1
    return out


def yazar_bul(baslik, txt):
    m = YAZAR_ALAN.search(txt)
    if m:
        ad = re.sub(r"\[\[|\]\]|Yazar:", "", m.group(1)).strip()
        if ad in YAZARLAR:
            return ad, (BASLIK_ALAN.search(txt).group(1).strip() if BASLIK_ALAN.search(txt) else baslik.split("/")[0])
    m = PARANTEZ.match(baslik)
    if m and m.group(2).strip() in YAZARLAR:
        return m.group(2).strip(), m.group(1).strip()
    m = ANTOLOJI.match(baslik)
    if m and m.group(2).strip() in YAZARLAR:
        return m.group(2).strip(), m.group(1)
    for ad in YAZARLAR:
        if re.search(r"\[\[\s*(?:Kategori|Category)\s*:\s*" + re.escape(ad) + r"(?:\s|\]|\|)", txt):
            return ad, baslik.split("/")[-1]
    return None, None


SAYFALAR = re.compile(r"<pages\s+index\s*=\s*\"?([^\"/>]+?)\"?\s+from\s*=\s*\"?(\d+)\"?\s+to\s*=\s*\"?(\d+)\"?[^>]*/>", re.I)


def _oku():
    """Dökümü bir kez okuyup ad alanlarına ayırır: metin sayfaları, taranmış sayfalar (Sayfa:), yazar sayfaları."""
    ana, tarama, yazar_sayfasi = [], {}, {}
    for _, el in ET.iterparse(bz2.open(DOKUM), events=("end",)):
        if not el.tag.endswith("}page"):
            continue
        ns = el.find("{*}ns").text
        baslik = el.find("{*}title").text
        txt = el.find("{*}revision/{*}text").text or ""
        yonlendirme = el.find("{*}redirect") is not None
        el.clear()
        if yonlendirme:
            continue
        if ns == "0":
            ana.append((baslik, txt))
        elif ns == "250":  # Sayfa: (taranmış kitap sayfalarının metni)
            # <noinclude> başlık/altlık kısımlarını at
            tarama[baslik.split(":", 1)[1]] = re.sub(r"<noinclude>.*?</noinclude>", "", txt, flags=re.S)
        elif ns == "100":  # Yazar:
            yazar_sayfasi[baslik.split(":", 1)[1]] = txt
    return ana, tarama, yazar_sayfasi


def metinler():
    """(yazar_adı, yazar_id, dönem, gelenek, eser, sayfa_başlığı, satırlar) üretir."""
    ana, tarama, yazar_sayfasi = _oku()
    # Yazar sayfalarındaki eser bağlantıları → sayfa başlığı: yazar adı
    yazar_eseri = {}
    for ad, txt in yazar_sayfasi.items():
        if ad not in YAZARLAR:
            continue
        for hedef in re.findall(r"\[\[([^\]|#]+)", txt):
            hedef = hedef.strip()
            if not re.match(r"(?i)(Kategori|Category|Dosya|File|Yazar|w|wikipedia|Vikipedi):", hedef):
                yazar_eseri.setdefault(hedef, ad)
    # Ana sayfaların başlık → yazar eşlemesini alt sayfalara da yay (Eser/Bölüm)
    for baslik, txt in ana:
        if txt.lstrip().lower().startswith("#yönlendi") or "{{anlam ayrımı" in txt.lower():
            continue
        if baslik.startswith("Orhun Yazıtları ("):
            s = orhun_satirlari(txt)
            if s:
                eser = baslik[baslik.index("(") + 1:-1] + " Yazıtı"
                yield None, "yollug-tigin" if "Tonyukuk" not in baslik else "tonyukuk", "islam-oncesi", "Yazıt", eser, baslik, s
            continue
        # Taranmış sayfalardan aktarılan metni ekle
        for dosya, bas, son in SAYFALAR.findall(txt):
            bas, son = int(bas), int(son)
            if son - bas <= 400:
                txt += "\n\n" + "\n\n".join(tarama.get(f"{dosya.strip()}/{i}", "") for i in range(bas, son + 1))
        ad, eser = yazar_bul(baslik, txt)
        if not ad:
            kok = baslik.split("/")[0]
            ad = yazar_eseri.get(baslik) or yazar_eseri.get(kok)
            eser = kok if ad else None
        if ad:
            yid, donem, gelenek, _ = YAZARLAR[ad]
        else:
            an = next((a for a in ANONIM if a[0].search(baslik)), None)
            if not an:
                continue
            ad, eser, yid, donem, gelenek = None, an[1], an[2], an[3], an[4]
        s = satirlar(txt)
        if len(s) >= 2:
            yield ad, yid, donem, gelenek, eser, baslik, s
