<p align="center"><img src="paket/bengu-512.png" width="128" alt="Bengü"></p>

<h1 align="center">Bengü — Türkçenin Ebedî Sözlüğü</h1>

<p align="center">
Türkiye Türkçesi, Osmanlı Türkçesi ve Eski Türkçe için bilgisayarınızda, <b>internet olmadan</b> çalışan sözlük ve edebiyat aracı.<br>
Öğrenciler, öğretmenler, edebiyatçılar ve akademisyenler için.
</p>

<p align="center">
<a href="https://github.com/MiracLight/bengu-sozluk/releases/latest"><b>⬇ Windows için indir</b></a> ·
<a href="#özellikler">Özellikler</a> · <a href="#kaynaklar-ve-lisanslar">Kaynaklar</a> · <a href="#geliştirme">Geliştirme</a>
</p>

---

## Kurulum

1. [Son sürüm sayfasından](https://github.com/MiracLight/bengu-sozluk/releases/latest) `Bengu-Kurulum-x.y.z.exe` dosyasını indirin.
2. Çift tıklayın, **İleri → Kur** deyin. Yönetici izni ve başka hiçbir program gerekmez (Windows 10 / 11).
3. Masaüstündeki **Bengü** simgesiyle açın.

> Kurulum dosyası kod imzası taşımadığı için Windows SmartScreen ilk açılışta uyarı gösterebilir:
> **Ek bilgi → Yine de çalıştır** deyin.

## Özellikler

- **194.000'i aşkın madde başı**, 3.000'i aşkın deyim ve atasözü; Arap harfli (Osmanlıca) yazılışlar, Göktürk harfli Eski Türkçe kayıtlar
- **Her tanımın kaynağı ayrı gösterilir** — hangi bilginin hangi sözlükten geldiği, lisansıyla birlikte
- **Osmanlıca ⇄ Türkçe karşılık bulucu** — "savaş" → harp حرب, cenk جنك, cidal جدال …; Latin ya da Arap harfiyle
- **Edebî metinlerde tanık** — Orhun Yazıtları'ndan Tanzimat sonrasına 840 metin, 38.000'i aşkın satır; dönem ve yazara göre süzme
- **Rehber** — sorunuzu kendi cümlenizle sorun:
  - *"kibir anlamına gelen kelimeler"*, *"sabırla ilgili atasözleri"*
  - *"Divan şiirinde ayrılık temalı beyitler"* → hicrân, firâk, firkat geçen beyitler
  - *"çözümle: Bir safâ bahşedelim gel şu dil-i nâşâde"* → kelime kelime çözümleme
  - *"gül ile kafiyeli kelimeler"*, *"kitabın kökeni nedir"*, *"aşk ile sevda arasındaki fark"*, *"Fuzûlî kimdir"*
- **42 yazarın** kısa biyografisi, önemli eserleri ve derlemdeki metinleri
- **Günün seçkileri**, İSNAD biçiminde atıf kopyalama, Defterim, Osmanlıca klavye

### Yapay zekâ hakkında

Rehber'deki anlam modeli ([multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small)) tamamen
bilgisayarınızda çalışır ve internete veri göndermez. **Model hiçbir zaman tanım ya da metin üretmez**: anlamca yakın
kayıtları bulmaya yardım eder; gösterilen her bilgi kaynağı belli bir sözlük kaydı ya da beyittir.

## Kaynaklar ve lisanslar

| Bileşen | Kaynak | Lisans |
|---|---|---|
| Uygulama kodu | bu depo | [MIT](LICENSE) |
| Türkçe ve Osmanlıca maddeler | [Türkçe Vikisözlük](https://tr.wiktionary.org) ([kaikki.org](https://kaikki.org) çıkarımı) | CC BY-SA 4.0 |
| Osmanlıca yazılış, köken, Eski Türkçe | [İngilizce Vikisözlük](https://en.wiktionary.org) (kaikki.org çıkarımı) | CC BY-SA 4.0 |
| Tanık metin derlemi | [Türkçe Vikikaynak](https://tr.wikisource.org) | Kamu malı / CC BY-SA 4.0 |
| Ek atasözü ve deyimler | [Türkçe Vikisöz](https://tr.wikiquote.org) | CC BY-SA 4.0 |
| Örnek maddeler, yazar biyografileri | Bengü derlemesi (`veri/derleme/`) | CC BY-SA 4.0 |
| Anlam modeli | intfloat/multilingual-e5-small | MIT |
| Yazı tipleri | EB Garamond, Amiri, Cinzel Decorative, Noto Sans Old Turkic | SIL OFL 1.1 |

Ayrıntılar: [VERI_LISANSI.md](VERI_LISANSI.md). Tanık derlemine yalnız ölümünün üzerinden 70 yıl geçmiş yazarların
eserleri alınmıştır.

**Bilinen sınırlar:** Vikisözlük kayıtlarındaki dönem bilgisi kelimenin kökenine göre otomatik atanır; bazı köken ve
Arap harfli yazılış eşleştirmeleri hatalı olabilir. Kāmûs-ı Türkî ve Redhouse sözlüklerinin mevcut makine okumaları
akademik kullanıma yetecek doğrulukta olmadığından henüz eklenmemiştir.

## Geliştirme

```powershell
pip install -r gereksinimler.txt pyinstaller
python araclar/indir.py          # ham kaynaklar ve model (~250 MB)
python araclar/aktar.py          # veri/bengu.db (~35 sn)
python araclar/vektor.py         # veri/vektor.npz (~3 dk)
python testler/rehber_testi.py   # doğruluk testi
python sunucu.py 5174            # http://127.0.0.1:5174
```

Kurulum paketi: `powershell -ExecutionPolicy Bypass -File paket\derle.ps1` (Inno Setup 6 gerekir).
Yeni sürüm: `surum.py` içindeki numarayı artırıp `vX.Y.Z` etiketi gönderilir; [GitHub Actions](.github/workflows/surum.yml)
paketi derleyip **Releases** sayfasına ekler. Kurulu uygulamalar internet varken yeni sürümü fark edip kullanıcıya bildirir.

Mimari ve ayrıntılar: [BENIOKU.md](BENIOKU.md).

## Katkı

Sözlük maddeleri, yazar biyografileri ve eski biçimler listesi (`cekirdek/cozumleme.py → ESKI_BICIM`) uzman gözüyle
gözden geçirilmeyi bekliyor. Hata bildirimi ve öneriler için [Issues](https://github.com/MiracLight/bengu-sozluk/issues).
