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
                        bolum="Bilgisayar Mühendisliği", dogrulanmis=True):
    from uniasist.entity import Kullanici
    from uniasist.enumlar import Rol
    from uniasist.guvenlik import sifre_hashle

    k = Kullanici(
        ad_soyad="Ali Veli",
        eposta=eposta,
        sifre_hash=sifre_hashle("Gizli1234"),
        rol=Rol.OGRENCI,
        universite_id=1,
        bolum=bolum,
        eposta_dogrulandi=dogrulanmis,
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

    yanit = istemci.get("/belgelerim?sekme=bolum")
    bolum_metni = yanit.get_data(as_text=True)
    assert "Burs Yönergesi" not in bolum_metni

    belgeler = paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id)
    assert len(belgeler) == 1
    assert belgeler[0].gorunurluk == Gorunurluk.OZEL


def test_ogrenci_paylasir_bolum_gorur(ortam):
    istemci, paket = ortam
    ogr = dogrulanmis_ogrenci(paket)
    giris_yap(istemci)
    istemci.post("/belgelerim/yukle", data={
        "baslik": "Burs Yönergesi",
        "kategori": "Burs",
        "dosya": (io.BytesIO(BELGE_METNI.encode("utf-8")), "burs.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    belge = paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id)[0]

    yanit = istemci.post(
        f"/belgelerim/{belge.kaynak_id}/gorunurluk",
        data={"gorunurluk": "PAYLASILAN"},
        follow_redirects=True,
    )
    assert yanit.status_code == 200
    assert paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id)[0].gorunurluk == Gorunurluk.PAYLASILAN

    yanit = istemci.get("/belgelerim?sekme=bolum")
    assert "Burs Yönergesi" in yanit.get_data(as_text=True)


def test_dogrulanmamis_paylas_hata(ortam):
    istemci, paket = ortam
    ogr = dogrulanmis_ogrenci(paket, dogrulanmis=False)
    giris_yap(istemci)

    yanit = istemci.get("/")
    assert "doğrulayın" in yanit.get_data(as_text=True)

    yanit = istemci.post("/belgelerim/yukle", data={
        "baslik": "Burs Yönergesi",
        "kategori": "Burs",
        "paylas": "1",
        "dosya": (io.BytesIO(BELGE_METNI.encode("utf-8")), "burs.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert "doğrulamanız" in yanit.get_data(as_text=True)
    assert paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id) == []


def test_dogrulama_rotasi_token_ile(ortam):
    from datetime import datetime, timedelta

    istemci, paket = ortam
    ogr = dogrulanmis_ogrenci(paket, dogrulanmis=False)
    ogr.dogrulamaTokenAta("test-token", datetime.now() + timedelta(hours=1))
    paket.kimlik.kullanici_deposu.kaydet(ogr)
    giris_yap(istemci)
    assert "doğrulayın" in istemci.get("/").get_data(as_text=True)

    yanit = istemci.get("/dogrula/test-token")
    assert yanit.status_code == 200
    assert paket.kimlik.kullanici_deposu.idIleBul(ogr.kullanici_id).dogrulanmisMi()
    assert "doğrulayın" not in istemci.get("/").get_data(as_text=True)


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
    ogr = dogrulanmis_ogrenci(paket)
    giris_yap(istemci)
    istemci.post("/belgelerim/yukle", data={
        "baslik": "Staj Yönergesi",
        "kategori": "Staj",
        "dosya": (io.BytesIO(STAJ_METNI.encode("utf-8")), "staj.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    belge = paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id)[0]
    istemci.post(
        f"/belgelerim/{belge.kaynak_id}/gorunurluk",
        data={"gorunurluk": "PAYLASILAN"},
    )

    baska = dogrulanmis_ogrenci(paket, eposta="baska@universite.edu.tr")
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
