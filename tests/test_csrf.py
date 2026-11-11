import re

import pytest

from tests.yardimci import SahteYZ, gecici_db
from uniasist.kurulum import kur
from uniasist.uygulama import uygulama_olustur


@pytest.fixture
def paket():
    return kur(db=gecici_db(), yapay_zeka=SahteYZ())


@pytest.fixture
def istemci(paket):
    uygulama = uygulama_olustur(paket)
    uygulama.config["TESTING"] = True
    # WTF_CSRF_ENABLED ayarlanmaz — bu uygulamada CSRF AÇIK kalır
    with uygulama.test_client() as istemci:
        yield istemci


def _token_al(istemci, yol="/giris"):
    metin = istemci.get(yol).get_data(as_text=True)
    eslesme = re.search(r'<meta name="csrf-token" content="([^"]+)"', metin)
    assert eslesme, "csrf meta etiketi bulunamadı"
    return eslesme.group(1)


def test_tokensiz_post_400_doner(istemci):
    yanit = istemci.post(
        "/giris", data={"eposta": "a@universite.edu.tr", "sifre": "Yanlis1234"}
    )
    assert yanit.status_code == 400


def test_gecersiz_token_400_doner(istemci):
    yanit = istemci.post(
        "/giris",
        data={
            "eposta": "a@universite.edu.tr",
            "sifre": "Yanlis1234",
            "csrf_token": "sahte-deger",
        },
    )
    assert yanit.status_code == 400


def test_form_tokenu_kabul_edilir(istemci):
    token = _token_al(istemci)
    yanit = istemci.post(
        "/giris",
        data={
            "eposta": "a@universite.edu.tr",
            "sifre": "Yanlis1234",
            "csrf_token": token,
        },
    )
    assert yanit.status_code == 200
    assert "E-posta veya şifre hatalı" in yanit.get_data(as_text=True)


def test_baslik_tokenu_kabul_edilir(istemci):
    token = _token_al(istemci)
    yanit = istemci.post(
        "/giris",
        data={"eposta": "a@universite.edu.tr", "sifre": "Yanlis1234"},
        headers={"X-CSRFToken": token},
    )
    assert yanit.status_code == 200
    assert "E-posta veya şifre hatalı" in yanit.get_data(as_text=True)


def test_get_istekleri_etkilenmez(istemci):
    assert istemci.get("/giris").status_code == 200


def test_meta_etiketi_token_tasir(istemci):
    metin = istemci.get("/giris").get_data(as_text=True)
    assert '<meta name="csrf-token"' in metin
