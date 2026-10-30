import os
import uuid

from flask import Blueprint, g, redirect, render_template, request
from werkzeug.utils import secure_filename

import config
from uniasist.ekran.yardimcilar import dogrulama_required, paket_getir
from uniasist.enumlar import Gorunurluk
from uniasist.hatalar import IsKuraliIhlaliException

belgelerim_bp = Blueprint("belgelerim", __name__)


def _dosya_kaydet(dosya):
    klasor = config.DOSYA_KLASORU
    os.makedirs(klasor, exist_ok=True)
    guvenli_ad = secure_filename(dosya.filename) or "belge"
    yol = os.path.join(klasor, f"{uuid.uuid4().hex}_{guvenli_ad}")
    boyut = len(dosya.read())
    dosya.seek(0)
    dosya.save(yol)
    return guvenli_ad, yol, boyut


def _dosya_temizle(yol):
    try:
        os.remove(yol)
    except OSError:
        pass


def _sayfa(kur_, kullanici, sekme="benim", hata=None, bilgi=None):
    dersler = kur_.ders_deposu.kullanicininDersleri(kullanici.kullanici_id)
    if sekme == "ders":
        ders_id = request.args.get("ders_id", type=int)
        if ders_id:
            takipte = kur_.ders_deposu.takipteMi(kullanici.kullanici_id, ders_id)
            belgeler = kur_.bilgi_tabani.dersinPaylasilanlari(ders_id)
            if not takipte:
                belgeler = [
                    b for b in belgeler
                    if b.sahip_id == kullanici.kullanici_id
                ]
        else:
            belgeler = []
            for ders in dersler:
                belgeler.extend(kur_.bilgi_tabani.dersinPaylasilanlari(ders.ders_id))
    else:
        sekme = "benim"
        belgeler = kur_.bilgi_tabani.belgeleriListele(kullanici.kullanici_id)
    return render_template(
        "belgelerim.html",
        belgeler=belgeler,
        dersler=dersler,
        sekme=sekme,
        hata=hata,
        bilgi=bilgi,
    )


@belgelerim_bp.route("/belgelerim")
@dogrulama_required()
def belgelerim():
    kur_ = paket_getir()
    return _sayfa(
        kur_, g.aktif_kullanici, request.args.get("sekme", "benim")
    )


@belgelerim_bp.route("/belgelerim/yukle", methods=["POST"])
@dogrulama_required()
def belge_yukle():
    kur_ = paket_getir()
    kullanici = g.aktif_kullanici
    dosya = request.files.get("dosya")
    baslik = request.form.get("baslik", "")
    kategori = request.form.get("kategori", "")
    ders_adi = request.form.get("ders", "")
    gorunurluk = (
        Gorunurluk.PAYLASILAN if request.form.get("paylas") else Gorunurluk.OZEL
    )
    if dosya is None or not dosya.filename:
        return _sayfa(kur_, kullanici, hata="Dosya seçilmedi.")
    ad, yol, boyut = _dosya_kaydet(dosya)
    try:
        belge = kur_.bilgi_tabani.belgeYukle(
            ad, yol, boyut, baslik, kategori,
            sahip=kullanici, gorunurluk=gorunurluk, ders_adi=ders_adi,
        )
    except IsKuraliIhlaliException as e:
        _dosya_temizle(yol)
        return _sayfa(kur_, kullanici, hata=e.mesaj)
    return _sayfa(
        kur_, kullanici,
        bilgi=f"Belge yüklendi: {belge.baslik}",
    )


@belgelerim_bp.route("/belgelerim/<int:belge_id>/gorunurluk", methods=["POST"])
@dogrulama_required()
def gorunurluk_degistir(belge_id):
    kur_ = paket_getir()
    try:
        gorunurluk = Gorunurluk(request.form.get("gorunurluk", ""))
    except ValueError:
        gorunurluk = Gorunurluk.OZEL
    try:
        kur_.bilgi_tabani.gorunurlukDegistir(
            belge_id, g.aktif_kullanici, gorunurluk,
            ders_adi=request.form.get("ders", ""),
        )
    except IsKuraliIhlaliException as e:
        return _sayfa(kur_, g.aktif_kullanici, hata=e.mesaj)
    return redirect("/belgelerim")


@belgelerim_bp.route("/belgelerim/<int:belge_id>/sil", methods=["POST"])
@dogrulama_required()
def belge_sil(belge_id):
    kur_ = paket_getir()
    try:
        kur_.bilgi_tabani.belgeSil(belge_id, g.aktif_kullanici.kullanici_id)
    except IsKuraliIhlaliException as e:
        return _sayfa(kur_, g.aktif_kullanici, hata=e.mesaj)
    return redirect("/belgelerim")


@belgelerim_bp.route("/belgelerim/<int:belge_id>/guncelle", methods=["POST"])
@dogrulama_required()
def belge_guncelle(belge_id):
    kur_ = paket_getir()
    kullanici = g.aktif_kullanici
    baslik = request.form.get("baslik", "")
    kategori = request.form.get("kategori", "")
    dosya = request.files.get("dosya")
    try:
        if dosya is not None and dosya.filename:
            ad, yol, boyut = _dosya_kaydet(dosya)
            kur_.bilgi_tabani.belgeGuncelle(
                belge_id, kullanici.kullanici_id, baslik, kategori,
                yeni_dosya_yolu=yol, yeni_dosya_adi=ad, yeni_boyut_byte=boyut,
            )
        else:
            kur_.bilgi_tabani.belgeGuncelle(
                belge_id, kullanici.kullanici_id, baslik, kategori
            )
    except IsKuraliIhlaliException as e:
        if dosya is not None and dosya.filename:
            _dosya_temizle(yol)
        return _sayfa(kur_, kullanici, hata=e.mesaj)
    return _sayfa(kur_, kullanici, bilgi="Belge güncellendi.")


@belgelerim_bp.route("/belgelerim/<int:belge_id>/bildir", methods=["POST"])
@dogrulama_required()
def belge_bildir(belge_id):
    kur_ = paket_getir()
    try:
        kur_.moderasyon.bildir(
            belge_id, g.aktif_kullanici, request.form.get("neden", "")
        )
    except IsKuraliIhlaliException as e:
        return _sayfa(kur_, g.aktif_kullanici, sekme="ders", hata=e.mesaj)
    return _sayfa(
        kur_, g.aktif_kullanici, sekme="ders",
        bilgi="Bildiriminiz alındı; yönetici ekibi inceleyecek.",
    )
