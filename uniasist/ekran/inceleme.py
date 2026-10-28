from flask import Blueprint, redirect, render_template, request

from uniasist.ekran.yardimcilar import giris_required, paket_getir
from uniasist.enumlar import KayitDurumu, Rol

inceleme_bp = Blueprint("inceleme", __name__)


@inceleme_bp.route("/yonetici/yanitlanamayan-sorular")
@giris_required([Rol.YONETICI])
def yanitlanamayan_sorular():
    kur_ = paket_getir()
    try:
        durum = KayitDurumu(request.args.get("durum", "ACIK"))
    except ValueError:
        durum = KayitDurumu.ACIK
    kayitlar = kur_.yanitlanamayan.listele(durum)
    return render_template("yanitlanamayan.html", kayitlar=kayitlar, durum=durum.value)


@inceleme_bp.route("/yonetici/yanitlanamayan-sorular/<int:kayit_id>/coz", methods=["POST"])
@giris_required([Rol.YONETICI])
def yanitlanamayan_coz(kayit_id):
    kur_ = paket_getir()
    kur_.yanitlanamayan.cozulduIsaretle(kayit_id)
    return redirect("/yonetici/yanitlanamayan-sorular")


@inceleme_bp.route("/yonetici/geri-bildirimler")
@giris_required([Rol.YONETICI])
def geri_bildirimler():
    kur_ = paket_getir()
    ozetler = kur_.geri_bildirim.yararsizlariListele()
    return render_template("geribildirimler.html", ozetler=ozetler)
