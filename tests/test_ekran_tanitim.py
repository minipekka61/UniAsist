import pytest

from tests.yardimci import SahteYZ, gecici_db
from uniasist.kurulum import kur
from uniasist.uygulama import uygulama_olustur


@pytest.fixture
def ortam():
    paket = kur(db=gecici_db(), yapay_zeka=SahteYZ())
    uygulama = uygulama_olustur(paket)
    uygulama.config["TESTING"] = True
    with uygulama.test_client() as istemci:
        yield istemci, paket


def _dogrulanmis_ogrenci(paket, eposta="ali@universite.edu.tr"):
    from uniasist.entity import Kullanici
    from uniasist.enumlar import Rol
    from uniasist.guvenlik import sifre_hashle

    k = Kullanici(
        ad_soyad="Ali Veli",
        eposta=eposta,
        sifre_hash=sifre_hashle("Gizli1234"),
        rol=Rol.OGRENCI,
        eposta_dogrulandi=True,
    )
    paket.kimlik.kullanici_deposu.kaydet(k)
    return k


def test_kayitsiz_anasayfa_tanitim(ortam):
    istemci, _ = ortam
    yanit = istemci.get("/")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "UniAsist" in metin
    assert "Ücretsiz" in metin
    assert "Pro" in metin
    assert 'href="/kayit"' in metin
    assert 'href="/giris"' in metin


def test_girisli_anasayfa_sohbete_yonlenir(ortam):
    istemci, paket = ortam
    _dogrulanmis_ogrenci(paket)
    istemci.post("/giris", data={"eposta": "ali@universite.edu.tr", "sifre": "Gizli1234"})

    yanit = istemci.get("/")
    assert yanit.status_code == 302
    assert yanit.headers["Location"].endswith("/sohbet")


def test_giris_sonrasi_sohbete(ortam):
    istemci, paket = ortam
    _dogrulanmis_ogrenci(paket)
    yanit = istemci.post(
        "/giris", data={"eposta": "ali@universite.edu.tr", "sifre": "Gizli1234"}
    )
    assert yanit.status_code == 302
    assert yanit.headers["Location"].endswith("/sohbet")
