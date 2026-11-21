# Bengü — Türkçenin Ebedî Sözlüğü

Yerel bilgisayarda çalışan Türkçe – Eski Türkçe – Osmanlı Türkçesi sözlüğü.

## Klasörler

| Klasör | İçerik |
|---|---|
| `ui/` | Arayüz (HTML/CSS/JS, "eski kâğıt ve tezhip" teması) |
| `cekirdek/` | Arama motoru ve metin normalleştirme (Python, yalnız standart kitaplık) |
| `sunucu.py` | Yerel sunucu: arayüzü ve `/api/*` uçlarını yalnızca 127.0.0.1'e sunar |
| `araclar/aktar.py` | Ham kaynakları `veri/bengu.db` veritabanına aktarır |
| `veri/derleme/` | Elle hazırlanan maddeler ve yazarlar (JSON) — **düzenlenebilir asıl kaynak** |
| `veri/ham/` | İndirilen kaynak dosyaları (kaikki.org çıkarımları) |

## Çalıştırma (geliştirme)

```
python araclar/aktar.py     # veritabanını yeniden kurar (~25 sn)
python sunucu.py 5174       # http://127.0.0.1:5174
```

## Kurulum paketi (Windows)

```
powershell -ExecutionPolicy Bypass -File paket\derle.ps1            # veri + vektör + test + exe + kurulum
powershell -ExecutionPolicy Bypass -File paket\derle.ps1 -VeriAtla  # yalnız paketle
```

Çıktı: `dagitim\Bengu-Kurulum-<sürüm>.exe` (1.0.0: 168 MB; kurulu hâli 403 MB).

| Parça | Dosya | Görevi |
|---|---|---|
| Başlatıcı | `bengu_baslat.py` → `Bengu.exe` | Yerel sunucuyu boş bir bağlantı noktasında açar, Bengü'yü Edge uygulama kipinde ayrı pencerede gösterir (Edge yoksa varsayılan tarayıcı); pencere kapanınca (arayüzden 25 sn sinyal gelmezse) kapanır; ikinci açılışta yeni sunucu başlatmaz |
| Paketleyici | `paket/bengu.spec` | PyInstaller, klasör kipi (hızlı açılış); veritabanı, vektör dizini, model, arayüz ve gömülü yazı tipleri dahil |
| Kurulum | `paket/bengu.iss` | Inno Setup; yönetici izni gerektirmez, `%LOCALAPPDATA%\Programs\Bengu`'ya kurar; Başlat menüsü + isteğe bağlı masaüstü kısayolu; sabit AppId sayesinde yeni sürümler üzerine kurulur |
| Öz test | `Bengu.exe --oztest` | Veritabanı, arama, Arap harfli arama, çeviri, tanık, çözümleme, Rehber ve modeli sınar; Başlat menüsünde "Bengü öz testi" kısayolu |

Kullanıcı verisi (Defterim, Rehber geçmişi, pencere profili, `gunluk.txt`) `%LOCALAPPDATA%\Bengu` altında durur;
kaldırma işlemi bunlara dokunmaz. Veritabanı salt okunur ve değişmez (`immutable`) açılır; kurulum klasörüne hiç yazılmaz.

**GitHub notu:** `veri/bengu.db` (127 MB) GitHub'ın 100 MB dosya sınırını aşar; `.gitignore` onu ve diğer üretilen
dosyaları dışarıda bırakır. Depoya kaynak kod ve derleme betikleri girer; kurulum dosyası "Releases" sayfasına eklenir.

## Veri kaynakları ve lisans

- **Bengü derlemesi** — elle hazırlanmış tanıklı maddeler ve yazar biyografileri (uzman denetimi bekliyor).
- **Türkçe Vikisözlük** — CC BY-SA 4.0, kaikki.org (wiktextract) çıkarımı: `https://kaikki.org/trwiktionary/`
- **İngilizce Vikisözlük, Osmanlı Türkçesi ve Eski Türkçe** — CC BY-SA 4.0, kaikki.org çıkarımı.

- **Türkçe Vikikaynak** (tanık derlemi) — Wikimedia dökümü `dumps.wikimedia.org/trwikisource`, kamu malı / CC BY-SA.
  `araclar/vikikaynak.py` yalnız beyaz listedeki yazarları (ölümünün üzerinden 70 yıl geçmiş) ve anonim klasikleri
  (Orhun Yazıtları, Dede Korkut) alır; siyasi konuşmalar ve resmî belgeler alınmaz. Orhun tablosundan çeviri yazı,
  Göktürk harfli asıl ve Türkiye Türkçesi çevirisi ayrı ayrı çıkarılır. Yeni yazar eklemek için `YAZARLAR` sözlüğüne
  ekleyip biyografisini `veri/derleme/yazarlar_ek.json` dosyasına yazın.
- **Türkçe Vikisöz** — "Türkçe atasözleri/A…Z" listelerinden, başka kaynakta olmayan atasözü ve deyimler (açıklamasız).

### Denenip şimdilik alınmayanlar

| Kaynak | Neden |
|---|---|
| Redhouse, *Turkish and English Lexicon* (1890) | Internet Archive makine okuması: ~18 bin madde ayrıştırılabildi ama yalnız ~2.800'ü doğrulanabildi ve tanımların çoğu bozuk. `araclar/redhouse.py` deneme ayrıştırıcısı olarak duruyor. |
| Redhouse, *Turkish Dictionary* (1880) | Çeviri yazı kısmı okunamayacak kadar bozuk. |
| Kāmûs-ı Türkî (1901) | Mevcut Arap harfli makine okuması kullanılamaz; Osmanlıca'ya özel bir okuma modeliyle yeniden işlenmeli. |

