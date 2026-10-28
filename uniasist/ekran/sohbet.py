import json
import uuid

from flask import Blueprint, Response, abort, g, redirect, render_template, request

from uniasist.ekran.yardimcilar import giris_required, paket_getir
from uniasist.enumlar import GonderenTuru, KayitDurumu
from uniasist.hatalar import IsKuraliIhlaliException

sohbet_bp = Blueprint("sohbet", __name__)


def _ziyaretci_kimligi():
    return request.cookies.get("ziyaretci_id")


@sohbet_bp.route("/")
def sohbet_sayfasi():
    kur_ = paket_getir()
    mesajlar = []
    gosterilen_sohbet_id = None
    if g.aktif_kullanici:
        sohbet_id = request.args.get("sohbet_id", type=int)
        if request.args.get("yeni") is None and not sohbet_id:
            liste = kur_.sohbet.sohbetleriListele(g.aktif_kullanici.kullanici_id)
            if liste:
                sohbet_id = liste[0].sohbet_id
        if sohbet_id:
            try:
                sohbet = kur_.sohbet.sohbetGetir(sohbet_id, g.aktif_kullanici.kullanici_id)
                mesajlar = sohbet.mesajlar
                gosterilen_sohbet_id = sohbet.sohbet_id
            except IsKuraliIhlaliException:
                mesajlar = []
    else:
        ziyaretci_id = _ziyaretci_kimligi()
        if ziyaretci_id and ziyaretci_id in kur_.sohbet.ziyaretci_sohbetleri:
            mesajlar = kur_.sohbet.ziyaretci_sohbetleri[ziyaretci_id].mesajlar
    return render_template(
        "sohbet.html", mesajlar=mesajlar, sohbet_id=gosterilen_sohbet_id
    )


def _ogrenci_sohbeti(kur_):
    sohbet_id = request.form.get("sohbet_id", type=int)
    if sohbet_id:
        return kur_.sohbet.sohbetGetir(sohbet_id, g.aktif_kullanici.kullanici_id)
    return kur_.sohbet.yeniSohbetBaslat(kullanici=g.aktif_kullanici)


@sohbet_bp.route("/sohbet/yanit", methods=["POST"])
def yanit():
    kur_ = paket_getir()
    soru = request.form.get("soru", "")
    ziyaretci_id = None
    if g.aktif_kullanici:
        sohbet = _ogrenci_sohbeti(kur_)
    else:
        ziyaretci_id = _ziyaretci_kimligi() or uuid.uuid4().hex
        sohbet = kur_.sohbet.yeniSohbetBaslat(ziyaretci_oturum_id=ziyaretci_id)

    def akis():
        for olay in kur_.sohbet.soruSorAkis(sohbet, soru):
            yield _sse(olay, sohbet)

    yanit_ = Response(akis(), mimetype="text/event-stream")
    if ziyaretci_id and not _ziyaretci_kimligi():
        yanit_.set_cookie("ziyaretci_id", ziyaretci_id, httponly=True)
    return yanit_


def _sse(olay, sohbet):
    tur = olay.get("tur")
    veri = {"tur": tur}
    if tur == "hata":
        veri["mesaj"] = olay["mesaj"]
    elif tur == "parca":
        veri["metin"] = olay["metin"]
    elif tur == "sonuc":
        veri["durum"] = olay["durum"]
        veri["metin"] = olay["metin"]
        veri["uyarilar"] = olay.get("uyarilar", [])
        veri["kaynaklar"] = [
            {
                "kaynak_adi": r.kaynak_adi,
                "bolum_bilgisi": r.bolum_bilgisi,
                "kaynak_id": r.kaynak_id,
            }
            for r in olay.get("kaynaklar", [])
        ]
        yanit_mesaji = olay.get("yanit")
        veri["mesaj_id"] = yanit_mesaji.mesaj_id if yanit_mesaji else None
        veri["sohbet_id"] = sohbet.sohbet_id
    return f"event: {tur}\ndata: {json.dumps(veri, ensure_ascii=False)}\n\n"


@sohbet_bp.route("/sohbet/yeni", methods=["GET", "POST"])
def yeni_sohbet():
    kur_ = paket_getir()
    if not g.aktif_kullanici:
        ziyaretci_id = _ziyaretci_kimligi()
        if ziyaretci_id and ziyaretci_id in kur_.sohbet.ziyaretci_sohbetleri:
            del kur_.sohbet.ziyaretci_sohbetleri[ziyaretci_id]
        return redirect("/")
    return redirect("/?yeni=1")


@sohbet_bp.route("/gecmis")
@giris_required()
def gecmis():
    kur_ = paket_getir()
    sohbetler = kur_.sohbet.sohbetleriListele(g.aktif_kullanici.kullanici_id)
    return render_template("gecmis.html", sohbetler=sohbetler)


@sohbet_bp.route("/gecmis/tumunu-sil", methods=["POST"])
@giris_required()
def tumunu_sil():
    kur_ = paket_getir()
    kur_.sohbet.tumSohbetleriSil(g.aktif_kullanici.kullanici_id)
    return redirect("/gecmis")


@sohbet_bp.route("/gecmis/<int:sohbet_id>")
@giris_required()
def gecmis_ac(sohbet_id):
    kur_ = paket_getir()
    try:
        sohbet = kur_.sohbet.sohbetGetir(sohbet_id, g.aktif_kullanici.kullanici_id)
    except IsKuraliIhlaliException:
        abort(403)
    return render_template(
        "sohbet.html",
        mesajlar=sohbet.mesajlar,
        sadece_okuma=True,
        sohbet_id=sohbet.sohbet_id,
    )


@sohbet_bp.route("/gecmis/<int:sohbet_id>/sil", methods=["POST"])
@giris_required()
def gecmis_sil(sohbet_id):
    kur_ = paket_getir()
    try:
        kur_.sohbet.sohbetSil(sohbet_id, g.aktif_kullanici.kullanici_id)
    except IsKuraliIhlaliException:
        abort(403)
    return redirect("/gecmis")


@sohbet_bp.route("/kaynak/<int:kaynak_id>")
def kaynak_ac(kaynak_id):
    kur_ = paket_getir()
    from uniasist.entity import KaynakReferansi

    referans = KaynakReferansi(kaynak_id=kaynak_id)
    kaynak = kur_.sohbet.kaynagiGoruntule(referans)
    if kaynak is None:
        return render_template("kaynak.html", kaynak=None)
    return render_template(
        "kaynak.html",
        kaynak=kaynak,
        bolum=request.args.get("bolum", ""),
    )


@sohbet_bp.route("/geri-bildirim", methods=["POST"])
@giris_required()
def geri_bildirim():
    kur_ = paket_getir()
    veri = request.get_json(silent=True) or {}
    try:
        from uniasist.enumlar import GeriBildirimTuru

        kur_.geri_bildirim.geriBildirimVer(
            g.aktif_kullanici.kullanici_id,
            int(veri.get("mesaj_id", 0)),
            GeriBildirimTuru(veri.get("tur")),
            veri.get("aciklama"),
        )
        return {"ok": True}
    except (IsKuraliIhlaliException, ValueError) as e:
        mesaj = e.mesaj if isinstance(e, IsKuraliIhlaliException) else "Geçersiz istek."
        return {"ok": False, "hata": mesaj}, 400
