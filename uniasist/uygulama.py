from pathlib import Path

from flask import Flask, g

import config
from uniasist.ekran.giris import giris_bp
from uniasist.ekran.inceleme import inceleme_bp
from uniasist.ekran.kullaniciyonetimi import kullaniciyonetimi_bp
from uniasist.ekran.rapor import rapor_bp
from uniasist.ekran.sohbet import sohbet_bp
from uniasist.ekran.yardimcilar import oturum_yukle
from uniasist.kurulum import kur

_KOK = Path(__file__).resolve().parent.parent


def tarih_filtresi(deger, bicim="%d.%m.%Y %H:%M"):
    if deger is None:
        return ""
    return deger.strftime(bicim)


def uygulama_olustur(paket=None):
    if paket is None:
        paket = kur(seed_yap=True)
    uygulama = Flask(
        __name__,
        template_folder=str(_KOK / "sablonlar"),
        static_folder=str(_KOK / "statik"),
    )
    uygulama.secret_key = config.SECRET_KEY
    uygulama.extensions["uniasist"] = paket

    uygulama.jinja_env.filters["tarih"] = tarih_filtresi

    @uygulama.before_request
    def _oturum_yukle():
        oturum_yukle(paket)

    uygulama.register_blueprint(giris_bp)
    uygulama.register_blueprint(sohbet_bp)
    uygulama.register_blueprint(inceleme_bp)
    uygulama.register_blueprint(kullaniciyonetimi_bp)
    uygulama.register_blueprint(rapor_bp)

    @uygulama.context_processor
    def _ortak():
        yerel_mod = type(paket.yapay_zeka).__name__ == "YerelAramaServisi"
        return {
            "aktif_kullanici": getattr(g, "aktif_kullanici", None),
            "yerel_mod": yerel_mod,
        }

    return uygulama
