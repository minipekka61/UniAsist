from functools import wraps

from flask import abort, current_app, g, redirect, request, url_for

from uniasist.enumlar import Rol

CEREZ_ADI = "uniasist_oturum"


def paket_getir():
    return current_app.extensions["uniasist"]


def oturum_yukle(paket):
    token = request.cookies.get(CEREZ_ADI)
    g.oturum_token = token
    g.aktif_kullanici = paket.kimlik.oturumDogrula(token) if token else None


def giris_required(roller=None):
    def dekorator(gorunum):
        @wraps(gorunum)
        def sarmal(*args, **kwargs):
            if getattr(g, "aktif_kullanici", None) is None:
                return redirect(url_for("giris.giris"))
            if roller is not None and g.aktif_kullanici.rol not in roller:
                abort(403)
            return gorunum(*args, **kwargs)

        return sarmal

    return dekorator


def dogrulama_required(roller=None):
    def dekorator(gorunum):
        @wraps(gorunum)
        def sarmal(*args, **kwargs):
            if getattr(g, "aktif_kullanici", None) is None:
                return redirect(url_for("giris.giris"))
            if roller is not None and g.aktif_kullanici.rol not in roller:
                abort(403)
            if (
                not g.aktif_kullanici.dogrulanmisMi()
                and g.aktif_kullanici.rol != Rol.YONETICI
            ):
                return redirect("/dogrulama-bekliyor")
            return gorunum(*args, **kwargs)

        return sarmal

    return dekorator
