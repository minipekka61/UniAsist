import pytest

import config
from tests.yardimci import SahteYZ, gecici_db
from uniasist.entity import Kullanici
from uniasist.enumlar import Gorunurluk, Plan, Rol
from uniasist.guvenlik import sifre_hashle
from uniasist.hatalar import IsKuraliIhlaliException
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


def ogrenci(paket, eposta="ali@universite.edu.tr"):
    k = Kullanici(
        ad_soyad="Ali Veli",
        eposta=eposta,
        sifre_hash=sifre_hashle("Gizli1234"),
        rol=Rol.OGRENCI,
        eposta_dogrulandi=True,
    )
    paket.kimlik.kullanici_deposu.kaydet(k)
    return k


def giris_yap(istemci, eposta="ali@universite.edu.tr"):
    istemci.post("/giris", data={"eposta": eposta, "sifre": "Gizli1234"})


def _belge_yukle(paket, sahip, tmp_path, i, gorunurluk=Gorunurluk.OZEL):
    dosya = tmp_path / f"burs-{i}.txt"
    dosya.write_text(
        "Burs yonergesi metni. Basari bursu icin ortalama sarti vardir. " * 5,
        encoding="utf-8",
    )
    return paket.bilgi_tabani.belgeYukle(
        f"burs-{i}.txt", str(dosya), 1000, f"Belge {i}", "Burs",
        sahip=sahip, gorunurluk=gorunurluk,
        ders_adi="Burs Dersi" if gorunurluk == Gorunurluk.PAYLASILAN else "",
    )


def test_haklar_ucrtsiz(paket):
    ogr = ogrenci(paket)
    haklar = paket.plan.haklar(ogr)
    assert haklar["plan"] == Plan.UCRETSIZ
    assert haklar["belge_limiti"] == config.UCRETSIZ_AZAMI_BELGE
    assert haklar["gunluk_limit"] == config.UCRETSIZ_GUNLUK_SORU
    assert haklar["belge_sayisi"] == 0
    assert haklar["bugunku_soru"] == 0


def test_ik33_gunluk_soru_limiti(paket):
    ogr = ogrenci(paket)
    sohbet = paket.sohbet.yeniSohbetBaslat(kullanici=ogr)
    for _ in range(config.UCRETSIZ_GUNLUK_SORU):
        paket.sohbet.soruSor(sohbet, "Burs başvurusu ne zaman yapılır?")
    with pytest.raises(IsKuraliIhlaliException) as h:
        paket.sohbet.soruSor(sohbet, "Burs başvurusu ne zaman yapılır?")
    assert h.value.kural_no_getir() == "IK-33"

    paket.plan.proYap(ogr)
    yanit = paket.sohbet.soruSor(sohbet, "Burs başvurusu ne zaman yapılır?")
    assert yanit is not None


def test_ik34_belge_limiti(paket, tmp_path):
    ogr = ogrenci(paket)
    for i in range(config.UCRETSIZ_AZAMI_BELGE):
        _belge_yukle(paket, ogr, tmp_path, i)
    with pytest.raises(IsKuraliIhlaliException) as h:
        _belge_yukle(paket, ogr, tmp_path, config.UCRETSIZ_AZAMI_BELGE)
    assert h.value.kural_no_getir() == "IK-34"

    paket.plan.proYap(ogr)
    belge = _belge_yukle(paket, ogr, tmp_path, config.UCRETSIZ_AZAMI_BELGE)
    assert belge.kaynak_id is not None


def test_ik36_ucretsiz_paylasamaz(paket, tmp_path):
    ogr = ogrenci(paket)
    with pytest.raises(IsKuraliIhlaliException) as h:
        _belge_yukle(paket, ogr, tmp_path, 0, gorunurluk=Gorunurluk.PAYLASILAN)
    assert h.value.kural_no_getir() == "IK-36"

    ozel = _belge_yukle(paket, ogr, tmp_path, 1)
    with pytest.raises(IsKuraliIhlaliException) as h:
        paket.bilgi_tabani.gorunurlukDegistir(
            ozel.kaynak_id, ogr, Gorunurluk.PAYLASILAN, ders_adi="Burs Dersi"
        )
    assert h.value.kural_no_getir() == "IK-36"


def test_proya_gecis_ve_donus(paket):
    ogr = ogrenci(paket)
    paket.plan.proYap(ogr)
    assert ogr.proMu()
    assert paket.kimlik.kullanici_deposu.idIleBul(ogr.kullanici_id).plan == Plan.PRO

    paket.plan.ucretsizeDon(ogr)
    assert not ogr.proMu()
    okunan = paket.kimlik.kullanici_deposu.idIleBul(ogr.kullanici_id)
    assert okunan.plan == Plan.UCRETSIZ


def test_prodan_donusumde_paylasim_kalir(paket, tmp_path):
    ogr = ogrenci(paket)
    paket.plan.proYap(ogr)
    _belge_yukle(paket, ogr, tmp_path, 0, gorunurluk=Gorunurluk.PAYLASILAN)

    paket.plan.ucretsizeDon(ogr)
    okunan = paket.bilgi_tabani.belgeleriListele(ogr.kullanici_id)[0]
    assert okunan.gorunurluk == Gorunurluk.PAYLASILAN


def test_plan_ekrani_ve_gecis(ortam):
    istemci, paket = ortam
    ogr = ogrenci(paket)
    giris_yap(istemci)

    yanit = istemci.get("/plan")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "Ücretsiz" in metin
    assert "Pro" in metin

    yanit = istemci.post("/plan/pro", follow_redirects=True)
    assert yanit.status_code == 200
    assert paket.kimlik.kullanici_deposu.idIleBul(ogr.kullanici_id).proMu()

    yanit = istemci.post("/plan/ucretsiz", follow_redirects=True)
    assert yanit.status_code == 200
    assert not paket.kimlik.kullanici_deposu.idIleBul(ogr.kullanici_id).proMu()
