from flask import Blueprint, g, redirect, render_template, request

from uniasist.ekran.yardimcilar import giris_required, paket_getir
from uniasist.hatalar import IsKuraliIhlaliException

profil_bp = Blueprint("profil", __name__)


@profil_bp.route("/profil", methods=["GET", "POST"])
@giris_required()
def profil():
    kur_ = paket_getir()
    kullanici = g.aktif_kullanici
    hata = None
    bilgi = None
    if request.method == "POST":
        try:
            kur_.kimlik.profilGuncelle(
                kullanici.kullanici_id,
                request.form.get("ad_soyad", ""),
                request.form.get("universite", ""),
                request.form.get("bolum", ""),
            )
            bilgi = "Profiliniz güncellendi."
        except IsKuraliIhlaliException as e:
            hata = e.mesaj
    kullanici = kur_.kimlik.kullanici_deposu.idIleBul(kullanici.kullanici_id)
    haklar = kur_.plan.haklar(kullanici)
    return render_template(
        "profil.html",
        kullanici=kullanici,
        haklar=haklar,
        hata=hata,
        bilgi=bilgi,
    )


@profil_bp.route("/profil/sifre", methods=["POST"])
@giris_required()
def sifre_degistir():
    kur_ = paket_getir()
    kullanici = g.aktif_kullanici
    hata = None
    bilgi = None
    try:
        kur_.kimlik.sifreDegistir(
            kullanici.kullanici_id,
            request.form.get("mevcut_sifre", ""),
            request.form.get("yeni_sifre", ""),
            request.form.get("yeni_sifre_tekrar", ""),
        )
        bilgi = "Şifreniz güncellendi."
    except IsKuraliIhlaliException as e:
        hata = e.mesaj
    haklar = kur_.plan.haklar(kullanici)
    return render_template(
        "profil.html",
        kullanici=kullanici,
        haklar=haklar,
        hata=hata,
        bilgi=bilgi,
    )
