from datetime import datetime, timedelta

import pytest

from tests.yardimci import gecici_db
from uniasist.depo.geri_bildirim_deposu import GeriBildirimDeposu
from uniasist.depo.soru_kaydi_deposu import SoruKaydiDeposu
from uniasist.entity import GeriBildirim, SoruKaydi
from uniasist.enumlar import GeriBildirimTuru
from uniasist.hatalar import IsKuraliIhlaliException
from uniasist.servis.rapor_servisi import RaporServisi


@pytest.fixture
def servisler():
    db = gecici_db()
    soru_depo = SoruKaydiDeposu(db)
    gb_depo = GeriBildirimDeposu(db)
    return RaporServisi(soru_depo, gb_depo), soru_depo, gb_depo


def test_ik33_varsayilan_son_30_gun(servisler):
    servis, _, _ = servisler
    rapor = servis.raporOlustur()
    assert (rapor.bitis - rapor.baslangic).days >= 29
    assert rapor.tarihAraligiGecerliMi()


def test_ik33_bitis_baslangictan_once_hata(servisler):
    servis, _, _ = servisler
    with pytest.raises(IsKuraliIhlaliException) as h:
        servis.raporOlustur(datetime(2026, 10, 10), datetime(2026, 10, 1))
    assert h.value.kural_no_getir() == "IK-33"


def test_ik34_metrikler(servisler):
    servis, soru_depo, gb_depo = servisler
    simdi = datetime.now()
    kayitlar = [
        SoruKaydi(zaman=simdi, kategori="Burs", yanitlandi=True),
        SoruKaydi(zaman=simdi, kategori="Burs", yanitlandi=True),
        SoruKaydi(zaman=simdi, kategori="Burs", yanitlandi=False),
        SoruKaydi(zaman=simdi, kategori="Yurt", yanitlandi=False),
        SoruKaydi(zaman=simdi, kategori="Kayıt", yanitlandi=True),
        SoruKaydi(zaman=simdi, kategori="Kayıt", yanitlandi=True),
        SoruKaydi(zaman=simdi, kategori="Staj", yanitlandi=True),
        SoruKaydi(zaman=simdi, kategori=None, yanitlandi=False),
    ]
    for k in kayitlar:
        soru_depo.kaydet(k)
    gb_depo.kaydet(GeriBildirim(mesaj_id=1, kullanici_id=1, tur=GeriBildirimTuru.YARARLI, aciklama=None, zaman=simdi))
    gb_depo.kaydet(GeriBildirim(mesaj_id=2, kullanici_id=1, tur=GeriBildirimTuru.YARARLI, aciklama=None, zaman=simdi))
    gb_depo.kaydet(GeriBildirim(mesaj_id=3, kullanici_id=1, tur=GeriBildirimTuru.YARARSIZ, aciklama="kotı", zaman=simdi))

    rapor = servis.raporOlustur(simdi - timedelta(days=1), simdi + timedelta(days=1))
    assert rapor.toplam_soru == 8
    assert abs(rapor.yanitlanamayan_orani - 3 / 8) < 1e-9
    assert abs(rapor.olumlu_geri_bildirim_orani - 2 / 3) < 1e-9
    kategoriler = list(rapor.en_cok_sorulan_kategoriler.items())
    assert kategoriler[0][0] == "Burs" and kategoriler[0][1] == 3
    assert len(kategoriler) == 4


def test_ik34_csv_format(servisler):
    servis, soru_depo, _ = servisler
    simdi = datetime(2026, 10, 15, 12, 0)
    soru_depo.kaydet(SoruKaydi(zaman=simdi, kategori="Burs", yanitlandi=True))
    soru_depo.kaydet(SoruKaydi(zaman=simdi, kategori="Öğrenci İşleri", yanitlandi=False))
    rapor = servis.raporOlustur(datetime(2026, 10, 1), datetime(2026, 10, 31))
    csv = servis.csvHazirla(rapor)
    assert csv.startswith("Metrik;Değer")
    assert "Toplam Soru;2" in csv
    assert "Yanıtlanamayan Soru Oranı;%50,0" in csv
    assert "Rapor Dönemi;01.10.2026 - 31.10.2026" in csv
    assert "Burs;1" in csv
    assert "Öğrenci İşleri;1" in csv
    assert csv.encode("utf-8-sig").decode("utf-8-sig") == csv


def test_ik34_veri_yok(servisler):
    servis, _, _ = servisler
    rapor = servis.raporOlustur(datetime(2026, 1, 1), datetime(2026, 1, 31))
    assert rapor.toplam_soru == 0
    assert rapor.yanitlanamayan_orani == 0.0
    assert rapor.olumlu_geri_bildirim_orani == 0.0
    csv = servis.csvHazirla(rapor)
    assert "Toplam Soru;0" in csv
    assert "%0,0" in csv
