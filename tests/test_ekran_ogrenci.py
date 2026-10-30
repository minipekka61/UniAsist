import io

import pytest

import config
from tests.yardimci import SahteYZ, gecici_db
from uniasist.enumlar import Gorunurluk
from uniasist.kurulum import kur
from uniasist.uygulama import uygulama_olustur

BELGE_METNI = (
    "Burs yonergesi universite ogrencilerine saglanan destegi duzenler. "
    "Basari bursu icin genel not ortalamasinin en az 3.00 olmasi gerekir. "
    "Burs basvurusu eylul ayinin ilk haftasinda ogrenci isleri tarafindan alinir. "
    "Ihtiyac bursu icin gelir belgesi talep edilir ve aile geliri siniri kontrol edilir. "
    "Burs kapsaminda ogrenim ucreti destegi ve harc destegi saglanir. "
    "Yurt basvurusu ayri olarak KYK sistemi uzerinden yapilir ve temmuz ayinda acilir. "
) * 3

STAJ_METNI = (
    "Staj yonergesi ogrencilerin yaz stajlarini duzenler ve zorunlu kilar. "
    "Staj basvurusu icin en az 60 gun kesintisiz calisma sarti vardir. "
    "Staj defteri staj bitiminden sonraki 15 gun icinde teslim edilir. "
) * 3


@pytest.fixture
def paket():
    return kur(db=gecici_db(), yapay_zeka=SahteYZ())


