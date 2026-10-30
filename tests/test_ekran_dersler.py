import pytest

from tests.yardimci import SahteYZ, gecici_db
from uniasist.kurulum import kur
from uniasist.uygulama import uygulama_olustur

STAJ_METNI = (
    "Staj yonergesi ogrencilerin yaz stajlarini duzenler. "
    "Staj basvurusu icin en az 60 gun kesintisiz calisma sarti vardir. "
    "Staj defteri staj bitiminden sonraki 15 gun icinde teslim edilir. "
) * 3


@pytest.fixture
def paket():
    return kur(db=gecici_db(), yapay_zeka=SahteYZ())


@pytest.fixture
def ortam(paket):
    uygulama = uygulama_olustur(paket)
    uygulama.config["TESTING"] = True
    with uygulama.test_client() as istemci:
        yield istemci, paket


def _ogrenci(paket, eposta="ali@universite.edu.tr", pro=False):
    from uniasist.entity import Kullanici
    from uniasist.enumlar import Plan, Rol
    from uniasist.guvenlik import sifre_hashle

    k = Kullanici(
        ad_soyad="Ali Veli",
        eposta=eposta,
        sifre_hash=sifre_hashle("Gizli1234"),
        rol=Rol.OGRENCI,
        eposta_dogrulandi=True,
        plan=Plan.PRO if pro else None,
    )
    paket.kimlik.kullanici_deposu.kaydet(k)
    return k


def _giris_yap(istemci, eposta="ali@universite.edu.tr"):
    istemci.post("/giris", data={"eposta": eposta, "sifre": "Gizli1234"})


def _belge_yukle(paket, sahip, tmp_path, baslik, gorunurluk, ders_adi):
    from uniasist.enumlar import Gorunurluk

    dosya = tmp_path / f"{baslik.lower().replace(' ', '-')}.txt"
    dosya.write_text(STAJ_METNI, encoding="utf-8")
    return paket.bilgi_tabani.belgeYukle(
        dosya.name, str(dosya), 1000, baslik, "Staj",
        sahip=sahip, gorunurluk=Gorunurluk(gorunurluk), ders_adi=ders_adi,
    )


def test_dersler_listesi_ve_arama(ortam):
    istemci, paket = ortam
    _ogrenci(paket)
    _giris_yap(istemci)
    paket.ders_deposu.bulVeYaOlustur("Matematik I")
    paket.ders_deposu.bulVeYaOlustur("Fizik I")

    yanit = istemci.get("/dersler")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "Matematik I" in metin
    assert "Fizik I" in metin

    yanit = istemci.get("/dersler?q=fizik")
    metin = yanit.get_data(as_text=True)
    assert "Fizik I" in metin
    assert "Matematik I" not in metin


def test_ders_takip_et_ve_birak(ortam, tmp_path):
    istemci, paket = ortam
    _ogrenci(paket)
    sahip = _ogrenci(paket, eposta="sahip@universite.edu.tr", pro=True)
    _giris_yap(istemci)
    _belge_yukle(paket, sahip, tmp_path, "Burs Yönergesi", "PAYLASILAN", "Matematik I")
    ders = paket.ders_deposu.adIleBul("Matematik I")

    yanit = istemci.post(f"/dersler/{ders.ders_id}/takip")
    assert yanit.status_code == 302
    yanit = istemci.get(f"/dersler/{ders.ders_id}")
    assert "Burs Yönergesi" in yanit.get_data(as_text=True)

    istemci.post(f"/dersler/{ders.ders_id}/birak")
    yanit = istemci.get(f"/dersler/{ders.ders_id}")
    assert "Burs Yönergesi" not in yanit.get_data(as_text=True)


def test_yeni_ders_olusturma(ortam):
    istemci, paket = ortam
    ogr = _ogrenci(paket)
    _giris_yap(istemci)

    yanit = istemci.post("/dersler", data={"ad": "Fizik II"})
    assert yanit.status_code == 302
    ders = paket.ders_deposu.adIleBul("Fizik II")
    assert ders is not None
    assert paket.ders_deposu.takipteMi(ogr.kullanici_id, ders.ders_id)
    metin = istemci.get("/dersler").get_data(as_text=True)
    assert "Fizik II" in metin


def test_ders_detayinda_paylasilanlar(ortam, tmp_path):
    istemci, paket = ortam
    _ogrenci(paket)
    sahip = _ogrenci(paket, eposta="sahip@universite.edu.tr", pro=True)
    _giris_yap(istemci)
    _belge_yukle(paket, sahip, tmp_path, "Paylasilan Belge", "PAYLASILAN", "Matematik I")
    _belge_yukle(paket, sahip, tmp_path, "Ozel Belge", "OZEL", "Matematik I")
    ders = paket.ders_deposu.adIleBul("Matematik I")

    istemci.post(f"/dersler/{ders.ders_id}/takip")
    yanit = istemci.get(f"/dersler/{ders.ders_id}")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "Paylasilan Belge" in metin
    assert "Ozel Belge" not in metin
    assert "bildir" in metin.lower()
