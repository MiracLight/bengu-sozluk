// Bengü — arayüz mantığı (veriyi yerel sunucunun /api uçlarından okur)
(function () {
  "use strict";

  const $ = (s, k = document) => k.querySelector(s);
  const icerik = $("#icerik");

  // ---------- Yardımcılar ----------
  const kacis = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const sayi = n => Number(n).toLocaleString("tr-TR");
  const bag = b => "#/madde/" + encodeURIComponent(b);

  async function api(yol, p = {}) {
    const qs = new URLSearchParams(Object.entries(p).filter(([, v]) => v !== "" && v != null)).toString();
    const r = await fetch(`/api/${yol}${qs ? "?" + qs : ""}`);
    if (r.status === 404) return null;
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).hata || r.statusText);
    return r.json();
  }

  function bildir(metin) {
    const b = $("#bildirim");
    b.textContent = metin;
    b.classList.add("goster");
    clearTimeout(bildir.t);
    bildir.t = setTimeout(() => b.classList.remove("goster"), 3200);
  }

  const depo = {
    al(k, v) { try { return JSON.parse(localStorage.getItem(k)) ?? v; } catch { return v; } },
    koy(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* yoksay */ } }
  };
  const defter = () => depo.al("bengu-defter2", []);

  const rozetKoken = k => k ? `<span class="rozet ${kacis(k)}">${kacis(KOKENLER[k] || k)}</span>` : "";
  const rozetTur = t => `<span class="rozet tur">${kacis(t)}</span>`;
  const rozetDil = d => d && d !== "tr" ? `<span class="rozet dil">${kacis(DILLER[d])}</span>` : "";
  const rozetDonem = ds => (ds || []).filter(d => DONEMLER[d]).map(d => `<span class="rozet donem">${DONEMLER[d].ad}</span>`).join("");
  const beyitHTML = metin => kacis(metin).split(" / ").map(m => `<span class="misra">${m}</span>`).join("");
  const yazarBag = (ad, id) => id ? `<a class="yazar-bag" href="#/yazar/${kacis(id)}">${kacis(ad)}</a>` : kacis(ad);
  const yukleniyor = () => { icerik.innerHTML = `<p class="bos" style="text-align:center">Yükleniyor…</p>`; };
  const hata = e => { icerik.innerHTML = `<p class="bos" style="text-align:center">Bir sorun oluştu: ${kacis(e.message)}</p>`; };

  // Künye: derleme tanıklarında yazar/eser/yüzyıl; Vikisözlük örneklerinde ham "ref"
  function kunye(o, baglantili = true) {
    if (o.yuzyil || o.yazar_id) return `${baglantili ? yazarBag(o.yazar, o.yazar_id) : kacis(o.yazar)}, <i>${kacis(o.eser)}</i>${o.yuzyil ? ", " + kacis(o.yuzyil) : ""}`;
    return kacis(o.ref || o.yazar || "");
  }

  // ---------- Ana sayfa ----------
  async function anaSayfa() {
    yukleniyor();
    const [g, ist] = await Promise.all([api("gunun"), api("istatistik")]);
    const tarih = new Date().toLocaleDateString("tr-TR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    const k = g.kelime?.kayitlar.find(x => x.tur !== "özel ad") || g.kelime?.kayitlar[0];
    const kTanik = g.kelime?.kayitlar.flatMap(x => x.ornekler)[0];
    const yazilis = g.kelime ? [...new Set(g.kelime.kayitlar.map(x => x.osmanli).filter(Boolean))][0] : null;

    icerik.innerHTML = `
      <section class="karsilama">
        <svg class="besmele-motif" viewBox="0 0 120 24" aria-hidden="true"><path d="M0 12h44M76 12h44" stroke="#b08a3e"/><path d="M60 2l8 10-8 10-8-10z" fill="#7a2e2a"/><circle cx="48" cy="12" r="3" fill="#b08a3e"/><circle cx="72" cy="12" r="3" fill="#b08a3e"/></svg>
        <div class="tarih">${tarih}</div>
        <div class="sayaclar">${sayi(ist.baslik)} madde başı · ${sayi(ist.deyim)} deyim · ${sayi(ist.atasozu)} atasözü · ${sayi(ist.osmanli)} Arap harfli yazılış · ${sayi(ist.ornek)} örnek cümle · ${sayi(ist.eser)} edebî metinden ${sayi(ist.satir)} tanık satırı</div>
      </section>

      <h2 class="bolum-baslik">Günün Seçkileri</h2>
      <div class="izgara">
        ${k ? `<article class="kart suslu gunun-kelimesi k-8">
          <div class="etiket">Günün Kelimesi</div>
          <h2>${kacis(g.kelime.baslik)}</h2>
          <div class="yazilislar">
            ${yazilis ? `<span class="arap">${kacis(yazilis)}</span>` : ""}
            ${k.ceviri ? `<span class="ceviri">${kacis(k.ceviri)}</span>` : ""}
            ${rozetKoken(k.koken)} ${rozetDonem(k.donem)}
          </div>
          <p>${kacis(k.anlamlar[0]?.metin)}</p>
          ${kTanik ? `<div class="beyit" style="text-align:left;font-size:19px">${beyitHTML(kTanik.metin)}</div>
          <div class="kaynak-satir" style="text-align:left">${kunye(kTanik)}</div>` : ""}
          <a class="devam" href="${bag(g.kelime.baslik)}">Maddenin tamamı →</a>
        </article>` : ""}

        <article class="kart k-4">
          ${g.deyim ? `<div class="etiket">Günün Deyimi</div>
          <h3><a href="${bag(g.deyim.baslik)}">${kacis(g.deyim.baslik)}</a></h3>
          <p>${kacis(g.deyim.anlam)}</p>` : ""}
          <hr style="border:0;border-top:1px dashed var(--cizgi);margin:16px 0">
          ${g.atasozu ? `<div class="etiket">Günün Atasözü</div>
          <h3><a href="${bag(g.atasozu.baslik)}">${kacis(g.atasozu.baslik)}</a></h3>
          <p>${kacis(g.atasozu.anlam)}</p>` : ""}
        </article>

        ${g.beyit ? `<article class="kart suslu k-8">
          <div class="etiket">Günün Beyti</div>
          <div class="beyit">${beyitHTML(g.beyit.metin)}</div>
          <div class="kaynak-satir">${g.beyit.metin_id ? `${yazarBag(g.beyit.yazar, g.beyit.yazar_id)}, <a href="#/metin/${g.beyit.metin_id}"><i>${kacis(g.beyit.eser)}</i></a>` : kunye(g.beyit)}</div>
          ${g.beyit.aciklama ? `<p class="kaynak-satir" style="font-style:italic">${kacis(g.beyit.aciklama)}</p>` : ""}
        </article>` : ""}

        ${g.sanat ? `<article class="kart k-4">
          <div class="etiket">Günün Edebî Sanatı</div>
          <h3><a href="${bag(g.sanat.baslik)}">${kacis(g.sanat.baslik)}</a> <span class="arap" style="font-size:22px">${kacis(g.sanat.osmanli)}</span></h3>
          <p style="font-size:16px">${kacis(g.sanat.anlam)}</p>
        </article>` : ""}
      </div>

      <section class="kart rehber-cagri">
        <div><div class="etiket">Rehber ✦</div><h3 style="margin:2px 0">Sorunuzu kendi cümlenizle sorun</h3></div>
        <div class="ornek-kelimeler" style="margin:0">${REHBER_ORNEK.slice(0, 5).map(o => `<a href="#/rehber/${encodeURIComponent(o)}">${kacis(o)}</a>`).join("")}</div>
      </section>

      <h2 class="bolum-baslik">Dönemlere Göre Gezin</h2>
      <nav class="donem-seridi">
        ${Object.entries(DONEMLER).map(([k, d]) => `<a href="#/donem/${k}"><b>${d.ad}</b><span>${d.aralik} · ${sayi(ist.donem[k] || 0)} kayıt</span></a>`).join("")}
      </nav>`;
  }

  // ---------- Arama ----------
  async function sonucSayfasi(sorgu, sec = {}, sayfa = 1, ekle = false) {
    if (!ekle) yukleniyor();
    const p = { q: sorgu, sayfa };
    for (const ad of ["donem", "koken", "tur", "dil", "kaynak"]) p[ad] = (sec[ad] || []).join(",");
    const r = await api("ara", p);

    const kart = g => {
      const k = g.kayitlar[0];
      const osm = g.kayitlar.map(x => x.osmanli).find(Boolean);
      const eski = g.kayitlar.map(x => x.eski_yazi).find(Boolean);
      const kaynakSay = new Set(g.kayitlar.map(x => x.kaynak_id)).size;
      const kn = g.kayitlar.map(x => x.kunye).find(Boolean);
      const [yz, es, yy] = (kn || "||").split("|");
      return `<a class="sonuc kart" href="${bag(g.baslik)}">
        <h3>${kacis(g.baslik)} ${osm ? `<span class="arap">${kacis(osm)}</span>` : ""} ${eski ? `<span class="gokturk">${kacis(eski)}</span>` : ""}
          <span>${rozetTur(k.tur)}${rozetKoken(k.koken)}${rozetDil(k.dil)}</span></h3>
        <p>${kacis(k.anlam)}${k.aciklama_dili === "en" ? ` <span class="ing">(İng.)</span>` : ""}</p>
        <p class="sonuc-alt">${kn ? `${kacis(yz)}${es ? `, <i>${kacis(es)}</i>` : ""}${yy ? ", " + kacis(yy) : ""} · ` : ""}${kaynakSay} kaynak${g.kayitlar.length > 1 ? `, ${g.kayitlar.length} kayıt` : ""}</p>
      </a>`;
    };

    if (ekle) {
      $("#dahaTus")?.remove();
      $("#sonucListe").insertAdjacentHTML("beforeend", r.sonuclar.map(kart).join("") + dahaTus(r));
      return;
    }
    const kutu = (ad, deger, etiket) => `<label><input type="checkbox" name="${ad}" value="${kacis(deger)}" ${(sec[ad] || []).includes(deger) ? "checked" : ""}> ${kacis(etiket)}</label>`;
    icerik.innerHTML = `
      <div class="sonuc-duzen">
        <aside class="suzgec kart" id="suzgec">
          <h4>Dönem</h4>${Object.entries(DONEMLER).map(([k, d]) => kutu("donem", k, d.ad)).join("")}
          <h4>Dil</h4>${Object.entries(DILLER).map(([k, d]) => kutu("dil", k, d)).join("")}
          <h4>Köken</h4>${Object.entries(KOKENLER).map(([k, d]) => kutu("koken", k, d)).join("")}
          <h4>Tür</h4>${TURLER.map(t => kutu("tur", t, t[0].toLocaleUpperCase("tr") + t.slice(1))).join("")}
          <h4>Kaynak</h4>${kutu("kaynak", "bengu", "Bengü derlemesi")}${kutu("kaynak", "trwikt", "Türkçe Vikisözlük")}${kutu("kaynak", "enwikt-ota", "Wiktionary (Osmanlıca)")}${kutu("kaynak", "enwikt-otk", "Wiktionary (Eski Türkçe)")}
        </aside>
        <section>
          <p class="sonuc-bilgi">“${kacis(sorgu)}” için ${sayi(r.toplam)} madde başı</p>
          ${r.kok ? `<div class="kok-notu">Aradığınız “<b>${kacis(r.kok.sorgu)}</b>” kelimesinin ${r.kok.yol === "çekim" ? "sözlük biçimi" : "kökü"} <a href="${bag(r.kok.madde)}"><b>${kacis(r.kok.madde)}</b></a> olarak bulundu.</div>` : ""}
          <div id="sonucListe">${r.sonuclar.length ? r.sonuclar.map(kart).join("") + dahaTus(r)
            : `<p class="bos">Bu aramaya uygun madde bulunamadı.${navigator.onLine ? "" : " İnternete bağlandığınızda ek kaynaklar da taranacak (Faz 3)."}</p>`}</div>
        </section>
      </div>`;

    $("#suzgec").addEventListener("change", () => {
      const yeni = {};
      for (const ad of ["donem", "koken", "tur", "dil", "kaynak"]) yeni[ad] = [...document.querySelectorAll(`#suzgec input[name="${ad}"]:checked`)].map(i => i.value);
      sonucSayfasi(sorgu, yeni).catch(hata);
    });
    aramaDurum = { sorgu, sec };
  }
  let aramaDurum = null;
  icerik.addEventListener("click", e => {
    if (e.target.id !== "dahaTus" || !aramaDurum) return;
    e.target.disabled = true;
    sonucSayfasi(aramaDurum.sorgu, aramaDurum.sec, +e.target.dataset.sayfa, true).catch(hata);
  });
  const dahaTus = r => r.sayfa * r.boyut < r.toplam
    ? `<button class="tus daha-tus" id="dahaTus" data-sayfa="${r.sayfa + 1}">Daha fazla sonuç (${sayi(r.toplam - r.sayfa * r.boyut)} kaldı)</button>` : "";

  // ---------- Madde sayfası ----------
  function atif(baslik, k, o) {
    const tarih = new Date().toLocaleDateString("tr-TR");
    if (o && (o.yuzyil || o.yazar_id)) return `${o.yazar}, ${o.eser} (${o.yuzyil}); “${baslik}”, Bengü: Türkçenin Ebedî Sözlüğü, (Erişim ${tarih}).`;
    if (k.kaynak_id === "bengu") return `“${baslik}”, Bengü: Türkçenin Ebedî Sözlüğü, (Erişim ${tarih}).`;
    return `“${baslik}”, ${k.kaynak_ad} (${k.kaynak_lisans}), ${k.kaynak_url}, Bengü üzerinden, (Erişim ${tarih}).`;
  }

  async function maddeSayfasi(baslik) {
    yukleniyor();
    const m = await api("madde", { b: baslik });
    if (!m) { icerik.innerHTML = `<p class="bos" style="text-align:center">“${kacis(baslik)}” maddesi bulunamadı. <a href="#/ara/${encodeURIComponent(baslik)}">Bu kelimeyi arayın</a>.</p>`; return; }
    const asil = m.kayitlar.filter(k => k.tur !== "özel ad");
    const ozel = m.kayitlar.filter(k => k.tur === "özel ad");
    const ilk = asil[0] || m.kayitlar[0];
    const osm = [...new Set(m.kayitlar.map(k => k.osmanli).filter(Boolean))];
    const eski = [...new Set(m.kayitlar.map(k => k.eski_yazi).filter(Boolean))];
    const cev = [...new Set(m.kayitlar.map(k => k.ceviri).filter(Boolean))];
    const kayitli = defter().includes(m.baslik);
    const tumOrnekler = [];

    const kayitHTML = (k, ki) => {
      const ilgiliGrup = {};
      k.ilgili.forEach(i => (ilgiliGrup[i.tip] ||= []).push(i));
      return `
      <section class="kayit">
        <div class="kayit-ust">
          <span class="kayit-kaynak" title="${kacis(k.kaynak_lisans)}">${kacis(k.kaynak_ad)}</span>
          <span>${rozetTur(k.tur)}${rozetDil(k.dil)}${rozetKoken(k.koken)}${rozetDonem(k.donem)}</span>
        </div>
        ${k.koken_ayrinti ? `<p class="koken-ayr">Köken: ${kacis(k.koken_ayrinti)}</p>` : ""}
        ${k.aciklama_dili === "en" ? `<p class="koken-ayr">Bu kaynaktaki açıklamalar İngilizcedir; Türkçeleştirme sonraki fazda yapılacak.</p>` : ""}
        <ol class="anlamlar">${k.anlamlar.map(a => `<li>${a.etiket && a.etiket !== "İngilizce açıklama" ? `<span class="anlam-etiket">${kacis(a.etiket)}</span> ` : ""}${kacis(a.metin)}
          ${k.ornekler.filter(o => o.anlam_sira === a.sira).map(o => { tumOrnekler.push([k, o]); const i = tumOrnekler.length - 1; return `
            <div class="tanik">
              <div class="beyit">${beyitHTML(o.metin)}</div>
              ${o.aciklama ? `<div class="aciklama">${kacis(o.aciklama)}</div>` : ""}
              <div class="kaynak-kunye"><span>${kunye(o)} ${o.kaynak_turu ? `<span class="rozet donem">${kacis(o.kaynak_turu)}</span>` : ""}</span>
                <button class="tus kucuk" data-atif="${i}">Atıf</button></div>
            </div>`; }).join("")}
        </li>`).join("")}</ol>
        ${Object.entries(ilgiliGrup).map(([tip, l]) => `<div class="ilgili"><b>${kacis(tip[0].toLocaleUpperCase("tr") + tip.slice(1))}:</b> ${l.map(i => i.var ? `<a href="${bag(i.baslik)}">${kacis(i.baslik)}</a>` : `<span>${kacis(i.baslik)}</span>`).join(", ")}</div>`).join("")}
      </section>`;
    };

    icerik.innerHTML = `
      <article class="kart suslu" style="padding:30px 36px">
        <div class="madde-ust">
          <div>
            <h1>${kacis(m.baslik)}</h1>
            <div style="margin-top:8px">${rozetTur(ilk.tur)}${rozetKoken(ilk.koken)}</div>
          </div>
          <div class="madde-eylemler">
            <button class="tus ${kayitli ? "dolu" : ""}" id="defterTus">${kayitli ? "★ Defterimde" : "☆ Defterime ekle"}</button>
            <button class="tus" id="atifTus">Atıf kopyala (İSNAD)</button>
          </div>
        </div>
        <div class="madde-yazilis">
          ${osm.map(o => `<span class="arap" title="Arap harfli yazılışı">${kacis(o)}</span>`).join("")}
          ${eski.map(o => `<span class="gokturk" title="Göktürk harfleriyle">${kacis(o)}</span>`).join("")}
          ${cev.filter(c => c !== m.baslik).map(c => `<span class="ceviri" title="Çeviri yazı">${kacis(c)}</span>`).join("")}
        </div>
        ${asil.map(kayitHTML).join("")}
        <section class="kayit tanik-bolum" id="tanikBolum">
          <div class="kayit-ust"><span class="kayit-kaynak">Edebî Metinlerde</span><span class="tanik-say" id="tanikSay"></span></div>
          <div id="tanikIcerik"><p class="bos">Tanıklar aranıyor…</p></div>
        </section>
        ${ozel.length ? `<details class="ozel-ad"><summary>Özel ad olarak kullanımı (${ozel.length})</summary>${ozel.map(kayitHTML).join("")}</details>` : ""}
        <p class="lisans-notu">Kaynaklar: ${[...new Set(m.kayitlar.map(k => `${k.kaynak_ad} (${k.kaynak_lisans})`))].map(kacis).join(" · ")}</p>
      </article>`;

    const kopyala = metin => {
      (navigator.clipboard?.writeText(metin) ?? Promise.reject()).then(
        () => bildir("Atıf panoya kopyalandı."),
        () => { window.prompt("Atıf metni:", metin); });
    };
    const ilkTanik = tumOrnekler.find(([, o]) => o.yuzyil);
    $("#atifTus").onclick = () => kopyala(atif(m.baslik, ilkTanik?.[0] || ilk, ilkTanik?.[1]));
    icerik.querySelectorAll("[data-atif]").forEach(t => t.onclick = () => { const [k, o] = tumOrnekler[+t.dataset.atif]; kopyala(atif(m.baslik, k, o)); });
    $("#defterTus").onclick = () => {
      let d = defter();
      d = d.includes(m.baslik) ? d.filter(x => x !== m.baslik) : [...d, m.baslik];
      depo.koy("bengu-defter2", d);
      bildir(d.includes(m.baslik) ? "Defterinize eklendi." : "Defterinizden çıkarıldı.");
      maddeSayfasi(baslik);
    };
    tanikYukle(m.baslik).catch(e => { $("#tanikIcerik").innerHTML = `<p class="bos">${kacis(e.message)}</p>`; });
  }

  // ---------- Edebî metinlerde tanıklar (Vikikaynak derlemi) ----------
  function vurgula(metin, vurgu) {
    if (!vurgu?.length) return kacis(metin);
    let out = "", i = 0;
    for (const [a, b] of vurgu) { out += kacis(metin.slice(i, a)) + `<mark>${kacis(metin.slice(a, b))}</mark>`; i = b; }
    return out + kacis(metin.slice(i));
  }

  async function tanikYukle(baslik, sec = { yazar: "", donem: "" }, sayfa = 1, ekle = false) {
    const kutu = $("#tanikIcerik");
    if (!kutu) return;
    const r = await api("tanik", { b: baslik, yazar: sec.yazar, donem: sec.donem, sayfa });
    if (!r.genel_toplam) {
      kutu.innerHTML = `<p class="bos">Bu kelime derlemdeki edebî metinlerde geçmiyor (ya da yalnız çekimli, tanınmayan bir biçimde geçiyor).</p>`;
      $("#tanikSay").textContent = "";
      return;
    }
    $("#tanikSay").textContent = `${sayi(r.genel_toplam)} satır · ${r.yazarlar.length} yazar`;
    const satirHTML = s => `
      <div class="tanik derlem">
        <div class="beyit">
          ${s.once ? `<span class="misra ${s.once_vurgu?.length ? "" : "soluk"}">${vurgula(s.once, s.once_vurgu)}</span>` : ""}
          <span class="misra">${vurgula(s.metin, s.vurgu)}</span>
          ${s.sonra ? `<span class="misra ${s.sonra_vurgu?.length ? "" : "soluk"}">${vurgula(s.sonra, s.sonra_vurgu)}</span>` : ""}
        </div>
        ${s.ceviri ? `<div class="aciklama">Türkiye Türkçesi: ${kacis(s.ceviri)}</div>` : ""}
        <div class="kaynak-kunye"><span>${yazarBag(s.yazar, s.yazar_id)}, <i>${kacis(s.eser)}</i> <span class="rozet donem">${kacis(DONEMLER[s.donem]?.ad || "")}</span></span>
          <span>${!s.ceviri ? `<a class="tus kucuk" href="${cozumleBag([s.once, s.metin, s.sonra].filter(Boolean).join(" / "))}">Çözümle</a>` : ""}
          <a class="tus kucuk" href="${kacis(s.url)}" target="_blank" rel="noopener" title="Vikikaynak'ta aç (internet gerekir)">Vikikaynak ↗</a></span></div>
      </div>`;
    const daha = r.sayfa * r.boyut < r.toplam ? `<button class="tus daha-tus" id="tanikDaha">Daha fazla tanık (${sayi(r.toplam - r.sayfa * r.boyut)})</button>` : "";
    if (ekle) {
      $("#tanikDaha")?.remove();
      $("#tanikListe").insertAdjacentHTML("beforeend", r.satirlar.map(satirHTML).join("") + daha);
    } else {
      const cip = (tip, deger, etiket, sayi_) => `<button class="tanik-cip ${sec[tip] === deger ? "aktif" : ""}" data-tip="${tip}" data-deger="${kacis(deger)}">${kacis(etiket)}${sayi_ != null ? ` <small>${sayi_}</small>` : ""}</button>`;
      kutu.innerHTML = `
        <div class="tanik-suzgec">
          <span>Dönem:</span>${cip("donem", "", "Tümü")}${Object.entries(r.donemler).sort((a, b) => Object.keys(DONEMLER).indexOf(a[0]) - Object.keys(DONEMLER).indexOf(b[0])).map(([d, n]) => cip("donem", d, DONEMLER[d]?.ad || d, n)).join("")}
        </div>
        <div class="tanik-suzgec">
          <span>Yazar:</span>${cip("yazar", "", "Tümü")}${r.yazarlar.map(y => cip("yazar", y.id, y.ad, y.sayi)).join("")}
        </div>
        <div id="tanikListe">${r.satirlar.map(satirHTML).join("") + daha}</div>`;
      kutu.querySelectorAll(".tanik-cip").forEach(b => b.onclick = () => {
        const yeni = { ...sec, [b.dataset.tip]: b.dataset.deger };
        tanikYukle(baslik, yeni).catch(hata);
      });
    }
    const d = $("#tanikDaha");
    if (d) d.onclick = () => { d.disabled = true; tanikYukle(baslik, sec, sayfa + 1, true).catch(hata); };
  }

  // Ham metni kelimelere bölüp her kelimeyi sözlük bağlantısı yapar (kaçışlama parça parça yapılır)
  function kelimeBagla(metin) {
    return String(metin).split(/([A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîûñŋ]{3,})/).map((p, i) =>
      i % 2 ? `<a class="okuma-kelime" href="#/ara/${encodeURIComponent(p)}">${kacis(p)}</a>` : kacis(p)).join("");
  }

  // ---------- Eser okuma görünümü ----------
  async function metinSayfasi(id) {
    yukleniyor();
    const m = await api("metin", { id });
    if (!m) { icerik.innerHTML = `<p class="bos">Metin bulunamadı.</p>`; return; }
    const kitalar = [];
    m.satirlar.forEach(s => { (kitalar[s.kita] ||= []).push(s); });
    icerik.innerHTML = `
      <p style="margin:0 0 12px"><a href="#/yazar/${kacis(m.yazar_id)}">← ${kacis(m.yazar || "Yazar")}</a></p>
      <article class="kart suslu okuma">
        <div class="etiket">${kacis(DONEMLER[m.donem]?.ad || "")} · ${kacis(GELENEKLER[m.gelenek] || m.gelenek || "")}</div>
        <h1>${kacis(m.sayfa.split("/").pop())}</h1>
        <div class="yazar-yasam" style="font-size:18px">${kacis(m.yazar || "")}${m.eser && m.eser !== m.sayfa ? ` · <i>${kacis(m.eser)}</i>` : ""}</div>
        <div class="okuma-metin">${kitalar.filter(Boolean).map(k => `<div class="kita">${k.map(s => `
          <div class="okuma-satir">${s.eski_yazi ? `<div class="gokturk">${kacis(s.eski_yazi)}</div>` : ""}
            <span>${kelimeBagla(s.metin)}</span>${!s.ceviri ? ` <a class="okuma-coz" href="${cozumleBag(s.metin)}" title="Bu satırı çözümle">✦</a>` : ""}
            ${s.ceviri ? `<div class="aciklama">${kacis(s.ceviri)}</div>` : ""}</div>`).join("")}</div>`).join("")}</div>
        <p class="lisans-notu">Kaynak: Türkçe Vikikaynak (kamu malı / CC BY-SA) · <a href="${kacis(m.url)}" target="_blank" rel="noopener">Vikikaynak'ta aç ↗</a>
          · Kelimelere tıklayarak sözlükte açabilirsiniz.</p>
      </article>`;
  }

  // ---------- Dönem / liste sayfaları ----------
  async function donemSayfasi(donem, tur = "", sayfa = 1) {
    yukleniyor();
    const r = await api("donem", { d: donem, tur, sayfa });
    const d = DONEMLER[donem];
    const toplamSayfa = Math.ceil(r.toplam / r.boyut);
    icerik.innerHTML = `
      <h2 class="bolum-baslik">${kacis(d.ad)}</h2>
      <p style="text-align:center;color:var(--murekkep-soluk);font-style:italic">${kacis(d.aralik)} · ${sayi(r.toplam)} kayıt
        <br><small>Dönem bilgisi kökene göre otomatik atanmıştır; uzman denetimiyle düzeltilecektir.</small></p>
      <div class="tur-secici">${["", ...TURLER.filter(t => t !== "özel ad")].map(t => `<a class="${t === tur ? "aktif" : ""}" href="#/donem/${donem}/${encodeURIComponent(t)}">${t ? kacis(t) : "Tümü"}</a>`).join("")}</div>
      <div class="liste-izgara">${r.kayitlar.map(k => `
        <a class="sonuc kart" href="${bag(k.baslik)}">
          <h3>${kacis(k.baslik)} ${k.osmanli ? `<span class="arap">${kacis(k.osmanli)}</span>` : ""}${k.eski_yazi ? `<span class="gokturk">${kacis(k.eski_yazi)}</span>` : ""}
            <span>${rozetTur(k.tur)}${rozetKoken(k.koken)}</span></h3>
          <p>${kacis(k.anlam)}</p></a>`).join("")}</div>
      <div class="sayfalama">
        ${sayfa > 1 ? `<button class="tus" data-git="${sayfa - 1}">← Önceki</button>` : ""}
        <span>Sayfa ${sayfa} / ${sayi(toplamSayfa)}</span>
        ${sayfa < toplamSayfa ? `<button class="tus" data-git="${sayfa + 1}">Sonraki →</button>` : ""}
      </div>`;
    icerik.querySelectorAll("[data-git]").forEach(b => b.onclick = () => donemSayfasi(donem, tur, +b.dataset.git).then(() => window.scrollTo(0, 0)).catch(hata));
  }

  function basitListe(baslik, aciklama, basliklar) {
    icerik.innerHTML = `
      <h2 class="bolum-baslik">${kacis(baslik)}</h2>
      ${aciklama ? `<p style="text-align:center;color:var(--murekkep-soluk);font-style:italic">${kacis(aciklama)}</p>` : ""}
      ${basliklar.length ? `<div class="liste-izgara">${basliklar.map(b => `<a class="sonuc kart" href="${bag(b)}"><h3>${kacis(b)}</h3></a>`).join("")}</div>`
        : `<p class="bos" style="text-align:center">Henüz bir şey yok. Madde sayfalarındaki “Defterime ekle” düğmesini kullanın.</p>`}`;
  }

  async function donemlerSayfasi() {
    yukleniyor();
    const ist = await api("istatistik");
    icerik.innerHTML = `<h2 class="bolum-baslik">Türk Edebiyatının Dönemleri</h2>
      <div class="izgara">${Object.entries(DONEMLER).map(([k, d]) => `
        <a class="kart suslu k-6" style="text-decoration:none;color:inherit" href="#/donem/${k}">
          <div class="etiket">${d.aralik}</div><h3 style="color:var(--bordo)">${d.ad}</h3>
          <p>${sayi(ist.donem[k] || 0)} kayıt</p></a>`).join("")}</div>`;
  }

  async function sanatlarSayfasi() {
    yukleniyor();
    const r = await api("ara", { q: "sanat", tur: "sanat" });
    const r2 = await api("donem", { d: "islami", tur: "sanat" });
    const basliklar = [...new Set([...r.sonuclar.map(g => g.baslik), ...r2.kayitlar.map(k => k.baslik)])];
    basitListe("Edebî Sanatlar", "Söz ve anlam sanatları — derleme sürüyor", basliklar);
  }

  async function kaynaklarSayfasi() {
    yukleniyor();
    const [ks, ys] = await Promise.all([api("kaynaklar"), api("yazarlar")]);
    icerik.innerHTML = `<h2 class="bolum-baslik">Sözlük Kaynakları</h2>
      <div class="izgara">${ks.map(k => `
        <div class="kart k-6"><div class="etiket">${kacis(k.lisans)}</div>
          <h3>${kacis(k.ad)}</h3><p>${kacis(k.aciklama)}</p>
          <p class="sonuc-alt">${k.eser_sayisi ? `${sayi(k.eser_sayisi)} eser, ${sayi(k.satir_sayisi)} satır` : `${sayi(k.kayit_sayisi)} kayıt`}${k.url ? ` · ${kacis(k.url)}` : ""}</p></div>`).join("")}</div>
      <div class="kart" style="margin-top:20px"><div class="etiket">Henüz eklenmeyen kaynaklar</div>
        <p style="font-size:16px">Kāmûs-ı Türkî (1901) ve Redhouse sözlükleri (1880, 1890) kamu malıdır ve taramaları Internet Archive'da bulunur; ancak mevcut makine okumaları akademik kullanıma yetecek doğrulukta değildir. Osmanlıca'ya özel bir okuma modeliyle yeniden işlenmeleri planlanmaktadır.</p></div>
      <h2 class="bolum-baslik">Tanık Eserler</h2>
      <div class="izgara">${ys.flatMap(y => y.eserler.map(e => ({ y, e }))).map(({ y, e }) => `
        <div class="kart k-6"><div class="etiket">${kacis(e.tur)} · ${kacis(e.tarih)}</div>
          <h3><i>${kacis(e.ad)}</i></h3><p style="margin:0"><a href="#/yazar/${y.id}">${kacis(y.gorunen || y.ad)}</a></p>
          ${e.notu ? `<p style="font-size:16px">${kacis(e.notu)}</p>` : ""}</div>`).join("")}</div>`;
  }

  // ---------- Yazarlar ----------
  let yazarOnbellek = null;
  async function yazarlarSayfasi(sec = { donem: [], gelenek: [], tur: [] }, metin = "") {
    if (!yazarOnbellek) { yukleniyor(); yazarOnbellek = await api("yazarlar"); }
    const nrm = s => String(s).toLocaleLowerCase("tr").normalize("NFD").replace(/[̀-ͯ]/g, "");
    const q = nrm(metin);
    const liste = yazarOnbellek.filter(y =>
      (!sec.donem.length || sec.donem.includes(y.donem)) &&
      (!sec.gelenek.length || sec.gelenek.includes(y.gelenek)) &&
      (!sec.tur.length || y.tur.some(t => sec.tur.includes(t))) &&
      (!q || nrm(y.ad + " " + y.biyografi + " " + y.eserler.map(e => e.ad).join(" ")).includes(q)));
    const kutu = (ad, deger, etiket) => `<label><input type="checkbox" name="${ad}" value="${deger}" ${sec[ad].includes(deger) ? "checked" : ""}> ${etiket}</label>`;
    const turler = { "şair": "Şair", "nesir": "Nesir yazarı", "yazıt": "Yazıt", "sözlükçü": "Sözlükçü / dil bilgini" };
    const sira = Object.keys(DONEMLER);
    const sirali = [...liste].sort((a, b) => sira.indexOf(a.donem) - sira.indexOf(b.donem));

    icerik.innerHTML = `
      <h2 class="bolum-baslik">Yazarlar ve Eserleri</h2>
      <div class="sonuc-duzen">
        <aside class="suzgec kart" id="ySuzgec">
          <input type="search" id="yAra" class="kucuk-ara" placeholder="Yazar ya da eser ara…" value="${kacis(metin)}">
          <h4>Dönem</h4>${Object.entries(DONEMLER).filter(([k]) => k !== "gunumuz").map(([k, d]) => kutu("donem", k, d.ad)).join("")}
          <h4>Gelenek</h4>${Object.entries(GELENEKLER).map(([k, d]) => kutu("gelenek", k, d)).join("")}
          <h4>Yazar türü</h4>${Object.entries(turler).map(([k, d]) => kutu("tur", k, d)).join("")}
        </aside>
        <section>
          <p class="sonuc-bilgi">${sirali.length} yazar</p>
          <div class="yazar-izgara">
          ${sirali.length ? sirali.map(y => `
            <a class="kart yazar-kart" href="#/yazar/${y.id}">
              <div class="yazar-harf" aria-hidden="true">${kacis((y.gorunen || y.ad)[0])}</div>
              <div>
                <h3>${kacis(y.gorunen || y.ad)}</h3>
                <div class="yazar-yasam">${kacis(y.yasam)} · ${DONEMLER[y.donem].ad}</div>
                <p>${kacis(y.biyografi.split(". ")[0])}.</p>
                <div class="yazar-eserler">${y.eserler.slice(0, 3).map(e => `<i>${kacis(e.ad)}</i>`).join(" · ")}</div>
                ${y.metin_sayisi ? `<div class="yazar-eserler" style="margin-top:4px">📜 ${sayi(y.metin_sayisi)} metin, ${sayi(y.satir_sayisi)} satır</div>` : ""}
              </div>
            </a>`).join("") : `<p class="bos">Bu süzgeçlere uyan yazar yok.</p>`}
          </div>
        </section>
      </div>`;

    const oku = () => {
      const s = {};
      for (const ad of ["donem", "gelenek", "tur"]) s[ad] = [...document.querySelectorAll(`#ySuzgec input[name="${ad}"]:checked`)].map(i => i.value);
      return s;
    };
    $("#ySuzgec").addEventListener("change", e => { if (e.target.type === "checkbox") yazarlarSayfasi(oku(), $("#yAra").value); });
    const yAra = $("#yAra");
    yAra.addEventListener("input", () => {
      clearTimeout(yAra.t);
      yAra.t = setTimeout(() => { const p = yAra.value; yazarlarSayfasi(oku(), p).then(() => { const k = $("#yAra"); k.focus(); k.setSelectionRange(p.length, p.length); }); }, 250);
    });
  }

  async function yazarSayfasi(id) {
    yukleniyor();
    const y = await api("yazar", { id });
    if (!y) { icerik.innerHTML = `<p class="bos">Yazar bulunamadı.</p>`; return; }
    if (!yazarOnbellek) yazarOnbellek = await api("yazarlar");
    const ayniDonem = yazarOnbellek.filter(x => x.donem === y.donem && x.id !== y.id);
    icerik.innerHTML = `
      <p style="margin:0 0 12px"><a href="#/yazarlar">← Tüm yazarlar</a></p>
      <div class="izgara">
        <article class="kart suslu k-8" style="padding:30px 36px">
          <div class="etiket">${DONEMLER[y.donem].ad} · ${kacis(GELENEKLER[y.gelenek])}</div>
          <h1 style="margin:4px 0 0;font-size:46px;line-height:1.1">${kacis(y.gorunen || y.ad)}</h1>
          <div class="yazar-yasam" style="font-size:18px">${kacis(y.yasam)}</div>
          <div class="madde-bolum"><h3>Hayatı</h3><p>${kacis(y.biyografi)}</p></div>
          <div class="madde-bolum"><h3>Önemli Eserleri</h3>
            ${y.eserler.map(e => `
              <div class="eser">
                <div class="eser-ust"><b><i>${kacis(e.ad)}</i></b><span class="rozet donem">${kacis(e.tur)}</span><span class="eser-tarih">${kacis(e.tarih)}</span></div>
                ${e.notu ? `<p>${kacis(e.notu)}</p>` : ""}
              </div>`).join("")}
          </div>
          <div class="madde-bolum"><h3>Sözlükteki Tanıkları</h3>
            ${y.taniklar.length ? y.taniklar.map(t => `
              <div class="tanik">
                <div class="beyit">${beyitHTML(t.metin)}</div>
                <div class="kaynak-kunye"><span><i>${kacis(t.eser)}</i></span>
                  <a href="${bag(t.baslik)}">madde: ${kacis(t.baslik)} →</a></div>
              </div>`).join("") : `<p class="bos">Bu yazardan henüz elle hazırlanmış tanık yok.</p>`}
          </div>
          ${y.metinler?.length ? `<div class="madde-bolum"><h3>Vikikaynak'taki Metinleri (${y.metinler.length} metin, ${sayi(y.satir_sayisi)} satır)</h3>
            <div class="metin-liste">${y.metinler.map(t => `
              <a class="metin-kart" href="#/metin/${t.id}">
                <b>${kacis(t.sayfa.split("/").pop())}</b>
                <span class="metin-ilk">${t.ilk.map(kacis).join(" / ")}</span>
                <small>${sayi(t.satir)} satır</small>
              </a>`).join("")}</div></div>` : ""}
        </article>
        <aside class="k-4">
          <div class="kart">
            <div class="etiket">Aynı dönemden</div>
            <ul class="liste-noktali" style="margin-top:8px">${ayniDonem.map(x => `<li><a href="#/yazar/${x.id}">${kacis(x.gorunen || x.ad)}</a> <span class="yazar-yasam">${kacis(x.yasam)}</span></li>`).join("")}</ul>
          </div>
        </aside>
      </div>`;
  }

  // ---------- Osmanlıca ⇄ Türkçe çeviri ----------
  const OSM_HARFLER = ["ا", "ب", "پ", "ت", "ث", "ج", "چ", "ح", "خ", "د", "ذ", "ر", "ز", "ژ", "س", "ش", "ص", "ض", "ط", "ظ",
    "ع", "غ", "ف", "ق", "ک", "گ", "ڭ", "ل", "م", "ن", "و", "ه", "ی", "ء", "آ", "ة", "ئ", "ؤ", "لا"];
  const ORNEKLER = { "tr-ota": ["özlem", "savaş", "gizli", "düşünce", "güzel", "ölüm", "sevgi", "gizli bir sevgi"],
                     "ota-tr": ["nihan", "حسرت", "mektûm", "cenk", "merg", "نبرد", "vedâd"] };
  const GUVEN_SINIF = { "tam karşılık": "tam", "eş anlamlı": "es", "yakın anlam": "yakin" };
  const guvenRozet = g => `<span class="guven ${GUVEN_SINIF[g]}">${kacis(g)}</span>`;

  function ceviriSayfasi(yon = "tr-ota", metin = "") {
    if (yon !== "ota-tr") yon = "tr-ota";
    const kaynakDil = yon === "tr-ota" ? "Günümüz Türkçesi" : "Osmanlıca";
    const hedefDil = yon === "tr-ota" ? "Osmanlıca" : "Günümüz Türkçesi";
    icerik.innerHTML = `
      <h2 class="bolum-baslik">Osmanlıca ⇄ Türkçe Karşılıklar</h2>
      <section class="kart suslu ceviri-kutu">
        <div class="ceviri-yon">
          <span class="dil-ad">${kaynakDil}</span>
          <button class="tus degis" id="yonDegis" title="Yönü değiştir">⇄</button>
          <span class="dil-ad">${hedefDil}</span>
        </div>
        <form id="ceviriForm" class="ceviri-form" autocomplete="off">
          <input id="ceviriKutu" dir="auto" value="${kacis(metin)}" placeholder="${yon === "tr-ota" ? "Bir kelime ya da kısa bir söz yazın… (ör. özlem)" : "Latin ya da Arap harfiyle yazın… (ör. nihan, حسرت)"}">
          <button type="button" class="tus" id="osmKlavyeTus" title="Osmanlıca klavye">ع ب</button>
          <button type="submit" class="ara-tus ceviri-tus">Karşılık bul</button>
        </form>
        <div class="osm-klavye" id="osmKlavye" ${yon === "ota-tr" ? "" : "hidden"}>
          ${OSM_HARFLER.map(h => `<button type="button" data-h="${h}">${h}</button>`).join("")}
          <button type="button" data-h=" " class="genis">boşluk</button><button type="button" data-sil="1" class="genis">⌫ sil</button>
        </div>
        <div class="ornek-kelimeler">Örnekler: ${ORNEKLER[yon].map(o => `<a href="#/ceviri/${yon}/${encodeURIComponent(o)}">${kacis(o)}</a>`).join("")}</div>
        <p class="yontem-notu">Öneriler yapay zekâ ile üretilmez. Sözlük kayıtlarındaki belgelenmiş ilişkilerden çıkarılır:
          ${guvenRozet("tam karşılık")} kelime, Osmanlıca kaydın tanımında doğrudan geçiyor ·
          ${guvenRozet("eş anlamlı")} eş anlamlı bağlantısı var ·
          ${guvenRozet("yakın anlam")} İngilizce karşılıklar üzerinden bulundu, anlam farkı olabilir.</p>
      </section>
      <div id="ceviriSonuc"></div>`;

    const kutu = $("#ceviriKutu");
    $("#yonDegis").onclick = () => { location.hash = `#/ceviri/${yon === "tr-ota" ? "ota-tr" : "tr-ota"}/${encodeURIComponent(kutu.value.trim())}`; };
    $("#ceviriForm").onsubmit = e => { e.preventDefault(); const v = kutu.value.trim(); if (v) location.hash = `#/ceviri/${yon}/${encodeURIComponent(v)}`; };
    $("#osmKlavyeTus").onclick = () => { $("#osmKlavye").hidden = !$("#osmKlavye").hidden; };
    $("#osmKlavye").onclick = e => {
      const b = e.target.closest("button"); if (!b) return;
      const p = kutu.selectionStart ?? kutu.value.length, s = kutu.selectionEnd ?? p;
      if (b.dataset.sil) { const a = s > p ? p : Math.max(0, p - 1); kutu.value = kutu.value.slice(0, a) + kutu.value.slice(s); kutu.setSelectionRange(a, a); }
      else { kutu.value = kutu.value.slice(0, p) + b.dataset.h + kutu.value.slice(s); kutu.setSelectionRange(p + b.dataset.h.length, p + b.dataset.h.length); }
      kutu.focus();
    };
    if (metin) return ceviriSonuc(yon, metin);
    kutu.focus();
  }

  const kopyalaMetin = metin => (navigator.clipboard?.writeText(metin) ?? Promise.reject()).then(
    () => bildir("Panoya kopyalandı: " + metin), () => window.prompt("Kopyalayın:", metin));

  function osmKart(o) {
    const ad = o.basliklar.join(" / ");
    return `<article class="kart osm-kart">
      <div class="osm-yazi">${o.osmanli ? kacis(o.osmanli) : `<span class="yok">—</span>`}</div>
      <h3><a href="${bag(o.madde || o.basliklar[0])}">${kacis(ad)}</a></h3>
      <div class="osm-rozetler">${guvenRozet(o.guven)}${rozetKoken(o.koken)}${rozetDil(o.dil)}</div>
      ${o.anlam ? `<p>${kacis(o.anlam)}</p>` : ""}
      ${o.anlam_en && !o.anlam ? `<p>${kacis(o.anlam_en)} <span class="ing">(İng.)</span></p>` : ""}
      <div class="osm-alt"><span>${kacis(o.yollar.join(", "))}</span>
        <button class="tus kucuk" data-kopya="${kacis(o.basliklar[0] + (o.osmanli ? " (" + o.osmanli + ")" : ""))}">Kopyala</button></div>
    </article>`;
  }

  function trOtaHTML(r, baslikGoster = true) {
    if (!r.oneriler.length) return `<p class="bos">“${kacis(r.sorgu)}” için Osmanlıca karşılık bulunamadı. Kelimenin sözlük biçimini (ör. “özlemek” yerine “özlem”) deneyin.</p>`;
    return `${baslikGoster ? `<p class="sonuc-bilgi">“${kacis(r.sorgu)}” için ${r.oneriler.length} Osmanlıca karşılık önerisi</p>` : ""}
      ${r.yol ? `<div class="kok-notu">Aradığınız kelime “<b>${kacis(r.aranan)}</b>” biçimine indirgenerek arandı.</div>` : ""}
      ${r.kendisi ? `<div class="kok-notu">“${kacis(r.kendisi.baslik)}” kelimesinin kendisi de ${r.kendisi.koken ? kacis(KOKENLER[r.kendisi.koken] || r.kendisi.koken) + " kökenlidir ve " : ""}Osmanlıcada <span class="arap" style="font-size:24px">${kacis(r.kendisi.osmanli)}</span> biçiminde yazılır.</div>` : ""}
      <div class="osm-izgara">${r.oneriler.map(osmKart).join("")}</div>`;
  }

  function otaTrHTML(r) {
    if (!r.bulunan.length) return `<p class="bos">“${kacis(r.sorgu)}” Osmanlıca kayıtlarda bulunamadı. Yazımı değiştirmeyi deneyin (ör. â/a, harekesiz Arap harfleri).</p>`;
    const osm = [...new Set(r.bulunan.map(b => b.osmanli).filter(Boolean))];
    return `
      <div class="izgara">
        <article class="kart suslu k-7">
          <div class="etiket">Osmanlıca kelime</div>
          <h2 style="margin:4px 0">${kacis(r.bulunan[0].baslik)} ${osm.map(o => `<span class="arap">${kacis(o)}</span>`).join(" ")}</h2>
          ${r.bulunan.map(b => `
            <div class="kayit" style="margin-top:12px;padding-top:10px">
              <div class="kayit-ust"><span class="kayit-kaynak">${kacis(b.kaynak)}</span><span>${rozetKoken(b.koken)}${rozetDil(b.dil)}</span></div>
              <ol class="anlamlar">${b.anlamlar.map(a => `<li>${kacis(a)}${b.ingilizce ? ` <span class="ing">(İng.)</span>` : ""}</li>`).join("")}</ol>
            </div>`).join("")}
          <a class="devam" href="${bag(r.bulunan[0].baslik)}">Maddenin tamamı →</a>
        </article>
        <article class="kart k-5">
          <div class="etiket">Günümüz Türkçesi karşılıkları</div>
          ${r.karsiliklar.length ? `<ul class="karsilik-liste">${r.karsiliklar.map(k => `
            <li><a href="${bag(k.baslik)}">${kacis(k.baslik)}</a>
              ${k.oz_turkce ? `<span class="rozet T">öz Türkçe</span>` : rozetKoken(k.koken)} ${guvenRozet(k.guven)}</li>`).join("")}</ul>`
            : `<p class="bos">Karşılık ilişkisi kayıtlı değil; anlamlar soldadır.</p>`}
        </article>
      </div>`;
  }

  async function ceviriSonuc(yon, metin) {
    const hedef = $("#ceviriSonuc");
    hedef.innerHTML = `<p class="bos" style="text-align:center">Aranıyor…</p>`;
    const r = await api("ceviri", { q: metin, yon });
    const tekHTML = s => yon === "tr-ota" ? trOtaHTML(s) : otaTrHTML(s);
    if (r.tek) hedef.innerHTML = tekHTML(r.sonuc);
    else {
      hedef.innerHTML = `
        ${r.butun ? `<h3 class="alt-baslik">Bütün olarak: “${kacis(metin)}”</h3>${tekHTML(r.butun)}` : ""}
        <h3 class="alt-baslik">Kelime kelime</h3>
        <div class="kelime-tablo">${r.kelimeler.map(s => `
          <div class="kelime-satir">
            <div class="kelime-ad">${kacis(s.sorgu)}</div>
            <div class="kelime-oneriler">${yon === "tr-ota"
              ? (s.oneriler.length ? s.oneriler.map(o => `<a class="oneri-cip" href="${bag(o.madde || o.basliklar[0])}" title="${kacis(o.anlam || "")}">
                    ${o.osmanli ? `<span class="arap">${kacis(o.osmanli)}</span>` : ""} ${kacis(o.basliklar[0])} ${guvenRozet(o.guven)}</a>`).join("") : `<span class="bos">karşılık yok</span>`)
              : (s.karsiliklar.length ? s.karsiliklar.slice(0, 6).map(k => `<a class="oneri-cip" href="${bag(k.baslik)}">${kacis(k.baslik)} ${guvenRozet(k.guven)}</a>`).join("")
                 : (s.bulunan[0] ? `<span>${kacis(s.bulunan[0].anlamlar[0] || "")}</span>` : `<span class="bos">bulunamadı</span>`))}
            </div>
          </div>`).join("")}</div>`;
    }
    hedef.querySelectorAll("[data-kopya]").forEach(b => b.onclick = () => kopyalaMetin(b.dataset.kopya));
  }

  // ---------- Rehber (doğal dilde soru) ----------
  const REHBER_ORNEK = [
    "kibir anlamına gelen kelimeler", "cömertlik anlamında Arapça kelimeler", "sabırla ilgili atasözleri",
    "savaşın Osmanlıcası", "nihan ne demek", "Divan şiirinde ayrılık temalı beyitler",
    "çözümle: Bir safâ bahşedelim gel şu dil-i nâşâde", "gül ile kafiyeli kelimeler", "-dâr ile biten Farsça kelimeler",
    "aşk ile sevda arasındaki fark", "kitabın kökeni nedir", "Fuzûlî kimdir", "Tanzimat yazarları",
    "Orhun yazıtlarında tengri", "güzel kelimesinin zıt anlamlısı"];
  const SORU_GIBI = /\s\S+\s|anlam|osmanlıca|ilgili|hakkında|konulu|temalı|beyit|dize|ne demek|atasöz|deyim|kelimeler|şiir|kökeni|kafiye|kimdir|fark|çözümle|zıt|eş anlam|yazarları|şairleri/i;
  const cozumleBag = metin => `#/rehber/${encodeURIComponent("çözümle: " + metin)}`;

  function satirKart(s) {
    return `
      <div class="tanik derlem">
        ${s.kelime ? `<div class="tema-kelime">${kacis(s.kelime)}</div>` : ""}
        <div class="beyit">
          ${s.once ? `<span class="misra ${s.once_vurgu?.length ? "" : "soluk"}">${vurgula(s.once, s.once_vurgu)}</span>` : ""}
          <span class="misra">${vurgula(s.metin, s.vurgu)}</span>
          ${s.sonra ? `<span class="misra ${s.sonra_vurgu?.length ? "" : "soluk"}">${vurgula(s.sonra, s.sonra_vurgu)}</span>` : ""}
        </div>
        ${s.ceviri ? `<div class="aciklama">Türkiye Türkçesi: ${kacis(s.ceviri)}</div>` : ""}
        <div class="kaynak-kunye"><span>${yazarBag(s.yazar, s.yazar_id)}, <i>${kacis(s.eser)}</i> <span class="rozet donem">${kacis(DONEMLER[s.donem]?.ad || "")}</span></span>
          <span>${!s.ceviri ? `<a class="tus kucuk" href="${cozumleBag([s.once, s.metin, s.sonra].filter(Boolean).join(" / "))}">Çözümle</a>` : ""}
          ${s.url ? `<a class="tus kucuk" href="${kacis(s.url)}" target="_blank" rel="noopener">Vikikaynak ↗</a>` : ""}</span></div>
      </div>`;
  }

  // Rehber'in yeni bölüm görünümleri
  function cozumlemeHTML(v) {
    return `
      <div class="cozumleme-satir">${v.kelimeler.map(k => `
        <span class="coz-kelime ${k.bulundu ? "" : "yok"} ${k.ek ? "ek" : ""} ${k.kalip ? "kalip" : ""}" title="${kacis(k.anlam || "sözlükte bulunamadı")}">
          ${k.osmanli ? `<small class="arap">${kacis(k.osmanli)}</small>` : ""}${kacis(k.yazilan)}</span>`).join("")}</div>
      <table class="coz-tablo">
        <thead><tr><th>Metinde</th><th>Sözlük biçimi</th><th>Anlamı</th><th>Köken</th></tr></thead>
        <tbody>${v.kelimeler.map(k => `
          <tr class="${k.bulundu ? "" : "yok"} ${k.ek ? "ek" : ""}">
            <td>${kacis(k.yazilan)}</td>
            <td>${k.ek ? `<i>${kacis(k.bicim)}</i>` : k.bulundu ? `<a href="${bag(k.bicim)}">${kacis(k.bicim)}</a>` : `<span class="bos">—</span>`}
              ${k.osmanli ? `<span class="arap" style="font-size:20px">${kacis(k.osmanli)}</span>` : ""}
              ${k.kalip ? `<span class="rozet tur">kalıp</span>` : ""}</td>
            <td>${k.anlam ? kacis(k.anlam) : `<span class="bos">sözlükte bulunamadı</span>`}
              ${k.baska ? `<div class="coz-baska">Başka okuma: <a href="${bag(k.baska.bicim)}">${kacis(k.baska.bicim)}</a> ${kacis(k.baska.ek)}${k.baska.anlam ? " — " + kacis(k.baska.anlam) : ""}</div>` : ""}
              ${k.yol === "eski biçim" ? `<span class="rozet donem">eski biçim</span>` : ""}</td>
            <td>${rozetKoken(k.koken)}</td>
          </tr>`).join("")}</tbody>
      </table>
      <p class="yontem-notu">Her satır sözlükteki bir kaydın ilk tanımıdır; bağlama göre doğru anlam farklı olabilir. Altı çizili “Başka okuma”, ekli okunuşun da mümkün olduğunu gösterir.</p>`;
  }

  function kafiyeHTML(v) {
    if (!v.length) return `<p class="bos">Bu sonla biten kayıt bulunamadı.</p>`;
    return `<div class="kafiye-liste">${v.map(k => `
      <a class="kafiye-cip" href="${bag(k.baslik)}" title="${kacis(k.anlam || "")}">
        ${k.osmanli ? `<span class="arap">${kacis(k.osmanli)}</span>` : ""}<b>${kacis(k.baslik)}</b>
        ${k.siklik ? `<small>${sayi(k.siklik)}</small>` : ""}</a>`).join("")}</div>
      <p class="yontem-notu">Sağdaki sayı, kelimenin tanık derlemindeki şiirlerde kaç satırda geçtiğidir; şiirde sık kullanılanlar önde.</p>`;
  }

  function kokenHTML(v) {
    return `<div class="kart koken-kart">
      <h3><a href="${bag(v.baslik)}">${kacis(v.baslik)}</a> ${v.osmanli ? `<span class="arap">${kacis(v.osmanli)}</span>` : ""} ${rozetKoken(v.koken)}</h3>
      ${v.kaynaklar.length ? `<ul class="liste-noktali">${v.kaynaklar.map(k => `<li><b>${kacis(k.kaynak)}:</b> ${kacis(k.ayrinti || KOKENLER[k.koken] || "")}
        ${rozetDil(k.dil)} ${rozetDonem(k.donem)}</li>`).join("")}</ul>` : `<p class="bos">Kaynaklarda köken bilgisi yok.</p>`}
    </div>`;
  }

  function karsilastirHTML(v) {
    const sutun = x => !x.bulundu ? `<div class="kart"><h3>${kacis(x.baslik)}</h3><p class="bos">Sözlükte bulunamadı.</p></div>` : `
      <div class="kart karsi-sutun">
        <h3><a href="${bag(x.baslik)}">${kacis(x.baslik)}</a> ${x.osmanli ? `<span class="arap">${kacis(x.osmanli)}</span>` : ""}</h3>
        <div>${rozetKoken(x.koken)} ${rozetDonem(x.donem)}</div>
        ${x.koken_ayrinti ? `<p class="koken-ayr">Köken: ${kacis(x.koken_ayrinti)}</p>` : ""}
        <ol class="anlamlar">${x.anlamlar.map(a => `<li>${kacis(a)}</li>`).join("")}</ol>
        <p class="sonuc-alt">Tanık derleminde ${sayi(x.tanik_sayisi)} satırda geçiyor.${x.digerinde ? " Tanımında diğer kelime geçiyor." : ""}</p>
        ${x.tanik_ornek ? satirKart(x.tanik_ornek) : ""}
      </div>`;
    return `<div class="karsi-izgara">${sutun(v.a)}${sutun(v.b)}</div>
      ${v.ortak.length ? `<p class="ilgili"><b>Ortak eş anlamlılar:</b> ${v.ortak.map(o => `<a href="${bag(o)}">${kacis(o)}</a>`).join(", ")}</p>` : ""}`;
  }

  function yazarKartHTML(y) {
    return `<div class="kart suslu">
      <div class="etiket">${kacis(DONEMLER[y.donem]?.ad || "")} · ${kacis(GELENEKLER[y.gelenek] || "")}</div>
      <h3 style="font-size:28px;margin:4px 0"><a href="#/yazar/${kacis(y.id)}">${kacis(y.gorunen || y.ad)}</a> <span class="yazar-yasam">${kacis(y.yasam)}</span></h3>
      <p>${kacis(y.biyografi)}</p>
      ${y.eserler.length ? `<p><b>Önemli eserleri:</b> ${y.eserler.map(e => `<i>${kacis(e.ad)}</i> (${kacis(e.tarih)})`).join(", ")}</p>` : ""}
      ${y.metinler?.length ? `<p class="sonuc-alt">Derlemdeki metinleri: ${y.metinler.slice(0, 8).map(t => `<a href="#/metin/${t.id}">${kacis(t.sayfa.split("/").pop())}</a>`).join(" · ")}</p>` : ""}
      <a class="devam" href="#/yazar/${kacis(y.id)}">Yazar sayfası →</a>
    </div>`;
  }

  function kelimeKart(k) {
    return `<a class="sonuc kart rehber-kelime" href="${bag(k.baslik)}">
      <h3>${kacis(k.baslik)} ${k.osmanli ? `<span class="arap">${kacis(k.osmanli)}</span>` : ""}
        <span>${rozetTur(k.tur)}${rozetKoken(k.koken)}${rozetDil(k.dil)}</span></h3>
      <p>${kacis(k.anlam || "")}${k.ingilizce ? ` <span class="ing">(İng.)</span>` : ""}</p>
      ${k.yol ? `<p class="sonuc-alt">${kacis(k.yol)}</p>` : ""}
    </a>`;
  }

  const NIYET_ADI = { karsilik: "Osmanlıca karşılık arıyorsunuz", anlam: "Bir kelimenin anlamını soruyorsunuz",
    kavram: "Anlamı / konusu verilen kelimeleri arıyorsunuz", tanik: "Edebî metinlerde tanık arıyorsunuz", ara: "Sözlük araması",
    cozumle: "Metni kelime kelime çözümlüyorsunuz", kafiye: "Kafiye / uyak arıyorsunuz", koken: "Kelimenin kökenini soruyorsunuz",
    ilgili: "Eş / zıt anlamlı arıyorsunuz", karsilastir: "İki kelimeyi karşılaştırıyorsunuz", yazar: "Bir yazarı soruyorsunuz",
    yazarlar: "Bir dönemin / geleneğin yazarlarını soruyorsunuz" };
  const gecmis = () => depo.al("bengu-rehber-gecmis", []);

  function rehberSayfasi(soru = "") {
    icerik.innerHTML = `
      <h2 class="bolum-baslik">Rehber ✦</h2>
      <section class="kart suslu rehber-kutu">
        <p class="rehber-giris">Sorunuzu kendi cümlenizle yazın. Rehber ne aradığınızı anlayıp sözlükte ve edebî metinlerde arar.
          <b>Kendisi tanım ya da metin üretmez</b>; gösterdiği her şey kaynağı belli sözlük kaydı ya da beyittir.</p>
        <form id="rehberForm" class="ceviri-form" autocomplete="off">
          <input id="rehberKutu" value="${kacis(soru)}" placeholder="ör. sabırla ilgili atasözleri">
          <button type="submit" class="ara-tus ceviri-tus">Sor</button>
        </form>
        <div class="ornek-kelimeler">Örnekler: ${REHBER_ORNEK.map(o => `<a href="#/rehber/${encodeURIComponent(o)}">${kacis(o)}</a>`).join("")}</div>
        ${gecmis().length ? `<div class="ornek-kelimeler gecmis">Son sorularınız: ${gecmis().map(o => `<a href="#/rehber/${encodeURIComponent(o)}">${kacis(o)}</a>`).join("")}
          <button class="tus kucuk" id="gecmisSil" type="button">temizle</button></div>` : ""}
        <p class="yontem-notu" id="rehberDurum"></p>
      </section>
      <div id="rehberSonuc"></div>`;
    const kutu = $("#rehberKutu");
    $("#rehberForm").onsubmit = e => { e.preventDefault(); const v = kutu.value.trim(); if (v) location.hash = "#/rehber/" + encodeURIComponent(v); };
    $("#gecmisSil")?.addEventListener("click", () => { depo.koy("bengu-rehber-gecmis", []); rehberSayfasi(soru); });
    if (soru) depo.koy("bengu-rehber-gecmis", [soru, ...gecmis().filter(g => g !== soru)].slice(0, 8));
    api("durum").then(d => {
      $("#rehberDurum").innerHTML = d.anlamsal
        ? "✦ Anlamsal arama açık: yapay zekâ modeli (multilingual-e5-small, bilgisayarınızda çalışır) anlamca yakın kayıtları da bulur."
        : "Anlamsal arama kapalı (model yüklü değil). Rehber kural tabanlı çözümleyiciyle çalışıyor.";
    }).catch(() => {});
    if (soru) return rehberSonuc(soru);
    kutu.focus();
  }

  async function rehberSonuc(soru) {
    const hedef = $("#rehberSonuc");
    hedef.innerHTML = `<p class="bos" style="text-align:center">Düşünüyor…</p>`;
    const r = await api("rehber", { q: soru });
    if (r.niyet === "ara" || !r.bolumler.length) {
      hedef.innerHTML = `<div class="kok-notu">Soru tam anlaşılamadı; “${kacis(r.kavram || soru)}” için sözlük araması yapılıyor…</div>`;
      setTimeout(() => { location.hash = "#/ara/" + encodeURIComponent(r.kavram || soru); }, 900);
      return;
    }
    const anlayis = `
      <div class="rehber-anlayis">
        <span class="anlayis-baslik">✦ Anladığım:</span>
        <span class="anlayis-cip niyet">${kacis(NIYET_ADI[r.niyet])}</span>
        ${r.kavram && r.niyet !== "cozumle" ? `<span class="anlayis-cip">Kavram: <b>${kacis(r.kavram)}</b></span>` : ""}
        ${r.anlasilan.map(a => `<span class="anlayis-cip">${kacis(a.etiket)}</span>`).join("")}
        <a class="anlayis-duz" href="#/ara/${encodeURIComponent(r.niyet === "cozumle" ? soru : (r.kavram || soru))}">Yanlış mı anladım? Düz sözlük araması →</a>
      </div>
      ${r.ozet ? `<p class="rehber-ozet">${kacis(r.ozet)}</p>` : ""}`;
    const oneriHTML = r.oneriler?.length ? `<div class="rehber-oneriler"><span>Bunları da sorabilirsiniz:</span>
      ${r.oneriler.map(o => `<a class="tanik-cip" href="#/rehber/${encodeURIComponent(o)}">${kacis(o)}</a>`).join("")}</div>` : "";
    const bolumHTML = b => {
      let govde = "";
      if (b.tip === "karsilik") govde = trOtaHTML(b.veri, false);
      else if (b.tip === "anlam") govde = otaTrHTML(b.veri);
      else if (b.tip === "kelimeler") govde = b.veri.length ? `<div class="liste-izgara">${b.veri.map(kelimeKart).join("")}</div>` : `<p class="bos">Uygun kayıt bulunamadı.</p>`;
      else if (b.tip === "tanik") govde = b.veri.satirlar.map(satirKart).join("");
      else if (b.tip === "tanik_tema" || b.tip === "tanik_anlam") govde = b.veri.map(satirKart).join("");
      else if (b.tip === "cozumleme") govde = cozumlemeHTML(b.veri);
      else if (b.tip === "kafiye") govde = kafiyeHTML(b.veri);
      else if (b.tip === "koken") govde = kokenHTML(b.veri);
      else if (b.tip === "karsilastir") govde = karsilastirHTML(b.veri);
      else if (b.tip === "yazar") govde = yazarKartHTML(b.veri);
      else if (b.tip === "yazarlar") govde = `<div class="yazar-izgara">${b.veri.map(y => `
        <a class="kart yazar-kart" href="#/yazar/${y.id}"><div class="yazar-harf">${kacis((y.gorunen || y.ad)[0])}</div>
          <div><h3>${kacis(y.gorunen || y.ad)}</h3><div class="yazar-yasam">${kacis(y.yasam)}</div>
          <p>${kacis(y.biyografi.split(". ")[0])}.</p></div></a>`).join("")}</div>`;
      const not = b.tip === "tanik_anlam" ? `<p class="yontem-notu">Bu satırlar yapay zekâ modelinin anlam benzerliğine göre sıralandı; eski metinlerde isabet düşebilir.</p>`
        : b.tip === "tanik_tema" ? `<p class="yontem-notu">Kavram ve sözlükteki Osmanlıca eş anlamlıları geçen satırlar.</p>` : "";
      return `<section class="rehber-bolum"><h3 class="alt-baslik">${kacis(b.baslik)}</h3>${not}${govde}</section>`;
    };
    hedef.innerHTML = anlayis + r.bolumler.map(bolumHTML).join("") + oneriHTML;
    hedef.querySelectorAll("[data-kopya]").forEach(b => b.onclick = () => kopyalaMetin(b.dataset.kopya));
  }

  // ---------- Yönlendirme ----------
  function yonlendir() {
    const h = location.hash.slice(1) || "/";
    const [, yol, a1, a2] = h.split("/").map(decodeURIComponent);
    $("#baglantiPanel").hidden = true;
    $("#ozelHarfler").hidden = true;
    document.querySelectorAll(".sekmeler a").forEach(a => a.classList.toggle("aktif",
      a.dataset.sekme === ({ "": "ana", donem: "donemler", madde: "", ara: "", yazar: "yazarlar", metin: "yazarlar" }[yol] ?? yol)));
    let is;
    if (yol === "ara") { $("#aramaKutusu").value = a1 || ""; is = sonucSayfasi(a1 || ""); }
    else if (yol === "madde") is = maddeSayfasi(a1);
    else if (yol === "donem" && DONEMLER[a1]) is = donemSayfasi(a1, a2 || "");
    else if (yol === "ceviri") is = ceviriSayfasi(a1 || "tr-ota", a2 || "");
    else if (yol === "metin") is = metinSayfasi(a1);
    else if (yol === "rehber") is = rehberSayfasi(a1 || "");
    else if (yol === "donemler") is = donemlerSayfasi();
    else if (yol === "yazarlar") is = yazarlarSayfasi();
    else if (yol === "yazar") is = yazarSayfasi(a1);
    else if (yol === "sanatlar") is = sanatlarSayfasi();
    else if (yol === "kaynaklar") is = kaynaklarSayfasi();
    else if (yol === "defterim") basitListe("Defterim", "Kaydettiğiniz maddeler bu bilgisayarda saklanır.", defter());
    else is = anaSayfa();
    is?.catch(hata);
    window.scrollTo(0, 0);
  }
  window.addEventListener("hashchange", yonlendir);

  $("#aramaFormu").addEventListener("submit", e => {
    e.preventDefault();
    const q = $("#aramaKutusu").value.trim();
    // Soru cümlesi gibi görünüyorsa Rehber'e, tek kelime / kalıpsa doğrudan sözlüğe
    if (q) location.hash = (SORU_GIBI.test(q) && q.split(/\s+/).length >= 2 ? "#/rehber/" : "#/ara/") + encodeURIComponent(q);
  });

  // Yazarken öneri (otomatik tamamlama)
  const kutuA = $("#aramaKutusu"), oneriler = $("#oneriler");
  kutuA.addEventListener("input", () => {
    clearTimeout(kutuA.t);
    kutuA.t = setTimeout(async () => {
      const l = await api("oneri", { q: kutuA.value }).catch(() => []);
      oneriler.innerHTML = (l || []).map(b => `<option value="${kacis(b)}">`).join("");
    }, 150);
  });

  // Özel harf klavyesi
  const harfler = ["â", "î", "û", "ā", "ī", "ū", "ḥ", "ḫ", "ḳ", "ṭ", "ṣ", "ẓ", "ż", "ñ", "ŋ", "ʿ"];
  const ozel = $("#ozelHarfler");
  ozel.innerHTML = harfler.map(h => `<button type="button">${h}</button>`).join("");
  $("#osmTus").onclick = () => { ozel.hidden = !ozel.hidden; };
  ozel.addEventListener("click", e => {
    if (e.target.tagName !== "BUTTON") return;
    const p = kutuA.selectionStart ?? kutuA.value.length;
    kutuA.value = kutuA.value.slice(0, p) + e.target.textContent + kutuA.value.slice(kutuA.selectionEnd ?? p);
    kutuA.focus(); kutuA.setSelectionRange(p + 1, p + 1);
  });

  // ---------- Bağlantı durumu (wi-fi) ----------
  const tus = $("#baglantiTus"), panel = $("#baglantiPanel");
  function panelCiz() {
    panel.innerHTML = navigator.onLine ? `
      <h3>Çevrimiçi kaynaklara erişim açık</h3>
      <p>Bilgisayarda yüklü olmayan kaynaklar da taranabilir. Bu kaynaklardan gelen sonuçlar ayrı bir işaretle gösterilecek.</p>
      <ul>${CEVRIMICI_KAYNAKLAR.map(k => `<li><span class="rozet donem">${k.durum}</span><b>${kacis(k.ad)}</b>${kacis(k.aciklama)}</li>`).join("")}</ul>` : `
      <h3>Çevrimdışı çalışıyorsunuz</h3>
      <p>Bengü bilgisayarınızdaki sözlükle tam olarak çalışmaya devam ediyor. İnternete bağlandığınızda ek kaynaklar kendiliğinden açılır.</p>`;
  }
  function durumGuncelle(degisti) {
    const acik = navigator.onLine;
    tus.classList.toggle("cevrimici", acik);
    $("#baglantiYazi").textContent = acik ? "Çevrimiçi" : "Çevrimdışı";
    tus.title = acik ? "Çevrimiçi: ek kaynaklar açık" : "Çevrimdışı: yerel sözlük";
    panelCiz();
    if (degisti) bildir(acik ? "İnternet bağlantısı bulundu: çevrimiçi kaynaklara erişim açık." : "Bağlantı kesildi: yerel sözlükle devam ediliyor.");
  }
  tus.onclick = e => { e.stopPropagation(); panel.hidden = !panel.hidden; };
  document.addEventListener("click", e => {
    if (!panel.hidden && !panel.contains(e.target)) panel.hidden = true;
    if (!ozel.hidden && !ozel.contains(e.target) && e.target.id !== "osmTus") ozel.hidden = true;
  });
  window.addEventListener("online", () => durumGuncelle(true));
  window.addEventListener("offline", () => durumGuncelle(true));

  durumGuncelle(false);
  if (navigator.onLine) setTimeout(() => bildir("Çevrimiçi kaynaklara erişim açık."), 600);

  // Masaüstü uygulaması: pencere açık olduğu sürece sunucuya "buradayım" sinyali (kapanınca sunucu da kapanır)
  const nabiz = () => fetch("/api/nabiz", { cache: "no-store" }).catch(() => {});
  nabiz();
  setInterval(nabiz, 5000);
  api("durum").then(d => {
    const alt = document.querySelector(".alt p");
    if (alt && d?.surum) alt.insertAdjacentHTML("afterbegin", `Sürüm ${kacis(d.surum)} · `);
  }).catch(() => {});

  // Güncelleme denetimi (yalnız internet varken; GitHub'dan yalnız son sürüm numarası sorulur)
  function guncellemeDenetle() {
    if (!navigator.onLine) return;
    api("guncelleme").then(g => {
      if (!g?.yeni_var || depo.al("bengu-gec-surum", "") === g.son) return;
      const s = document.createElement("div");
      s.className = "guncelleme-seridi";
      s.innerHTML = `<span>✦ <b>Bengü ${kacis(g.son)}</b> yayımlandı (kullandığınız: ${kacis(g.mevcut)}).</span>
        <a class="tus dolu" href="${kacis(g.adres)}" target="_blank" rel="noopener">İndir</a>
        <button class="tus" type="button">Sonra</button>`;
      s.querySelector("button").onclick = () => { depo.koy("bengu-gec-surum", g.son); s.remove(); };
      document.querySelector(".ust").insertAdjacentElement("afterend", s);
    }).catch(() => {});
  }
  setTimeout(guncellemeDenetle, 3000);
  window.addEventListener("online", () => setTimeout(guncellemeDenetle, 2000));

  yonlendir();
})();