@pytest.fixture
def ortam(paket, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DOSYA_KLASORU", str(tmp_path / "dosyalar"))
    uygulama = uygulama_olustur(paket)
    uygulama.config["TESTING"] = True
    with uygulama.test_client() as istemci:
        yield istemci, paket


def dogrulanmis_ogrenci(paket, eposta="ali@universite.edu.tr",
                        bolum="Bilgisayar Mühendisliği", dogrulanmis=True,
                        pro=False):
    from uniasist.entity import Kullanici
    from uniasist.enumlar import Plan, Rol
    from uniasist.guvenlik import sifre_hashle

    k = Kullanici(
        ad_soyad="Ali Veli",
        eposta=eposta,
        sifre_hash=sifre_hashle("Gizli1234"),
        rol=Rol.OGRENCI,
        universite="Üniversite",
        bolum=bolum,
        eposta_dogrulandi=dogrulanmis,
        plan=Plan.PRO if pro else None,
    )
    paket.kimlik.kullanici_deposu.kaydet(k)
    return k


def giris_yap(istemci, eposta="ali@universite.edu.tr"):
    istemci.post("/giris", data={"eposta": eposta, "sifre": "Gizli1234"})


def test_ogrenci_belge_yukler_ve_gorur(ortam):
    istemci, paket = ortam
    ogr = dogrulanmis_ogrenci(paket)
    giris_yap(istemci)

    yanit = istemci.post("/belgelerim/yukle", data={
        "baslik": "Burs Yönergesi",
        "kategori": "Burs",
        "dosya": (io.BytesIO(BELGE_METNI.encode("utf-8")), "burs.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "Burs Yönergesi" in metin

    yanit = istemci.get("/belgelerim?sekme=ders")
    ders_metni = yanit.get_data(as_text=True)
    assert "Burs Yönergesi" not in ders_metni

    belgeler = paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id)
    assert len(belgeler) == 1
    assert belgeler[0].gorunurluk == Gorunurluk.OZEL


def test_ogrenci_paylasir_ders_gorur(ortam):
    istemci, paket = ortam
    ogr = dogrulanmis_ogrenci(paket, pro=True)
    giris_yap(istemci)
    istemci.post("/belgelerim/yukle", data={
        "baslik": "Burs Yönergesi",
        "kategori": "Burs",
        "ders": "Matematik I",
        "dosya": (io.BytesIO(BELGE_METNI.encode("utf-8")), "burs.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    belge = paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id)[0]

    yanit = istemci.post(
        f"/belgelerim/{belge.kaynak_id}/gorunurluk",
        data={"gorunurluk": "PAYLASILAN", "ders": "Matematik I"},
        follow_redirects=True,
    )
    assert yanit.status_code == 200
    assert paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id)[0].gorunurluk == Gorunurluk.PAYLASILAN

    ders = paket.ders_deposu.adIleBul("Matematik I")
    yanit = istemci.get(f"/belgelerim?sekme=ders&ders_id={ders.ders_id}")
    assert "Burs Yönergesi" in yanit.get_data(as_text=True)


def test_dogrulanmamis_anasayfaya_erisemez(ortam):
    istemci, paket = ortam
    dogrulanmis_ogrenci(paket, dogrulanmis=False)
    giris_yap(istemci)
    yanit = istemci.get("/sohbet")
    assert yanit.status_code == 302
    assert yanit.headers["Location"].endswith("/dogrulama-bekliyor")


def test_dogrulanmamis_url_ile_erezami_yapar(ortam):
    istemci, paket = ortam
    dogrulanmis_ogrenci(paket, dogrulanmis=False)
    giris_yap(istemci)
    yollar = [
        ("/belgelerim", "GET"),
        ("/sohbet/yanit", "POST"),
        ("/kaynak/1", "GET"),
        ("/gecmis", "GET"),
    ]
    for yol, yontem in yollar:
        yanit = istemci.post(yol) if yontem == "POST" else istemci.get(yol)
        assert yanit.status_code == 302, yol
        assert yanit.headers["Location"].endswith("/dogrulama-bekliyor"), yol


def test_dogrulanmis_erisir(ortam):
    istemci, paket = ortam
    dogrulanmis_ogrenci(paket, dogrulanmis=False)
    giris_yap(istemci)
    ogr = paket.kimlik.kullanici_deposu.epostaIleBul("ali@universite.edu.tr")
    ogr.epostaDogrula()
    paket.kimlik.kullanici_deposu.kaydet(ogr)
    yanit = istemci.get("/sohbet")
    assert yanit.status_code == 200


def test_dogrulama_bekliyor_sayfasi(ortam):
    istemci, paket = ortam
    dogrulanmis_ogrenci(paket, dogrulanmis=False)
    giris_yap(istemci)
    yanit = istemci.get("/dogrulama-bekliyor")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "doğrulama" in metin.lower()
    assert "/dogrulama/yeniden" in metin


def test_yonetici_muaf(ortam):
    istemci, paket = ortam
    from uniasist.entity import Kullanici
    from uniasist.enumlar import Rol
    from uniasist.guvenlik import sifre_hashle

    yonetici = Kullanici(
        ad_soyad="Yönetici",
        eposta="y@universite.edu.tr",
        sifre_hash=sifre_hashle("Yonetici1234"),
        rol=Rol.YONETICI,
        eposta_dogrulandi=False,
    )
    paket.kimlik.kullanici_deposu.kaydet(yonetici)
    istemci.post("/giris", data={"eposta": "y@universite.edu.tr", "sifre": "Yonetici1234"})
    yanit = istemci.get("/belgelerim")
    assert yanit.status_code == 200


def test_dogrulama_rotasi_token_ile(ortam):
    from datetime import datetime, timedelta

    istemci, paket = ortam
    ogr = dogrulanmis_ogrenci(paket, dogrulanmis=False)
    ogr.dogrulamaTokenAta("test-token", datetime.now() + timedelta(hours=1))
    paket.kimlik.kullanici_deposu.kaydet(ogr)
    giris_yap(istemci)
    yanit = istemci.get("/sohbet")
    assert yanit.status_code == 302
    assert yanit.headers["Location"].endswith("/dogrulama-bekliyor")

    yanit = istemci.get("/dogrula/test-token")
    assert yanit.status_code == 200
    assert paket.kimlik.kullanici_deposu.idIleBul(ogr.kullanici_id).dogrulanmisMi()
    assert istemci.get("/sohbet").status_code == 200


def test_dogrulama_gecersiz_token_hata(ortam):
    istemci, _ = ortam
    yanit = istemci.get("/dogrula/gecersiz-token")
    assert yanit.status_code == 200
    assert "geçersiz" in yanit.get_data(as_text=True).lower()


def test_kayit_ekrani_bolum_listesi(ortam):
    istemci, _ = ortam
    yanit = istemci.get("/kayit")
    metin = yanit.get_data(as_text=True)
    assert "Bilgisayar Mühendisliği" in metin
    assert "Hukuk" in metin


def test_bolum_belgesi_bildir(ortam):
    istemci, paket = ortam
    ogr = dogrulanmis_ogrenci(paket, pro=True)
    giris_yap(istemci)
    istemci.post("/belgelerim/yukle", data={
        "baslik": "Staj Yönergesi",
        "kategori": "Staj",
        "ders": "Staj Dersi",
        "dosya": (io.BytesIO(STAJ_METNI.encode("utf-8")), "staj.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    belge = paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id)[0]
    istemci.post(
        f"/belgelerim/{belge.kaynak_id}/gorunurluk",
        data={"gorunurluk": "PAYLASILAN", "ders": "Staj Dersi"},
    )

    baska = dogrulanmis_ogrenci(paket, eposta="baska@universite.edu.tr")
    paket.ders_deposu.takipEt(baska.kullanici_id, belge.ders_id)
    giris_yap(istemci, eposta="baska@universite.edu.tr")
    yanit = istemci.post(
        f"/belgelerim/{belge.kaynak_id}/bildir",
        data={"neden": "Uygunsuz içerik"},
        follow_redirects=True,
    )
    assert yanit.status_code == 200
    aciklar = paket.moderasyon.acikBildirimler()
    assert len(aciklar) == 1
    assert aciklar[0][0].bildiren_id == baska.kullanici_id
    assert aciklar[0][0].belge_id == belge.kaynak_id


def test_bolum_paylasilanina_kaynak_baglantisi(ortam):
    istemci, paket = ortam
    ogr = dogrulanmis_ogrenci(paket, pro=True)
    giris_yap(istemci)
    istemci.post("/belgelerim/yukle", data={
        "baslik": "Burs Yönergesi",
        "kategori": "Burs",
        "ders": "Matematik I",
        "dosya": (io.BytesIO(BELGE_METNI.encode("utf-8")), "burs.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    belge = paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id)[0]
    istemci.post(
        f"/belgelerim/{belge.kaynak_id}/gorunurluk",
        data={"gorunurluk": "PAYLASILAN", "ders": "Matematik I"},
    )

    baska = dogrulanmis_ogrenci(paket, eposta="baska@universite.edu.tr")
    paket.ders_deposu.takipEt(baska.kullanici_id, belge.ders_id)
    giris_yap(istemci, eposta="baska@universite.edu.tr")
    yanit = istemci.get(f"/belgelerim?sekme=ders&ders_id={belge.ders_id}")
    assert f'href="/kaynak/{belge.kaynak_id}"' in yanit.get_data(as_text=True)

    yanit = istemci.get(f"/kaynak/{belge.kaynak_id}")
    assert yanit.status_code == 200
    assert "Burs Yönergesi" in yanit.get_data(as_text=True)


def test_asiri_buyuk_yukleme_413(ortam):
    istemci, paket = ortam
    ogr = dogrulanmis_ogrenci(paket)
    giris_yap(istemci)
    icerik = b"x" * (config.AZAMI_BELGE_BOYUTU + 2 * 1024 * 1024)
    yanit = istemci.post("/belgelerim/yukle", data={
        "baslik": "Devasa Belge",
        "kategori": "Staj",
        "dosya": (io.BytesIO(icerik), "devasa.txt"),
    }, content_type="multipart/form-data")
    assert yanit.status_code == 413
    assert paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id) == []


def test_reddedilen_yukleme_artik_dosya_birakmaz(ortam):
    import os

    istemci, paket = ortam
    ogr = dogrulanmis_ogrenci(paket)
    giris_yap(istemci)
    icerik = b"x" * (config.AZAMI_BELGE_BOYUTU + 512 * 1024)
    yanit = istemci.post("/belgelerim/yukle", data={
        "baslik": "Büyük Belge",
        "kategori": "Staj",
        "dosya": (io.BytesIO(icerik), "buyuk.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert yanit.status_code == 200
    assert "Belge yüklenemedi" in yanit.get_data(as_text=True)
    assert paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id) == []
    assert os.listdir(config.DOSYA_KLASORU) == []
