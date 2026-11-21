"""Bengü — masaüstü başlatıcısı (Bengu.exe'nin giriş noktası).

  Bengu.exe              Sunucuyu başlatır ve Bengü'yü kendi penceresinde açar (Edge uygulama kipi;
                         yoksa varsayılan tarayıcı). Pencere kapanınca sunucu da kapanır.
  Bengu.exe --oztest     Veritabanını, aramayı, çeviriyi, tanıkları, Rehber'i ve modeli sınar; rapor yazar.
  Bengu.exe --tarayici   Pencere yerine varsayılan tarayıcıda açar.

Kullanıcıya ait dosyalar: %LOCALAPPDATA%\\Bengu\\ (günlük, pencere profili = defter ve geçmiş, kilit dosyası)
"""
import json
import logging
import logging.handlers
import os
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

KULLANICI = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Bengu"
KILIT = KULLANICI / "calisiyor.json"
NABIZ_ZAMAN_ASIMI = 25          # sn: arayüzden sinyal gelmezse pencere kapanmış sayılır
ILK_NABIZ_BEKLEME = 120          # sn: tarayıcı kipinde sayfanın açılması için tanınan süre


def gunluk_kur():
    KULLANICI.mkdir(parents=True, exist_ok=True)
    g = logging.getLogger("bengu")
    g.setLevel(logging.INFO)
    h = logging.handlers.RotatingFileHandler(KULLANICI / "gunluk.txt", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    g.addHandler(h)
    return g


def uyari(baslik, metin, hata=True):
    """Kullanıcıya Türkçe bir ileti kutusu gösterir (konsol penceresi olmadığı için)."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, metin, baslik, 0x10 if hata else 0x40)
    except Exception:
        print(f"{baslik}: {metin}")


def calisan_ornek():
    """Zaten açık bir Bengü varsa adresini döndürür."""
    try:
        d = json.loads(KILIT.read_text(encoding="utf-8"))
        with urllib.request.urlopen(f"{d['adres']}/api/durum", timeout=2) as r:
            if json.loads(r.read()).get("uygulama") == "bengu":
                return d["adres"]
    except Exception:
        pass
    return None


def edge_bul():
    adaylar = [Path(os.environ.get(v, "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
               for v in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    try:
        import winreg
        for kok in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(kok, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe") as a:
                    adaylar.insert(0, Path(winreg.QueryValue(a, None)))
            except OSError:
                pass
    except ImportError:
        pass
    return next((str(a) for a in adaylar if a and a.is_file()), None)


def pencere_ac(adres, g, tarayici=False):
    """Edge uygulama kipinde ayrı pencere; olmazsa varsayılan tarayıcı. Edge sürecini döndürür (yoksa None)."""
    edge = None if tarayici else edge_bul()
    if edge:
        profil = KULLANICI / "pencere"
        try:
            return subprocess.Popen([edge, f"--app={adres}/", f"--user-data-dir={profil}", "--no-first-run",
                                     "--no-default-browser-check", "--disable-features=Translate,msEdgeSidebarV2",
                                     "--window-size=1320,900", "--lang=tr"],
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError:
            g.exception("Edge başlatılamadı; varsayılan tarayıcı kullanılacak")
    webbrowser.open(f"{adres}/")
    return None


def oztest(g):
    """Kurulumun sağlamlığını sınar. Rapor: %LOCALAPPDATA%\\Bengu\\oztest.txt; çıkış kodu 0 = başarılı."""
    sonuclar, basarili = [], True

    def dene(ad, f, beklenen=lambda r: bool(r)):
        nonlocal basarili
        t = time.time()
        try:
            r = f()
            ok = beklenen(r)
            sonuclar.append(f"{'✓' if ok else '✗'} {ad} ({(time.time() - t) * 1000:.0f} ms)")
            basarili &= ok
        except Exception as e:
            sonuclar.append(f"✗ {ad}: {e!r}")
            basarili = False

    import surum
    from cekirdek import anlam, arama, ceviri, rehber, cozumleme
    sonuclar.append(f"Bengü {surum.SURUM} öz testi — {time.strftime('%Y-%m-%d %H:%M')}")
    db = None
    dene("Veritabanı açılıyor", lambda: arama.baglan())
    db = arama.baglan()
    dene("Kayıt sayısı > 200.000", lambda: arama.istatistik(db)["kayit"] > 200000)
    dene("Arama: gönüllerimizde → gönül", lambda: arama.ara(db, "gönüllerimizde")["sonuclar"][0]["baslik"] == "gönül")
    dene("Arap harfiyle arama: عشق", lambda: any(g_["baslik"] == "aşk" for g_ in arama.ara(db, "عشق")["sonuclar"]))
    dene("Madde: aşk", lambda: len(arama.madde(db, "aşk")["kayitlar"]) >= 2)
    dene("Çeviri: savaş → harp/cenk", lambda: {"harp", "cenk", "harb"} & {b for o in ceviri.turkceden_osmanlicaya(db, "savaş")["oneriler"] for b in o["basliklar"]})
    dene("Tanık: tengri (Orhun)", lambda: arama.tanik(db, "tengri")["genel_toplam"] > 10)
    dene("Çözümleme: dil-i nâşâde", lambda: any(k["bicim"] == "dil-i nâşâd" for k in cozumleme.cozumle(db, "şu dil-i nâşâde")["kelimeler"]))
    dene("Rehber: savaşın Osmanlıcası", lambda: rehber.sor(db, "savaşın Osmanlıcası")["niyet"] == "karsilik")
    dene("Rehber: Divan şiirinde ayrılık temalı beyitler", lambda: rehber.sor(db, "Divan şiirinde ayrılık temalı beyitler")["bolumler"])
    model = anlam.hazir()
    sonuclar.append(f"• Anlamsal model dosyaları: {'var' if model else 'yok (Rehber kural tabanlı çalışır)'}")
    if model:
        dene("Anlamsal model çalışıyor", lambda: anlam.kodla(["deneme"]).shape == (1, 384))
        dene("Anlamsal arama: kibir → gurur", lambda: any(k["baslik"] == "gurur" for k in rehber.sor(db, "kibir anlamına gelen kelimeler")["bolumler"][0]["veri"]))
    sonuclar.append("SONUÇ: " + ("BAŞARILI" if basarili else "SORUN VAR — ayrıntılar yukarıda"))
    rapor = "\n".join(sonuclar)
    (KULLANICI / "oztest.txt").write_text(rapor, encoding="utf-8")
    g.info("Öz test:\n%s", rapor)
    try:
        print(rapor)
    except Exception:
        pass
    return basarili


def main():
    g = gunluk_kur()
    args = set(sys.argv[1:])
    import surum
    g.info("Bengü %s başlıyor (%s)", surum.SURUM, sys.executable)

    if "--oztest" in args:
        ok = oztest(g)
        if "--sessiz" not in args:
            uyari("Bengü öz testi", (KULLANICI / "oztest.txt").read_text(encoding="utf-8"), hata=not ok)
        sys.exit(0 if ok else 1)

    adres = calisan_ornek()
    if adres:  # zaten açık: yeni sunucu başlatma, pencereyi aç ve çık
        g.info("Açık bir Bengü bulundu (%s); yeni pencere açılıyor", adres)
        pencere_ac(adres, g, "--tarayici" in args)
        return

    try:
        import sunucu
        srv = sunucu.olustur(0)
    except Exception as e:
        g.exception("Sunucu başlatılamadı")
        uyari("Bengü başlatılamadı", f"Uygulama başlatılırken bir sorun oluştu:\n\n{e}\n\nAyrıntılar: {KULLANICI / 'gunluk.txt'}")
        sys.exit(1)
    adres = f"http://127.0.0.1:{srv.server_address[1]}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    KILIT.write_text(json.dumps({"adres": adres, "pid": os.getpid()}), encoding="utf-8")
    g.info("Sunucu hazır: %s", adres)

    try:
        surec = pencere_ac(adres, g, "--tarayici" in args)
        baslangic = time.time()
        # Pencere açık olduğu sürece bekle: Edge süreci yaşıyorsa ya da arayüzden yakın zamanda sinyal geldiyse
        while True:
            time.sleep(2)
            simdi = time.time()
            edge_acik = surec is not None and surec.poll() is None
            son = sunucu.son_nabiz()
            nabiz_taze = (simdi - son) < NABIZ_ZAMAN_ASIMI and son > baslangic
            ilk_bekleme = (simdi - baslangic) < (15 if surec is not None else ILK_NABIZ_BEKLEME)
            if not (edge_acik or nabiz_taze or ilk_bekleme):
                break
    except KeyboardInterrupt:
        pass
    finally:
        g.info("Pencere kapandı; Bengü kapanıyor")
        try:
            srv.shutdown()
        except Exception:
            pass
        try:
            if json.loads(KILIT.read_text(encoding="utf-8")).get("pid") == os.getpid():
                KILIT.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # son güvenlik ağı: her hatayı günlüğe yaz ve kullanıcıya göster
        logging.getLogger("bengu").exception("Beklenmeyen hata")
        uyari("Bengü", f"Beklenmeyen bir hata oluştu:\n\n{e}\n\nAyrıntılar: {KULLANICI / 'gunluk.txt'}")
        sys.exit(1)
