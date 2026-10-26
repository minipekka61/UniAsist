import os
import uuid

from flask import Blueprint, render_template, request
from werkzeug.utils import secure_filename

import config
from uniasist.ekran.yardimcilar import giris_required, paket_getir
from uniasist.enumlar import KayitDurumu, Rol
from uniasist.hatalar import IsKuraliIhlaliException

belgeyonetim_bp = Blueprint("belgeyonetim", __name__)


def _dosya_kaydet(dosya):
    klasor = config.DOSYA_KLASORU
    os.makedirs(klasor, exist_ok=True)
    guvenli_ad = secure_filename(dosya.filename) or "belge"
    yol = os.path.join(klasor, f"{uuid.uuid4().hex}_{guvenli_ad}")
    boyut = len(dosya.read())
    dosya.seek(0)
    dosya.save(yol)
    return guvenli_ad, yol, boyut


def _belgeler_sayfasi(kur_, hata=None, bilgi=None):
    return render_template(
        "belgeler.html",
        belgeler=kur_.bilgi_tabani.belgeleriListele(),
        hata=hata,
        bilgi=bilgi,
    )


@belgeyonetim_bp.route("/personel/belgeler")
@giris_required([Rol.PERSONEL, Rol.YONETICI])
def belgeler():
    return _belgeler_sayfasi(paket_getir())


@belgeyonetim_bp.route("/personel/belge-yukle", methods=["POST"])
@giris_required([Rol.PERSONEL, Rol.YONETICI])
def belge_yukle():
    kur_ = paket_getir()
    dosya = request.files.get("dosya")
    baslik = request.form.get("baslik", "")
    kategori = request.form.get("kategori", "")
    if dosya is None or not dosya.filename:
        return _belgeler_sayfasi(kur_, hata="Dosya seçilmedi.")
    try:
        ad, yol, boyut = _dosya_kaydet(dosya)
        belge = kur_.bilgi_tabani.belgeYukle(ad, yol, boyut, baslik, kategori)
    except IsKuraliIhlaliException as e:
        return _belgeler_sayfasi(kur_, hata=e.mesaj)
    return _belgeler_sayfasi(kur_, bilgi=f"Belge yüklendi ve aktif edildi: {belge.baslik}")


@belgeyonetim_bp.route("/personel/belge-guncelle/<int:belge_id>", methods=["POST"])
@giris_required([Rol.PERSONEL, Rol.YONETICI])
def belge_guncelle(belge_id):
    kur_ = paket_getir()
    baslik = request.form.get("baslik", "")
    kategori = request.form.get("kategori", "")
    dosya = request.files.get("dosya")
    try:
        if dosya is not None and dosya.filename:
            ad, yol, boyut = _dosya_kaydet(dosya)
            kur_.bilgi_tabani.belgeGuncelle(
                belge_id,
                baslik,
                kategori,
                yeni_dosya_yolu=yol,
                yeni_dosya_adi=ad,
                yeni_boyut_byte=boyut,
            )
        else:
            kur_.bilgi_tabani.belgeGuncelle(belge_id, baslik, kategori)
    except IsKuraliIhlaliException as e:
        return _belgeler_sayfasi(kur_, hata=e.mesaj)
    return _belgeler_sayfasi(kur_, bilgi="Belge güncellendi.")


@belgeyonetim_bp.route("/personel/belge-sil/<int:belge_id>", methods=["POST"])
@giris_required([Rol.PERSONEL, Rol.YONETICI])
def belge_sil(belge_id):
    kur_ = paket_getir()
    try:
        kur_.bilgi_tabani.belgeSil(belge_id)
    except IsKuraliIhlaliException as e:
        return _belgeler_sayfasi(kur_, hata=e.mesaj)
    return _belgeler_sayfasi(kur_, bilgi="Belge silindi.")


@belgeyonetim_bp.route("/personel/sss-ekle", methods=["GET", "POST"])
@giris_required([Rol.PERSONEL, Rol.YONETICI])
def sss_ekle():
    kur_ = paket_getir()
    hata = None
    bilgi = None
    soru = ""
    kayit_id = request.args.get("kayit_id", type=int) or request.form.get("kayit_id", type=int)
    if request.method == "GET":
        if kayit_id:
            kayit = kur_.yanitlanamayan.yanitlanamayan_soru_deposu.idIleBul(kayit_id)
            if kayit is not None:
                soru = kayit.soru_metni
    else:
        soru = request.form.get("soru", "")
        cevap = request.form.get("cevap", "")
        kategori = request.form.get("kategori", "")
        try:
            girdi = kur_.bilgi_tabani.sssEkle(soru, cevap, kategori)
            if kayit_id:
                kur_.yanitlanamayan.sssIleCoz(kayit_id, girdi)
                bilgi = "SSS girdisi eklendi ve yanıtlanamayan soru çözüldü olarak işaretlendi."
            else:
                bilgi = "SSS girdisi eklendi."
        except IsKuraliIhlaliException as e:
            hata = e.mesaj
    return render_template(
        "sss_ekle.html", hata=hata, bilgi=bilgi, soru=soru, kayit_id=kayit_id
    )


@belgeyonetim_bp.route("/personel/yanitlanamayan-sorular")
@giris_required([Rol.PERSONEL, Rol.YONETICI])
def yanitlanamayan_sorular():
    kur_ = paket_getir()
    try:
        durum = KayitDurumu(request.args.get("durum", "ACIK"))
    except ValueError:
        durum = KayitDurumu.ACIK
    kayitlar = kur_.yanitlanamayan.listele(durum)
    return render_template("yanitlanamayan.html", kayitlar=kayitlar, durum=durum.value)


@belgeyonetim_bp.route("/personel/geri-bildirimler")
@giris_required([Rol.PERSONEL, Rol.YONETICI])
def geri_bildirimler():
    kur_ = paket_getir()
    ozetler = kur_.geri_bildirim.yararsizlariListele()
    return render_template("geribildirimler.html", ozetler=ozetler)
