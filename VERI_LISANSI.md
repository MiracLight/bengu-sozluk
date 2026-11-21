# Veri, model ve yazı tipi lisansları

Uygulamanın kaynak kodu MIT lisanslıdır ([LICENSE](LICENSE)). Kurulum paketinde ve `veri/` klasöründe bulunan
içerik ise aşağıdaki kaynaklardan derlenmiştir ve **kendi lisanslarıyla** dağıtılır.

## Sözlük ve metin verisi — CC BY-SA 4.0

Üretilen veritabanı (`veri/bengu.db`), aşağıdaki Wikimedia projelerinden türetilmiştir ve bu nedenle
[Creative Commons Atıf-AynıLisanslaPaylaş 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.tr) lisansıyla
dağıtılır. Veritabanını ya da türevlerini paylaşan kişi kaynağı belirtmeli ve aynı lisansı kullanmalıdır.

| Kaynak | Adres | Not |
|---|---|---|
| Türkçe Vikisözlük katkıcıları | https://tr.wiktionary.org | [kaikki.org](https://kaikki.org/trwiktionary/) wiktextract çıkarımı |
| İngilizce Vikisözlük katkıcıları (Osmanlı Türkçesi, Eski Türkçe) | https://en.wiktionary.org | kaikki.org wiktextract çıkarımı |
| Türkçe Vikikaynak katkıcıları | https://tr.wikisource.org | Wikimedia dökümü; metinlerin kendisi kamu malıdır |
| Türkçe Vikisöz katkıcıları | https://tr.wikiquote.org | Wikimedia dökümü, "Türkçe atasözleri" listeleri |

Uygulama, her madde sayfasında ilgili kaydın kaynağını ve lisansını gösterir; tanık satırlarında Vikikaynak
sayfasının bağlantısı bulunur.

**Tanık derlemi seçimi:** Yalnız ölümünün üzerinden 70 yıl geçmiş yazarların eserleri ve anonim klasikler
(Orhun Yazıtları, Dede Korkut Kitabı) alınmıştır (`araclar/vikikaynak.py → YAZARLAR`). Siyasi konuşmalar ve resmî
belgeler alınmamıştır.

## Bengü derlemesi — CC BY-SA 4.0

`veri/derleme/` altındaki örnek maddeler, yazar biyografileri ve `cekirdek/cozumleme.py` içindeki eski biçimler
listesi Bengü katkıcılarınca hazırlanmıştır; uzman denetimi sürmektedir.

## Anlam modeli — MIT

[intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small) (Wang ve ark., Microsoft),
int8 ONNX dönüşümü: [Xenova/multilingual-e5-small](https://huggingface.co/Xenova/multilingual-e5-small).

## Yazı tipleri — SIL Open Font License 1.1

EB Garamond, Amiri, Cinzel Decorative, Noto Sans Old Turkic — [Google Fonts](https://fonts.google.com) üzerinden;
lisans: https://openfontlicense.org
