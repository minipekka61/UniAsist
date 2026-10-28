import pytest

import config
from tests.yardimci import SahteYZ, gecici_db
from uniasist.kurulum import kur
from uniasist.uygulama import uygulama_olustur


@pytest.fixture
def paket():
    from uniasist import seed

    paket = kur(db=gecici_db(), yapay_zeka=SahteYZ())
    seed.kos(paket)
    return paket


def _ogrenci(paket, eposta):
    return paket.kimlik.kullanici_deposu.epostaIleBul(eposta)


def test_seed_hesaplar_ve_belgeler(paket):
    admin = _ogrenci(paket, "admin@universite.edu.tr")
    bilgisayar = _ogrenci(paket, "bilgisayar@universite.edu.tr")
    elektrik = _ogrenci(paket, "elektrik@universite.edu.tr")
    assert admin is not None and admin.rol.value == "YONETICI"
    assert bilgisayar is not None and bilgisayar.rol.value == "OGRENCI"
    assert elektrik is not None and elektrik.rol.value == "OGRENCI"
    assert admin.sifreDogrula("Yonetici1234")
    assert bilgisayar.sifreDogrula("Ogrenci1234")
    assert elektrik.sifreDogrula("Ogrenci1234")
    assert bilgisayar.bolum == "Bilgisayar Mühendisliği"
    assert elektrik.bolum == "Elektrik-Elektronik Mühendisliği"
    assert bilgisayar.universite_id == elektrik.universite_id
    assert bilgisayar.dogrulanmisMi() and elektrik.dogrulanmisMi()

    bilgisayar_belgeleri = paket.bilgi_tabani.belgeleriListele(bilgisayar.kullanici_id)
    elektrik_belgeleri = paket.bilgi_tabani.belgeleriListele(elektrik.kullanici_id)
    assert len(bilgisayar_belgeleri) == 14
    assert len(elektrik_belgeleri) == 2
    assert all(b.aktifMi() for b in bilgisayar_belgeleri + elektrik_belgeleri)
    from uniasist.enumlar import Gorunurluk

    assert any(b.gorunurluk == Gorunurluk.OZEL for b in bilgisayar_belgeleri)
    assert any(b.gorunurluk == Gorunurluk.PAYLASILAN for b in bilgisayar_belgeleri)
    assert any(b.gorunurluk == Gorunurluk.OZEL for b in elektrik_belgeleri)
    assert any(b.gorunurluk == Gorunurluk.PAYLASILAN for b in elektrik_belgeleri)

    parca_sayisi = paket.db.execute(
        "SELECT COUNT(*) AS n FROM icerik_parcasi"
    ).fetchone()["n"]
    assert parca_sayisi >= 16

    universite_id = bilgisayar.universite_id
    bilgisayar_paylasilanlari = paket.bilgi_tabani.bolumunPaylasilanlari(
        universite_id, "Bilgisayar Mühendisliği"
    )
    elektrik_paylasilanlari = paket.bilgi_tabani.bolumunPaylasilanlari(
        universite_id, "Elektrik-Elektronik Mühendisliği"
    )
    assert all(b.sahip_id == bilgisayar.kullanici_id for b in bilgisayar_paylasilanlari)
    assert len(bilgisayar_paylasilanlari) >= 1
    assert all(b.sahip_id == elektrik.kullanici_id for b in elektrik_paylasilanlari)
    assert len(elektrik_paylasilanlari) >= 1


def test_seed_idempotent(paket):
    from uniasist import seed

    bilgisayar = _ogrenci(paket, "bilgisayar@universite.edu.tr")
    elektrik = _ogrenci(paket, "elektrik@universite.edu.tr")
    n_kullanici = paket.db.execute("SELECT COUNT(*) AS n FROM kullanici").fetchone()["n"]
    n_belge = len(paket.bilgi_tabani.belgeleriListele(bilgisayar.kullanici_id)) + len(
        paket.bilgi_tabani.belgeleriListele(elektrik.kullanici_id)
    )

    seed.kos(paket)

    assert paket.db.execute("SELECT COUNT(*) AS n FROM kullanici").fetchone()["n"] == n_kullanici
    assert (
        len(paket.bilgi_tabani.belgeleriListele(bilgisayar.kullanici_id))
        + len(paket.bilgi_tabani.belgeleriListele(elektrik.kullanici_id))
        == n_belge
    )


def test_seed_soru_yanitlanabilir(paket):
    paket.sohbet.yanit_uretme_servisi.benzerlik_esigi = config.YEREL_ESIK
    bilgisayar = _ogrenci(paket, "bilgisayar@universite.edu.tr")
    sohbet = paket.sohbet.yeniSohbetBaslat(kullanici=bilgisayar)
    mesaj = paket.sohbet.soruSor(sohbet, "Staj başvurusu için en az kaç gün çalışma gerekir?")
    assert "60" in mesaj.metin
    assert len(mesaj.kaynaklariGetir()) >= 1


def test_uygulama_olustur_bos_db_otomatik_seed(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "VERITABANI_YOLU", str(tmp_path / "seed-test.db"))
    uygulama = uygulama_olustur()
    paket = uygulama.extensions["uniasist"]
    bilgisayar = _ogrenci(paket, "bilgisayar@universite.edu.tr")
    assert len(paket.bilgi_tabani.belgeleriListele(bilgisayar.kullanici_id)) == 14
    assert paket.kimlik.kullanici_deposu.epostaVarMi("admin@universite.edu.tr")
