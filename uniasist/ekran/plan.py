from flask import Blueprint, g, redirect, render_template

from uniasist.ekran.yardimcilar import dogrulama_required, paket_getir
from uniasist.hatalar import IsKuraliIhlaliException

plan_bp = Blueprint("plan", __name__)


@plan_bp.route("/plan")
@dogrulama_required()
def plan_ekrani():
    kur_ = paket_getir()
    haklar = kur_.plan.haklar(g.aktif_kullanici)
    return render_template("plan.html", haklar=haklar)


@plan_bp.route("/plan/pro", methods=["POST"])
@dogrulama_required()
def pro_yap():
    kur_ = paket_getir()
    hata = None
    try:
        kur_.plan.proYap(g.aktif_kullanici)
    except IsKuraliIhlaliException as e:
        hata = e.mesaj
    if hata is None:
        return redirect("/plan")
    haklar = kur_.plan.haklar(g.aktif_kullanici)
    return render_template("plan.html", haklar=haklar, hata=hata)


@plan_bp.route("/plan/ucretsiz", methods=["POST"])
@dogrulama_required()
def ucretsize_don():
    kur_ = paket_getir()
    hata = None
    try:
        kur_.plan.ucretsizeDon(g.aktif_kullanici)
    except IsKuraliIhlaliException as e:
        hata = e.mesaj
    if hata is None:
        return redirect("/plan")
    haklar = kur_.plan.haklar(g.aktif_kullanici)
    return render_template("plan.html", haklar=haklar, hata=hata)
