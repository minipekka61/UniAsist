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
    ali = _ogrenci(paket, "ali@universite.edu.tr")
    ayse = _ogrenci(paket, "ayse@universite.edu.tr")
    assert admin is not None and admin.rol.value == "YONETICI"
    assert ali is not None and ali.rol.value == "OGRENCI"
    assert ayse is not None and ayse.rol.value == "OGRENCI"
    assert admin.sifreDogrula("Yonetici1234")
    assert ali.sifreDogrula("Ogrenci1234")
    assert ayse.sifreDogrula("Ogrenci1234")
    assert ali.proMu()
    assert not ayse.proMu()
    assert ali.dogrulanmisMi() and ayse.dogrulanmisMi()

    ali_belgeleri = paket.bilgi_tabani.belgeleriListele(ali.kullanici_id)
    ayse_belgeleri = paket.bilgi_tabani.belgeleriListele(ayse.kullanici_id)
    assert len(ali_belgeleri) == 14
    assert len(ayse_belgeleri) == 2
    assert all(b.aktifMi() for b in ali_belgeleri + ayse_belgeleri)
    from uniasist.enumlar import Gorunurluk

    assert any(b.gorunurluk == Gorunurluk.OZEL for b in ali_belgeleri)
    assert any(b.gorunurluk == Gorunurluk.PAYLASILAN for b in ali_belgeleri)
    assert all(b.gorunurluk == Gorunurluk.OZEL for b in ayse_belgeleri)

    parca_sayisi = paket.db.execute(
        "SELECT COUNT(*) AS n FROM icerik_parcasi"
    ).fetchone()["n"]
    assert parca_sayisi >= 16


def test_seed_dersler_ve_takipler(paket):
    ali = _ogrenci(paket, "ali@universite.edu.tr")
    ayse = _ogrenci(paket, "ayse@universite.edu.tr")

    matematik = paket.ders_deposu.adIleBul("Matematik I")
    fizik = paket.ders_deposu.adIleBul("Fizik I")
    assert matematik is not None
    assert fizik is not None

    burs = next(
        b for b in paket.bilgi_tabani.belgeleriListele(ali.kullanici_id)
        if b.baslik == "Burs Yönergesi"
    )
    staj = next(
        b for b in paket.bilgi_tabani.belgeleriListele(ali.kullanici_id)
        if b.baslik == "Staj Yönergesi"
    )
    assert burs.ders_id == matematik.ders_id
    assert staj.ders_id == fizik.ders_id

    matematik_paylasilanlari = paket.bilgi_tabani.dersinPaylasilanlari(matematik.ders_id)
    fizik_paylasilanlari = paket.bilgi_tabani.dersinPaylasilanlari(fizik.ders_id)
    assert burs.kaynak_id in [b.kaynak_id for b in matematik_paylasilanlari]
    assert staj.kaynak_id in [b.kaynak_id for b in fizik_paylasilanlari]
    assert all(b.sahip_id == ali.kullanici_id for b in matematik_paylasilanlari + fizik_paylasilanlari)

    assert paket.ders_deposu.takipteMi(ayse.kullanici_id, matematik.ders_id)
    assert paket.ders_deposu.takipteMi(ayse.kullanici_id, fizik.ders_id)
    assert not paket.ders_deposu.takipteMi(ali.kullanici_id, matematik.ders_id)


def test_seed_idempotent(paket):
    from uniasist import seed

    ali = _ogrenci(paket, "ali@universite.edu.tr")
    ayse = _ogrenci(paket, "ayse@universite.edu.tr")
    n_kullanici = paket.db.execute("SELECT COUNT(*) AS n FROM kullanici").fetchone()["n"]
    n_belge = len(paket.bilgi_tabani.belgeleriListele(ali.kullanici_id)) + len(
        paket.bilgi_tabani.belgeleriListele(ayse.kullanici_id)
    )
    n_ders = len(paket.ders_deposu.hepsiniListele())

    seed.kos(paket)

    assert paket.db.execute("SELECT COUNT(*) AS n FROM kullanici").fetchone()["n"] == n_kullanici
    assert (
        len(paket.bilgi_tabani.belgeleriListele(ali.kullanici_id))
        + len(paket.bilgi_tabani.belgeleriListele(ayse.kullanici_id))
        == n_belge
    )
    assert len(paket.ders_deposu.hepsiniListele()) == n_ders


def test_seed_soru_yanitlanabilir(paket):
    paket.sohbet.yanit_uretme_servisi.benzerlik_esigi = config.YEREL_ESIK
    ali = _ogrenci(paket, "ali@universite.edu.tr")
    sohbet = paket.sohbet.yeniSohbetBaslat(kullanici=ali)
    mesaj = paket.sohbet.soruSor(sohbet, "Staj başvurusu için en az kaç gün çalışma gerekir?")
    assert "60" in mesaj.metin
    assert len(mesaj.kaynaklariGetir()) >= 1


def test_uygulama_olustur_bos_db_otomatik_seed(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "VERITABANI_YOLU", str(tmp_path / "seed-test.db"))
    uygulama = uygulama_olustur()
    paket = uygulama.extensions["uniasist"]
    ali = _ogrenci(paket, "ali@universite.edu.tr")
    assert len(paket.bilgi_tabani.belgeleriListele(ali.kullanici_id)) == 14
    assert paket.kimlik.kullanici_deposu.epostaVarMi("admin@universite.edu.tr")
    assert paket.kimlik.kullanici_deposu.epostaVarMi("ayse@universite.edu.tr")
