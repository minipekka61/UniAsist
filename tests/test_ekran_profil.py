import pytest

from tests.yardimci import SahteYZ, gecici_db
from uniasist.kurulum import kur
from uniasist.uygulama import uygulama_olustur


@pytest.fixture
def paket():
    return kur(db=gecici_db(), yapay_zeka=SahteYZ())


@pytest.fixture
def ortam(paket):
    uygulama = uygulama_olustur(paket)
    uygulama.config["TESTING"] = True
    with uygulama.test_client() as istemci:
        yield istemci, paket


def _ogrenci(paket, eposta="ali@universite.edu.tr"):
    from uniasist.entity import Kullanici
    from uniasist.enumlar import Rol
    from uniasist.guvenlik import sifre_hashle

    k = Kullanici(
        ad_soyad="Ali Veli",
        eposta=eposta,
        sifre_hash=sifre_hashle("Gizli1234"),
        rol=Rol.OGRENCI,
        universite="İstanbul Üniversitesi",
        bolum="Bilgisayar Mühendisliği",
        eposta_dogrulandi=True,
    )
    paket.kimlik.kullanici_deposu.kaydet(k)
    return k


def _giris_yap(istemci, eposta="ali@universite.edu.tr"):
    istemci.post("/giris", data={"eposta": eposta, "sifre": "Gizli1234"})


def test_profil_bilgileri_gorunur(ortam):
    istemci, paket = ortam
    ogr = _ogrenci(paket)
    _giris_yap(istemci)

    yanit = istemci.get("/profil")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "Ali Veli" in metin
    assert "ali@universite.edu.tr" in metin
    assert "İstanbul Üniversitesi" in metin
    assert "Bilgisayar Mühendisliği" in metin
    assert "Ücretsiz" in metin
    assert "Doğrulanmış" in metin


def test_profil_guncelleme(ortam):
    istemci, paket = ortam
    ogr = _ogrenci(paket)
    _giris_yap(istemci)

    yanit = istemci.post("/profil", data={
        "ad_soyad": "Ali Veli Güncel",
        "universite": "Boğaziçi Üniversitesi",
        "bolum": "Fizik",
    }, follow_redirects=True)
    assert yanit.status_code == 200
    okunan = paket.kimlik.kullanici_deposu.idIleBul(ogr.kullanici_id)
    assert okunan.ad_soyad == "Ali Veli Güncel"
    assert okunan.universite == "Boğaziçi Üniversitesi"
    assert okunan.bolum == "Fizik"

    yanit = istemci.post("/profil", data={
        "ad_soyad": "",
        "universite": "",
        "bolum": "",
    }, follow_redirects=True)
    assert yanit.status_code == 200
    assert "Ad soyad zorunludur" in yanit.get_data(as_text=True)


def test_profil_sifre_degistirme(ortam):
    istemci, paket = ortam
    ogr = _ogrenci(paket)
    _giris_yap(istemci)

    yanit = istemci.post("/profil/sifre", data={
        "mevcut_sifre": "yanlis",
        "yeni_sifre": "Yeni12345",
        "yeni_sifre_tekrar": "Yeni12345",
    }, follow_redirects=True)
    assert yanit.status_code == 200
    assert "hatalı" in yanit.get_data(as_text=True)

    yanit = istemci.post("/profil/sifre", data={
        "mevcut_sifre": "Gizli1234",
        "yeni_sifre": "Yeni12345",
        "yeni_sifre_tekrar": "Yeni12345",
    }, follow_redirects=True)
    assert yanit.status_code == 200

    istemci.get("/cikis")
    yanit = istemci.post("/giris", data={
        "eposta": "ali@universite.edu.tr", "sifre": "Yeni12345",
    })
    assert yanit.status_code == 302


def test_eski_sifre_rotasi_yok(ortam):
    istemci, paket = ortam
    _ogrenci(paket)
    _giris_yap(istemci)
    yanit = istemci.get("/sifre-degistir")
    assert yanit.status_code == 404
