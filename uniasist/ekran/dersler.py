from flask import Blueprint, g, redirect, render_template, request

from uniasist.ekran.yardimcilar import dogrulama_required, paket_getir

dersler_bp = Blueprint("dersler", __name__)


@dersler_bp.route("/dersler")
@dogrulama_required()
def dersler():
    kur_ = paket_getir()
    q = request.args.get("q", "").strip()
    liste = kur_.ders_deposu.ara(q) if q else kur_.ders_deposu.hepsiniListele()
    takip_idler = kur_.ders_deposu.kullanicininDersIdleri(
        g.aktif_kullanici.kullanici_id
    )
    satirlar = [(ders, ders.ders_id in takip_idler) for ders in liste]
    return render_template("dersler.html", satirlar=satirlar, q=q)


@dersler_bp.route("/dersler", methods=["POST"])
@dogrulama_required()
def ders_ekle():
    kur_ = paket_getir()
    ad = request.form.get("ad", "").strip()
    if ad:
        ders = kur_.ders_deposu.bulVeYaOlustur(ad)
        kur_.ders_deposu.takipEt(g.aktif_kullanici.kullanici_id, ders.ders_id)
    return redirect("/dersler")


@dersler_bp.route("/dersler/<int:ders_id>")
@dogrulama_required()
def ders_detay(ders_id):
    kur_ = paket_getir()
    ders = kur_.ders_deposu.idIleBul(ders_id)
    if ders is None:
        return render_template("ders.html", ders=None), 404
    takipte = kur_.ders_deposu.takipteMi(
        g.aktif_kullanici.kullanici_id, ders_id
    )
    belgeler = (
        kur_.bilgi_tabani.dersinPaylasilanlari(ders_id) if takipte else []
    )
    return render_template(
        "ders.html", ders=ders, takipte=takipte, belgeler=belgeler
    )


@dersler_bp.route("/dersler/<int:ders_id>/takip", methods=["POST"])
@dogrulama_required()
def ders_takip(ders_id):
    kur_ = paket_getir()
    kur_.ders_deposu.takipEt(g.aktif_kullanici.kullanici_id, ders_id)
    return redirect(f"/dersler/{ders_id}")


@dersler_bp.route("/dersler/<int:ders_id>/birak", methods=["POST"])
@dogrulama_required()
def ders_birak(ders_id):
    kur_ = paket_getir()
    kur_.ders_deposu.takibiBirak(g.aktif_kullanici.kullanici_id, ders_id)
    return redirect(f"/dersler/{ders_id}")