CC BY-SA gereği: veritabanı dağıtılırken kaynak gösterilmeli ve aynı lisansla paylaşılmalıdır.
Uygulama her kaydın kaynağını ve lisansını madde sayfasında gösterir.

## Osmanlıca ⇄ Türkçe karşılıklar (`cekirdek/ceviri.py`)

Yapay zekâ kullanmaz; aktarım sırasında kurulan `karsilik` tablosundaki belgelenmiş ilişkilerden öneri üretir:

| Güven | Yol | Örnek |
|---|---|---|
| tam karşılık | Osmanlıca/Ar./Fa. kaydın Türkçe tanımında kelime geçiyor | hasret: "özlem" |
| eş anlamlı | Vikisözlük eş anlamlı bağlantısı | özlem ↔ tahassür |
| yakın anlam | İngilizce köprü (özlem → longing → …) | en düşük güven, gürültülü olabilir |

Ters yön (Osmanlıca → Türkçe) Latin ya da Arap harfiyle çalışır; Arap harfleri harekesiz ve ي/ی, ك/ک farkı gözetilmeden eşleştirilir.
Birden çok kelime yazılırsa her kelime için ayrı öneri listesi döner.

## Rehber ve yapay zekâ (`cekirdek/rehber.py`, `cekirdek/anlam.py`)

İlke: **yapay zekâ bulur, üretmez.** Rehber hiçbir zaman tanım ya da metin yazmaz; gösterdiği her şey kaynaklı kayıttır.

1. **Kural tabanlı çözümleyici** (modelsiz, her bilgisayarda): sorudan niyet (karşılık / anlam / kavram / tanık),
   kavram ve süzgeçleri (köken, tür, yazar, dönem, gelenek) çıkarır; kelimeyi çekim sözlüğüyle sözlük biçimine indirir.
2. **Anlamsal arama** (isteğe bağlı): `multilingual-e5-small` (MIT, int8 ONNX, 118 MB, `modeller/e5-small/`).
   Kavram sözlükteki kendi tanımıyla genişletilir (küçük model tek kelimede zayıf), sonuç anlamsal puan +
   tanım örtüşmesiyle karma puanlanır ve eşik altı elenir.
3. **Tema araması**: kavram + tanımının bir parçası tam olarak kavram olan kelimeler (ayrılık → hicrân, firâk, firkat),
   derlemde geçme sıklığına göre; eski metinlerde modelden daha isabetlidir.

```
pip install -r gereksinimler.txt      # isteğe bağlı anlamsal arama için
python araclar/vektor.py              # veri/vektor.npz (~46 MB, ~3 dk); aktar.py'den sonra
python testler/rehber_testi.py        # 17 örnek soruda niyet/kavram/süzgeç/sonuç doğruluğu
```

Model ya da vektör dosyası yoksa Rehber kural tabanlı çalışır (test iki durumda da geçer).

### Rehber'in anladığı soru türleri

| Niyet | Örnek | Kaynak |
|---|---|---|
| Osmanlıca karşılık | "savaşın Osmanlıcası", "özlem için Farsça bir kelime" | karşılık tablosu |
| Anlam | "nihan ne demek", "حسرت" | Osmanlıca kayıtlar |
| Anlama/konuya göre kelime | "kibir anlamına gelen kelimeler", "sabırla ilgili atasözleri" | karma (anlamsal + tanım) |
| Tanık / tema | "Fuzûlî'nin aşk geçen beyitleri", "Divan şiirinde ayrılık temalı beyitler" | Vikikaynak derlemi |
| **Çözümleme** | "çözümle: Bir safâ bahşedelim gel şu dil-i nâşâde" (izafetli metinler kendiliğinden) | `cekirdek/cozumleme.py` |
| **Kafiye** | "gül ile kafiyeli kelimeler", "-dâr ile biten Farsça kelimeler" | sözlük + derlem sıklığı |
| **Köken** | "kitabın kökeni nedir" | kayıtların köken alanları |
| **Eş / zıt anlamlı** | "hasret kelimesinin eş anlamlısı", "güzel kelimesinin zıt anlamlısı" | Vikisözlük bağlantıları + tanımlar |
| **Karşılaştırma** | "aşk ile sevda arasındaki fark" | iki maddenin tanımları, kökenleri, tanık sayıları |
| **Yazar** | "Fuzûlî kimdir", "Tanzimat yazarları" | yazar derlemesi |

Her yanıtta şablonla kurulan bir özet ("60 kayıt bulundu. Köken dağılımı: …") ve Rehber'in anlayacağı hazır
soru önerileri bulunur. Çözümleyici, sözlükte olmayan eski Anadolu Türkçesi biçimleri için küçük bir liste kullanır
(men = ben, menüm = benim, yoh = yok, degül = değil …; `cozumleme.py` → `ESKI_BICIM`).

## Bilinen sınırlar

- Dönem bilgisi Vikisözlük kayıtlarında **kökene göre otomatik** atanır (Eski Türkçe kökenli → İslamiyet öncesi,
  Arapça/Farsça → İslamî dönem, Batı dilleri → Batı etkisi). Edebî dönem sınıflaması için uzman düzeltmesi gerekir.
- Osmanlıca ve Eski Türkçe kayıtların bir kısmında açıklamalar İngilizcedir (Wiktionary kaynaklı).
- Arap harfli yazılış, Türkçe kayıtlara Osmanlıca kaynaklardan eşleştirmeyle eklenir; eş sesli kelimelerde hatalı eşleşme olabilir.
