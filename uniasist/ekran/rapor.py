from datetime import datetime

from flask import Blueprint, Response, render_template, request

from uniasist.ekran.yardimcilar import giris_required, paket_getir
from uniasist.enumlar import Rol
from uniasist.hatalar import IsKuraliIhlaliException

rapor_bp = Blueprint("rapor", __name__)


def _tarih_oku(deger):
    if not deger:
        return None
    try:
        return datetime.strptime(deger, "%Y-%m-%d")
    except ValueError:
        return None


def _rapor_getir(kur_):
    baslangic = _tarih_oku(request.args.get("baslangic", ""))
    bitis = _tarih_oku(request.args.get("bitis", ""))
    if bitis is not None and baslangic is not None and bitis < baslangic:
        raise IsKuraliIhlaliException(
            "IK-33", "Bitiş tarihi başlangıç tarihinden önce olamaz."
        )
    return kur_.rapor.raporOlustur(baslangic, bitis)


@rapor_bp.route("/yonetici/rapor")
@giris_required([Rol.YONETICI])
def rapor_goruntule():
    kur_ = paket_getir()
    hata = None
    try:
        rapor = _rapor_getir(kur_)
    except IsKuraliIhlaliException as e:
        hata = e.mesaj
        rapor = kur_.rapor.raporOlustur()
    return render_template("rapor.html", rapor=rapor, hata=hata)


@rapor_bp.route("/yonetici/rapor/csv")
@giris_required([Rol.YONETICI])
def rapor_csv():
    kur_ = paket_getir()
    try:
        rapor = _rapor_getir(kur_)
    except IsKuraliIhlaliException:
        rapor = kur_.rapor.raporOlustur()
    icerik = kur_.rapor.csvHazirla(rapor).encode("utf-8-sig")
    dosya_adi = f"UniAsist_Rapor_{rapor.baslangic:%Y-%m-%d}_{rapor.bitis:%Y-%m-%d}.csv"
    return Response(
        icerik,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={dosya_adi}"},
    )
