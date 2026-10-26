from flask import Blueprint, g, render_template, request

from uniasist.ekran.yardimcilar import giris_required, paket_getir
from uniasist.enumlar import Rol
from uniasist.hatalar import IsKuraliIhlaliException

kullaniciyonetimi_bp = Blueprint("kullaniciyonetimi", __name__)


def _kullanicilar_sayfasi(kur_, arama="", hata=None, bilgi=None):
    return render_template(
        "kullanicilar.html",
        kullanicilar=kur_.kullanici_yonetimi.kullanicilariListele(arama),
        arama=arama,
        hata=hata,
        bilgi=bilgi,
    )


@kullaniciyonetimi_bp.route("/yonetici/kullanicilar")
@giris_required([Rol.YONETICI])
def kullanicilar():
    return _kullanicilar_sayfasi(paket_getir(), request.args.get("q", ""))


@kullaniciyonetimi_bp.route("/yonetici/kullanicilar/<int:kullanici_id>/rol", methods=["POST"])
@giris_required([Rol.YONETICI])
def rol_degistir(kullanici_id):
    kur_ = paket_getir()
    try:
        yeni_rol = Rol(request.form.get("yeni_rol", ""))
        kur_.kullanici_yonetimi.rolDegistir(
            g.aktif_kullanici.kullanici_id, kullanici_id, yeni_rol
        )
    except (IsKuraliIhlaliException, ValueError) as e:
        mesaj = e.mesaj if isinstance(e, IsKuraliIhlaliException) else "Geçersiz rol."
        return _kullanicilar_sayfasi(kur_, hata=mesaj)
    return _kullanicilar_sayfasi(kur_, bilgi="Kullanıcı rolü güncellendi.")


@kullaniciyonetimi_bp.route("/yonetici/kullanicilar/<int:kullanici_id>/devre-disi", methods=["POST"])
@giris_required([Rol.YONETICI])
def devre_disi(kullanici_id):
    kur_ = paket_getir()
    try:
        kur_.kullanici_yonetimi.hesapDevreDisiBirak(
            g.aktif_kullanici.kullanici_id, kullanici_id
        )
    except IsKuraliIhlaliException as e:
        return _kullanicilar_sayfasi(kur_, hata=e.mesaj)
    return _kullanicilar_sayfasi(kur_, bilgi="Hesap devre dışı bırakıldı.")
