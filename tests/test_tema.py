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
        yield istemci


def test_tema_varsayilan_acik(ortam):
    yanit = ortam.get("/giris")
    assert yanit.status_code == 200
    assert 'data-tema="acik"' in yanit.get_data(as_text=True)


def test_tema_cerezden_koyu(ortam):
    ortam.set_cookie("uniasist_tema", "koyu")
    yanit = ortam.get("/giris")
    assert yanit.status_code == 200
    assert 'data-tema="koyu"' in yanit.get_data(as_text=True)


def test_tema_dugme_var(ortam):
    for yol in ("/giris", "/kayit"):
        yanit = ortam.get(yol)
        assert yanit.status_code == 200
        assert 'id="tema-dugme"' in yanit.get_data(as_text=True)
