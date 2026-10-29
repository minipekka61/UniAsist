from flask import Blueprint, g, render_template, request

from uniasist.ekran.yardimcilar import giris_required, paket_getir
from uniasist.enumlar import Rol
from uniasist.hatalar import IsKuraliIhlaliException

kullaniciyonetimi_bp = Blueprint("kullaniciyonetimi", __name__)


def _kullanicilar_sayfasi(kur_, arama="", hata=None, bilgi=None):
    satirlar = []
    for kullanici in kur_.kullanici_yonetimi.kullanicilariListele(arama):
        universite = kur_.universite_deposu.idIleBul(kullanici.universite_id)
        satirlar.append((kullanici, universite.ad if universite else "—"))
    return render_template(
        "kullanicilar.html",
        satirlar=satirlar,
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


@kullaniciyonetimi_bp.route("/yonetici/bildirimler")
@giris_required([Rol.YONETICI])
def bildirimler():
    return _bildirimler_sayfasi(paket_getir())


@kullaniciyonetimi_bp.route("/yonetici/bildirimler/<int:bildirim_id>/karar", methods=["POST"])
@giris_required([Rol.YONETICI])
def bildirim_karar(bildirim_id):
    kur_ = paket_getir()
    silinsin = request.form.get("sil") == "1"
    try:
        kur_.moderasyon.bildirimiDegerlendir(bildirim_id, silinsin=silinsin)
    except IsKuraliIhlaliException as e:
        return _bildirimler_sayfasi(kur_, hata=e.mesaj)
    return _bildirimler_sayfasi(kur_, bilgi="Bildirim değerlendirildi.")


def _bildirimler_sayfasi(kur_, hata=None, bilgi=None):
    kayitlar = []
    for bildirim, belge in kur_.moderasyon.acikBildirimler():
        sahip = kur_.kimlik.kullanici_deposu.idIleBul(belge.sahip_id)
        bildiren = kur_.kimlik.kullanici_deposu.idIleBul(bildirim.bildiren_id)
        kayitlar.append({
            "bildirim": bildirim,
            "belge": belge,
            "sahip_adi": sahip.ad_soyad if sahip else "—",
            "bildiren_adi": bildiren.ad_soyad if bildiren else "—",
        })
    return render_template(
        "bildirimler.html",
        kayitlar=kayitlar,
        hata=hata,
        bilgi=bilgi,
    )
