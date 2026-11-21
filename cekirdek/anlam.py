"""Bengü — anlamsal (vektör) arama.

Model: intfloat/multilingual-e5-small (MIT lisansı), int8 ONNX sürümü (Xenova dönüşümü), ~118 MB.
Model yalnızca metinleri anlamlarına göre vektöre çevirir; metin ÜRETMEZ. Sonuçlar daima sözlükteki
kayıtlı tanımlar ve beyitlerdir.

Kullanım isteğe bağlıdır: numpy / onnxruntime / tokenizers ya da model dosyası yoksa `hazir()` False döner
ve uygulama anlamsal arama olmadan çalışmaya devam eder.
"""
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
MODEL_DIZINI = KOK / "modeller" / "e5-small"
VEKTOR_DOSYASI = KOK / "veri" / "vektor.npz"

_model = None
_vektor = None


def _yukle_model():
    global _model
    if _model is None:
        import numpy as np  # noqa: F401
        import onnxruntime as ort
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(MODEL_DIZINI / "tokenizer.json"))
        tok.enable_truncation(max_length=128)
        tok.enable_padding(pad_id=1, pad_token="<pad>")
        secenek = ort.SessionOptions()
        secenek.intra_op_num_threads = 4
        # Uzun Windows yollarında sorun çıkmasın diye model bayt olarak verilir
        oturum = ort.InferenceSession((MODEL_DIZINI / "model_quantized.onnx").read_bytes(), secenek,
                                      providers=["CPUExecutionProvider"])
        _model = (tok, oturum, {i.name for i in oturum.get_inputs()})
    return _model


def kodla(metinler, tur="passage", parti=64):
    """Metinleri birim uzunluklu vektörlere çevirir. e5 modeli 'query: ' / 'passage: ' önekleri ister."""
    import numpy as np
    tok, oturum, girdiler = _yukle_model()
    out = []
    for i in range(0, len(metinler), parti):
        kodlar = tok.encode_batch([f"{tur}: {m}" for m in metinler[i:i + parti]])
        ids = np.array([k.ids for k in kodlar], dtype=np.int64)
        maske = np.array([k.attention_mask for k in kodlar], dtype=np.int64)
        besle = {"input_ids": ids, "attention_mask": maske}
        if "token_type_ids" in girdiler:
            besle["token_type_ids"] = np.zeros_like(ids)
        gizli = oturum.run(None, besle)[0]  # (n, uzunluk, 384)
        m = maske[..., None].astype(np.float32)
        v = (gizli * m).sum(1) / np.clip(m.sum(1), 1e-9, None)  # ortalama havuzlama
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        out.append(v.astype(np.float32))
    return np.vstack(out) if out else np.zeros((0, 384), dtype=np.float32)


_kapali = [False]


def devre_disi():
    """Model yüklenemezse çağrılır: uygulama anlamsal arama olmadan devam eder."""
    _kapali[0] = True


def hazir():
    if _kapali[0]:
        return False
    try:
        import numpy  # noqa: F401
        import onnxruntime  # noqa: F401
        import tokenizers  # noqa: F401
    except ImportError:
        return False
    return (MODEL_DIZINI / "model_quantized.onnx").exists() and VEKTOR_DOSYASI.exists()


def _yukle_vektor():
    global _vektor
    if _vektor is None:
        import numpy as np
        d = np.load(VEKTOR_DOSYASI)
        _vektor = {"kayit_id": d["kayit_id"], "kayit_v": d["kayit_v"].astype(np.float32),
                   "satir_id": d["satir_id"], "satir_v": d["satir_v"].astype(np.float32)}
    return _vektor


def benzer(sorgu, hedef="kayit", n=40, aday=None):
    """Sorguya anlamca en yakın kayıt / satır kimlikleri ve benzerlik puanları.
    aday: yalnız bu kimlikler arasında ara (ör. süzgeçten geçmiş kayıtlar)."""
    import numpy as np
    v = _yukle_vektor()
    ids, mat = v[f"{hedef}_id"], v[f"{hedef}_v"]
    q = kodla([sorgu], "query")[0]
    if aday is not None:
        maske = np.isin(ids, np.fromiter(aday, dtype=ids.dtype))
        ids, mat = ids[maske], mat[maske]
        if not len(ids):
            return []
    puan = mat @ q
    k = min(n, len(puan))
    en = np.argpartition(-puan, k - 1)[:k]
    en = en[np.argsort(-puan[en])]
    return [(int(ids[i]), float(puan[i])) for i in en]
