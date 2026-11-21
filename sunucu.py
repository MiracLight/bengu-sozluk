"""Bengü — yerel uygulama sunucusu.

Arayüzü (ui/) ve sözlük API'sini yalnızca bu bilgisayara (127.0.0.1) sunar; dışarıya kapalıdır.
Yalnızca Python standart kitaplığını kullanır.  Çalıştırma:  python sunucu.py [port]
"""
import json
import logging
import mimetypes
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cekirdek import anlam, arama, ceviri, rehber
import surum

KOK = Path(__file__).resolve().parent
UI = KOK / "ui"
_yerel = threading.local()
_son_nabiz = [time.time()]  # arayüzün son "buradayım" sinyali (pencere kapanınca sunucuyu kapatmak için)
gunluk = logging.getLogger("bengu")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")


def db():
    if not hasattr(_yerel, "db"):
        _yerel.db = arama.baglan()
    return _yerel.db


def _int(s, v=1):
    try:
        return max(1, int(s))
    except (TypeError, ValueError):
        return v


ROTALAR = {
    "/api/ara": lambda p: arama.ara(db(), p.get("q", ""), p.get("donem", ""), p.get("koken", ""), p.get("tur", ""),
                                    p.get("dil", ""), p.get("kaynak", ""), _int(p.get("sayfa"))),
    "/api/madde": lambda p: arama.madde(db(), p.get("b", "")),
    "/api/gunun": lambda p: arama.gunun_seckisi(db()),
    "/api/oneri": lambda p: arama.oneri(db(), p.get("q", "")),
    "/api/yazarlar": lambda p: arama.yazarlar(db()),
    "/api/yazar": lambda p: arama.yazar(db(), p.get("id", "")),
    "/api/kaynaklar": lambda p: arama.kaynaklar(db()),
    "/api/istatistik": lambda p: arama.istatistik(db()),
    "/api/rehber": lambda p: rehber.sor(db(), p.get("q", "")),
    "/api/durum": lambda p: {"anlamsal": anlam.hazir(), "surum": surum.SURUM, "tarih": surum.SURUM_TARIHI, "uygulama": "bengu"},
    "/api/nabiz": lambda p: (_son_nabiz.__setitem__(0, time.time()), {"tamam": True})[1],
    "/api/tanik": lambda p: arama.tanik(db(), p.get("b", ""), p.get("yazar", ""), p.get("donem", ""), _int(p.get("sayfa"))),
    "/api/metin": lambda p: arama.metin(db(), _int(p.get("id"), 0)),
    "/api/ceviri": lambda p: ceviri.cevir(db(), p.get("q", ""), "ota-tr" if p.get("yon") == "ota-tr" else "tr-ota"),
    "/api/donem": lambda p: arama.donem_listesi(db(), p.get("d", ""), _int(p.get("sayfa")), tur=p.get("tur", "")),
}


class Isleyici(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _gonder(self, kod, govde: bytes, tur):
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(govde)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith("/api/"):
            f = ROTALAR.get(u.path)
            if not f:
                return self._gonder(404, b'{"hata":"yok"}', "application/json")
            p = {k: v[0] for k, v in parse_qs(u.query).items()}
            try:
                veri = f(p)
                kod = 200 if veri is not None else 404
            except Exception as e:  # hatayı arayüze ilet ve günlüğe yaz, sunucu çökmesin
                gunluk.exception("API hatası: %s", self.path)
                veri, kod = {"hata": str(e)}, 500
            return self._gonder(kod, json.dumps(veri, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        yol = (UI / (u.path.lstrip("/") or "index.html")).resolve()
        if not yol.is_relative_to(UI) or not yol.is_file():
            return self._gonder(404, "Bulunamadı".encode(), "text/plain; charset=utf-8")
        tur = mimetypes.guess_type(yol.name)[0] or "application/octet-stream"
        if tur.startswith("text/") or tur.endswith("javascript"):
            tur += "; charset=utf-8"
        self._gonder(200, yol.read_bytes(), tur)

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass  # pencere kapanırken yarım kalan istekler


_guncelleme = {"zaman": 0, "sonuc": None}


def _surum_demeti(s):
    try:
        return tuple(int(x) for x in str(s).lstrip("vV").split(".")[:3])
    except ValueError:
        return (0,)


def guncelleme_denetle(p=None):
    """GitHub'daki en son sürümü sorar (6 saatte bir; internet yoksa sessizce 'bilinmiyor' döner).
    Yalnız sürüm bilgisi istenir; GitHub'a kullanıcıya dair hiçbir veri gönderilmez."""
    if not surum.GITHUB_DEPO:
        return {"durum": "kapali"}
    if _guncelleme["sonuc"] and time.time() - _guncelleme["zaman"] < 6 * 3600:
        return _guncelleme["sonuc"]
    import urllib.request
    try:
        istek = urllib.request.Request(f"https://api.github.com/repos/{surum.GITHUB_DEPO}/releases/latest",
                                       headers={"User-Agent": f"Bengu/{surum.SURUM}", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(istek, timeout=6) as r:
            d = json.loads(r.read())
        son = d.get("tag_name", "")
        sonuc = {"durum": "tamam", "mevcut": surum.SURUM, "son": son.lstrip("vV"),
                 "yeni_var": _surum_demeti(son) > _surum_demeti(surum.SURUM),
                 "adres": d.get("html_url") or f"https://github.com/{surum.GITHUB_DEPO}/releases/latest",
                 "notlar": (d.get("body") or "")[:600]}
    except Exception as e:
        gunluk.info("Güncelleme denetlenemedi: %s", e)
        return {"durum": "bilinmiyor", "mevcut": surum.SURUM}
    _guncelleme.update(zaman=time.time(), sonuc=sonuc)
    return sonuc


ROTALAR["/api/guncelleme"] = guncelleme_denetle


def _isit():
    try:
        anlam.kodla(["ısınma"])
        gunluk.info("Anlamsal model yüklendi")
    except Exception:
        gunluk.exception("Anlamsal model yüklenemedi; Rehber kural tabanlı çalışacak")
        anlam.devre_disi()


def olustur(port=0):
    """Sunucuyu oluşturur (port=0: boş bir bağlantı noktası seçilir). serve_forever() çağıran tarafa kalır."""
    sunucu = ThreadingHTTPServer(("127.0.0.1", port), Isleyici)
    sunucu.daemon_threads = True
    if anlam.hazir():  # modeli arka planda ısıt: ilk Rehber sorusu beklemesin
        threading.Thread(target=_isit, daemon=True).start()
    else:
        gunluk.info("Anlamsal arama kapalı (model ya da vektör dizini yok); Rehber kural tabanlı çalışır.")
    return sunucu


def son_nabiz():
    return _son_nabiz[0]


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5173
    sunucu = olustur(port)
    print(f"Bengü çalışıyor: http://127.0.0.1:{port}", flush=True)
    sunucu.serve_forever()


if __name__ == "__main__":
    main()
