// Bengü — arayüz sabitleri.
// Sözlük verisi artık veri/bengu.db veritabanında; elle hazırlanan maddeler ve yazarlar veri/derleme/*.json içinde.

const DONEMLER = {
  "islam-oncesi": { ad: "İslamiyet Öncesi", aralik: "VIII. yy ve öncesi" },
  "gecis":        { ad: "Geçiş Dönemi",     aralik: "XI–XII. yy" },
  "islami":       { ad: "İslamî Dönem",     aralik: "XIII–XIX. yy" },
  "bati":         { ad: "Batı Etkisi",      aralik: "1839 sonrası" },
  "gunumuz":      { ad: "Günümüz Türkçesi", aralik: "Cumhuriyet ve sonrası" }
};

const KOKENLER = { T: "Türkçe", Ar: "Arapça", Fa: "Farsça", Bt: "Batı dilleri", "Diğer": "Diğer" };
const DILLER = { tr: "Türkiye Türkçesi", ota: "Osmanlı Türkçesi", otk: "Eski Türkçe" };
const TURLER = ["kelime", "tamlama", "söz öbeği", "deyim", "atasözü", "sanat", "özel ad"];
const GELENEKLER = { "Yazıt": "Yazıtlar", "Karahanlı": "Karahanlı Türkçesi", "Tekke": "Tekke / Tasavvuf", "Divan": "Divan", "Halk": "Halk (Âşık)", "Yeni": "Batı Etkisi" };

// Çevrimiçi moddayken taranacak ek kaynaklar (Faz 3'te bağlanacak).
const CEVRIMICI_KAYNAKLAR = [
  { ad: "Güncelleme denetimi", aciklama: "GitHub'da yeni Bengü sürümü olup olmadığına bakılır (yalnız sürüm numarası sorulur)", durum: "açık" },
  { ad: "Vikisözlük (canlı)", aciklama: "Yerel kopyadan sonra eklenen yeni maddeler ve düzeltmeler", durum: "planlandı" },
  { ad: "Vikikaynak", aciklama: "Kamu malı edebî metinlerde tanık beyit / cümle taraması", durum: "planlandı" },
  { ad: "Internet Archive", aciklama: "Kāmûs-ı Türkî, Redhouse 1890 gibi taranmış eski sözlükler", durum: "planlandı" },
  { ad: "TDK Sözlükleri", aciklama: "Yalnızca bağlantı: madde TDK sitesinde açılır", durum: "planlandı" }
];
