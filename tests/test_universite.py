import pytest

from tests.yardimci import gecici_db
from uniasist.depo.universite_deposu import UniversiteDeposu
from uniasist.entity import Universite
from uniasist.veri.bolumler import BOLUMLER
from uniasist.veri.universiteler import UNIVERSITELER


@pytest.fixture
def depo():
    d = UniversiteDeposu(gecici_db())
    d.kaydet(Universite(ad="İstanbul Üniversitesi", eposta_alan_adi="istanbul.edu.tr"))
    d.kaydet(Universite(ad="ODTÜ", eposta_alan_adi="metu.edu.tr"))
    return d


def test_alan_adi_son_ek_eslesmesi(depo):
    u = depo.alanAdindanBul("ayse@ogrenci.istanbul.edu.tr")
    assert u is not None and u.ad == "İstanbul Üniversitesi"
    u2 = depo.alanAdindanBul("ali@istanbul.edu.tr")
    assert u2 is not None and u2.universite_id == u.universite_id
    u3 = depo.alanAdindanBul("ali@METU.EDU.TR")
    assert u3 is not None and u3.ad == "ODTÜ"
    assert len(depo.hepsiniListele()) == 2
    assert depo.idIleBul(u.universite_id).eposta_alan_adi == "istanbul.edu.tr"


def test_alan_adi_bilinmeyen_none_doner(depo):
    assert depo.alanAdindanBul("ali@gmail.com") is None
    assert depo.alanAdindanBul("ali@xistanbul.edu.tr") is None
    assert depo.alanAdindanBul("gecersiz") is None
    assert depo.alanAdindanBul("") is None
    assert depo.alanAdindanBul(None) is None


def test_bolum_ekle_ve_listele():
    d = UniversiteDeposu(gecici_db())
    assert d.bolumleriListele() == []
    d.bolumEkle("Bilgisayar Mühendisliği")
    d.bolumEkle("Hukuk")
    d.bolumEkle("Bilgisayar Mühendisliği")
    assert d.bolumleriListele() == ["Bilgisayar Mühendisliği", "Hukuk"]


def test_seed_listeleri_dolu():
    assert len(UNIVERSITELER) >= 25
    assert len(BOLUMLER) >= 30
    assert len({ad for ad, _ in UNIVERSITELER}) == len(UNIVERSITELER)
    assert len({alan for _, alan in UNIVERSITELER}) == len(UNIVERSITELER)
    assert len(set(BOLUMLER)) == len(BOLUMLER)
    assert all("." in alan and "@" not in alan for _, alan in UNIVERSITELER)
    assert ("Üniversite", "universite.edu.tr") in UNIVERSITELER
    assert "Bilgisayar Mühendisliği" in BOLUMLER
