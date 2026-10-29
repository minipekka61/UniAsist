from flask import Blueprint, g, make_response, redirect, render_template, request

from uniasist.ekran.yardimcilar import giris_required, paket_getir
from uniasist.enumlar import Rol
from uniasist.hatalar import IsKuraliIhlaliException
from uniasist.veri.bolumler import BOLUMLER

giris_bp = Blueprint("giris", __name__)


@giris_bp.route("/kayit", methods=["GET", "POST"])
def kayit():
    kur_ = paket_getir()
    hata = None
    if request.method == "POST":
        try:
            kur_.kimlik.kayitOl(
                request.form.get("ad_soyad", ""),
                request.form.get("eposta", ""),
                request.form.get("sifre", ""),
                request.form.get("sifre_tekrar", ""),
                universite=request.form.get("universite", ""),
                bolum=request.form.get("bolum", ""),
            )
            return render_template(
                "giris.html",
                bilgi=(
                    "Hesabınız oluşturuldu. E-postanıza gönderilen doğrulama "
                    "bağlantısına tıklayarak hesabınızı aktifleştirebilirsiniz."
                ),
            )
        except IsKuraliIhlaliException as e:
            hata = e.mesaj
    return render_template(
        "kayit.html",
        hata=hata,
        bolumler=BOLUMLER,
    )


@giris_bp.route("/dogrula/<token>")
def dogrula(token):
    kur_ = paket_getir()
    try:
        kur_.kimlik.dogrula(token)
        return render_template("dogrulama.html", basarili=True)
    except IsKuraliIhlaliException:
        return render_template("dogrulama.html", basarili=False)


@giris_bp.route("/dogrulama/yeniden", methods=["POST"])
@giris_required()
def dogrulama_yeniden():
    kur_ = paket_getir()
    kur_.kimlik.dogrulamaGonder(g.aktif_kullanici.eposta)
    return render_template(
        "giris.html",
        bilgi="Doğrulama e-postası tekrar gönderildi. Gelen kutunuzu kontrol edin.",
    )


@giris_bp.route("/giris", methods=["GET", "POST"])
def giris():
    hata = None
    if request.method == "POST":
        try:
            kur_ = paket_getir()
            oturum = kur_.kimlik.girisYap(
                request.form.get("eposta", ""), request.form.get("sifre", "")
            )
            kullanici = kur_.kimlik.kullanici_deposu.idIleBul(oturum.kullanici_id)
            hedef = "/yonetici/kullanicilar" if kullanici.rol == Rol.YONETICI else "/"
            yanit = make_response(redirect(hedef))
            yanit.set_cookie("uniasist_oturum", oturum.oturum_id, httponly=True)
            return yanit
        except IsKuraliIhlaliException as e:
            hata = e.mesaj
    return render_template("giris.html", hata=hata)


@giris_bp.route("/cikis")
def cikis():
    kur_ = paket_getir()
    kur_.kimlik.cikisYap(request.cookies.get("uniasist_oturum"))
    yanit = make_response(redirect("/giris"))
    yanit.delete_cookie("uniasist_oturum")
    return yanit


@giris_bp.route("/sifre-degistir", methods=["GET", "POST"])
@giris_required()
def sifre_degistir():
    hata = None
    bilgi = None
    if request.method == "POST":
        try:
            kur_ = paket_getir()
            kur_.kimlik.sifreDegistir(
                g.aktif_kullanici.kullanici_id,
                request.form.get("mevcut_sifre", ""),
                request.form.get("yeni_sifre", ""),
                request.form.get("yeni_sifre_tekrar", ""),
            )
            bilgi = "Şifreniz güncellendi."
        except IsKuraliIhlaliException as e:
            hata = e.mesaj
    return render_template("sifre.html", hata=hata, bilgi=bilgi)
