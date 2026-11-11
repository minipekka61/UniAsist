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


def _dogrulanmis_kullanici(paket):
    from uniasist.entity import Kullanici
    from uniasist.enumlar import Rol
    from uniasist.guvenlik import sifre_hashle

    ogrenci = Kullanici(
        ad_soyad="Ali Veli",
        eposta="ali@universite.edu.tr",
        sifre_hash=sifre_hashle("Gizli1234"),
        rol=Rol.OGRENCI,
        universite="Üniversite",
        bolum="Bilgisayar Mühendisliği",
        eposta_dogrulandi=True,
    )
    paket.kimlik.kullanici_deposu.kaydet(ogrenci)


def _giris_yap(istemci):
    metin = istemci.get("/giris").get_data(as_text=True)
    eslesme = re.search(r'name="csrf_token" value="([^"]+)"', metin)
    assert eslesme, "giris formunda gizli csrf_token yok"
    yanit = istemci.post(
        "/giris",
        data={
            "eposta": "ali@universite.edu.tr",
            "sifre": "Gizli1234",
            "csrf_token": eslesme.group(1),
        },
    )
    assert yanit.status_code == 302
    assert yanit.headers["Location"].endswith("/sohbet")
    return yanit


def test_giris_formunda_gizli_token(istemci, paket):
    _dogrulanmis_kullanici(paket)
    yanit = _giris_yap(istemci)
    assert yanit.headers["Location"].endswith("/sohbet")


def test_yanit_rotasi_baslik_tokeni_ile_calisir(istemci, paket):
    _dogrulanmis_kullanici(paket)
    _giris_yap(istemci)
    token = _token_al(istemci, "/sohbet")
    yanit = istemci.post(
        "/sohbet/yanit",
        data={"soru": "Burs başvurusu ne zaman yapılır?"},
        headers={"X-CSRFToken": token},
    )
    assert yanit.status_code == 200


def test_geri_bildirim_json_rotasi_korumali(istemci, paket):
    _dogrulanmis_kullanici(paket)
    _giris_yap(istemci)
    token = _token_al(istemci, "/sohbet")
    yanit = istemci.post(
        "/geri-bildirim", json={"mesaj_id": 999999, "tur": "YARARLI"}
    )
    assert yanit.status_code == 400
    assert yanit.get_json(silent=True) is None  # CSRF 400'ü — view çalışmadı
    yanit = istemci.post(
        "/geri-bildirim",
        json={"mesaj_id": 999999, "tur": "YARARLI"},
        headers={"X-CSRFToken": token},
    )
    veri = yanit.get_json(silent=True)
    assert veri is not None and veri["ok"] is False  # view çalıştı, mesaj yok


def test_cikis_post_ile_yapilir(istemci, paket):
    _dogrulanmis_kullanici(paket)
    _giris_yap(istemci)
    token = _token_al(istemci, "/sohbet")
    yanit = istemci.post("/cikis", headers={"X-CSRFToken": token})
    assert yanit.status_code == 302
    assert yanit.headers["Location"].endswith("/giris")


def test_cikis_get_405_doner(istemci):
    assert istemci.get("/cikis").status_code == 405


def test_oturum_cerezi_samesite_lax(istemci, paket):
    _dogrulanmis_kullanici(paket)
    yanit = _giris_yap(istemci)  # giriş yanıtını döndürür
    set_cerez = yanit.headers.get("Set-Cookie", "")
    assert "uniasist_oturum" in set_cerez
    assert "SameSite=Lax" in set_cerez


def test_session_cerezi_samesite_lax(istemci):
    yanit = istemci.get("/giris")
    set_cerez = yanit.headers.get("Set-Cookie", "")
    assert "session" in set_cerez
    assert "SameSite=Lax" in set_cerez
