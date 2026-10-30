import pytest

from tests.yardimci import SahteYZ, gecici_db
from uniasist.enumlar import Rol
from uniasist.kurulum import kur
from uniasist.uygulama import uygulama_olustur


@pytest.fixture
def paket():
    return kur(db=gecici_db(), yapay_zeka=SahteYZ())


@pytest.fixture
def istemci(paket):
    uygulama = uygulama_olustur(paket)

    from flask import g

    from uniasist.ekran.yardimcilar import giris_required

    @uygulama.route("/korunan-yonetici")
    @giris_required([Rol.YONETICI])
    def korunan():
        return "gizli"

    uygulama.config["TESTING"] = True
    with uygulama.test_client() as istemci:
        yield istemci


def test_uc01_kayit_basarili_ve_alan_adi_hatasi(istemci):
    yanit = istemci.post("/kayit", data={
        "ad_soyad": "Ali Veli",
        "eposta": "ali@gmail.com",
        "sifre": "Gizli1234",
        "sifre_tekrar": "Gizli1234",
    })
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "öğrenci e-posta" in metin

    yanit = istemci.post("/kayit", data={
        "ad_soyad": "Ali Veli",
        "eposta": "ali@universite.edu.tr",
        "sifre": "Gizli1234",
        "sifre_tekrar": "Gizli1234",
    }, follow_redirects=True)
    assert yanit.status_code == 200
    assert "Giriş" in yanit.get_data(as_text=True)


def test_uc02_giris_ve_role_gore_yonlendirme(istemci, paket):
    paket.kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234")
    yanit = istemci.post("/giris", data={"eposta": "ali@universite.edu.tr", "sifre": "Gizli1234"})
    assert yanit.status_code == 302
    assert yanit.headers["Location"].endswith("/sohbet")

    from uniasist.entity import Kullanici
    from uniasist.guvenlik import sifre_hashle

    yonetici = Kullanici(ad_soyad="Y", eposta="y@universite.edu.tr", sifre_hash=sifre_hashle("Yonetici1234"), rol=Rol.YONETICI)
    paket.kimlik.kullanici_deposu.kaydet(yonetici)
    yanit = istemci.post("/giris", data={"eposta": "y@universite.edu.tr", "sifre": "Yonetici1234"})
    assert yanit.status_code == 302
    assert yanit.headers["Location"].endswith("/sohbet")


def test_uc02_hatali_giris_mesaji(istemci, paket):
    paket.kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234")
    yanit = istemci.post("/giris", data={"eposta": "ali@universite.edu.tr", "sifre": "yanlis"})
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "E-posta veya şifre hatalı" in metin


def test_uc03_cikis_sonrasi_korumali_sayfa(istemci, paket):
    paket.kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234")
    istemci.post("/giris", data={"eposta": "ali@universite.edu.tr", "sifre": "Gizli1234"})
    yanit = istemci.get("/cikis")
    assert yanit.status_code == 302
    yanit = istemci.get("/profil")
    assert yanit.status_code == 302
    assert "/giris" in yanit.headers["Location"]


def test_uc04_sifre_degistirme(istemci, paket):
    k = paket.kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234")
    istemci.post("/giris", data={"eposta": "ali@universite.edu.tr", "sifre": "Gizli1234"})
    yanit = istemci.post("/profil/sifre", data={
        "mevcut_sifre": "yanlis", "yeni_sifre": "Yeni1234", "yeni_sifre_tekrar": "Yeni1234",
    })
    assert "hatalı" in yanit.get_data(as_text=True)

    yanit = istemci.post("/profil/sifre", data={
        "mevcut_sifre": "Gizli1234", "yeni_sifre": "Yeni12345", "yeni_sifre_tekrar": "Yeni12345",
    }, follow_redirects=True)
    assert yanit.status_code == 200
    assert paket.kimlik.oturumDogrula is not None


def test_ik08_gecersiz_cerez_girise_yonlendirir(istemci):
    istemci.set_cookie("uniasist_oturum", "uydurma-token")
    yanit = istemci.get("/profil")
    assert yanit.status_code == 302
    assert "/giris" in yanit.headers["Location"]


def test_nfr03_ogrenci_yonetim_sayfasina_ulasamaz(istemci, paket):
    paket.kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234")
    istemci.post("/giris", data={"eposta": "ali@universite.edu.tr", "sifre": "Gizli1234"})
    yanit = istemci.get("/korunan-yonetici")
    assert yanit.status_code == 403


def test_kayitsiz_ana_sayfa_girise_yonlendirir(istemci):
    yanit = istemci.get("/sohbet")
    assert yanit.status_code == 302
    assert "/giris" in yanit.headers["Location"]
