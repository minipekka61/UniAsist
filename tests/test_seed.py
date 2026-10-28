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


def test_seed_hesaplar_ve_belgeler(paket):
    admin = paket.kimlik.kullanici_deposu.epostaIleBul("admin@universite.edu.tr")
    ogrenci = paket.kimlik.kullanici_deposu.epostaIleBul("ogrenci@universite.edu.tr")
    assert admin is not None and admin.rol.value == "YONETICI"
    assert ogrenci is not None and ogrenci.rol.value == "OGRENCI"
    assert admin.sifreDogrula("Yonetici1234")
    assert ogrenci.sifreDogrula("Ogrenci1234")

    belgeler = paket.bilgi_tabani.belgeleriListele()
    assert len(belgeler) == 14
    assert all(b.aktifMi() for b in belgeler)
    parca_sayisi = paket.db.execute(
        "SELECT COUNT(*) AS n FROM icerik_parcasi"
    ).fetchone()["n"]
    assert parca_sayisi >= 14
    sss_sayisi = paket.db.execute(
        "SELECT COUNT(*) AS n FROM bilgi_kaynagi WHERE tur='SSS'"
    ).fetchone()["n"]
    assert sss_sayisi == 0


def test_seed_idempotent(paket):
    from uniasist import seed

    n_kullanici = paket.db.execute("SELECT COUNT(*) AS n FROM kullanici").fetchone()["n"]
    n_belge = len(paket.bilgi_tabani.belgeleriListele())
    n_sss = paket.db.execute(
        "SELECT COUNT(*) AS n FROM bilgi_kaynagi WHERE tur='SSS'"
    ).fetchone()["n"]

    seed.kos(paket)

    assert paket.db.execute("SELECT COUNT(*) AS n FROM kullanici").fetchone()["n"] == n_kullanici
    assert len(paket.bilgi_tabani.belgeleriListele()) == n_belge
    assert paket.db.execute(
        "SELECT COUNT(*) AS n FROM bilgi_kaynagi WHERE tur='SSS'"
    ).fetchone()["n"] == n_sss


def test_seed_soru_yanitlanabilir(paket):
    paket.sohbet.yanit_uretme_servisi.benzerlik_esigi = config.YEREL_ESIK
    ogrenci = paket.kimlik.kullanici_deposu.epostaIleBul("ogrenci@universite.edu.tr")
    sohbet = paket.sohbet.yeniSohbetBaslat(kullanici=ogrenci)
    mesaj = paket.sohbet.soruSor(sohbet, "Staj başvurusu için en az kaç gün çalışma gerekir?")
    assert "60" in mesaj.metin
    assert len(mesaj.kaynaklariGetir()) >= 1


def test_uygulama_olustur_bos_db_otomatik_seed(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "VERITABANI_YOLU", str(tmp_path / "seed-test.db"))
    uygulama = uygulama_olustur()
    paket = uygulama.extensions["uniasist"]
    assert len(paket.bilgi_tabani.belgeleriListele()) == 14
    assert paket.kimlik.kullanici_deposu.epostaVarMi("admin@universite.edu.tr")
