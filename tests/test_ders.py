from datetime import datetime

from tests.yardimci import gecici_db
from uniasist.depo.ders_deposu import DersDeposu
from uniasist.depo.kullanici_deposu import KullaniciDeposu
from uniasist.depo.soru_kaydi_deposu import SoruKaydiDeposu
from uniasist.entity import Kullanici, SoruKaydi
from uniasist.enumlar import Plan, Rol


def test_ders_bul_veya_olustur():
    depo = DersDeposu(gecici_db())
    ders = depo.bulVeYaOlustur("  Matematik I  ")
    assert ders.ders_id is not None
    assert ders.ad == "Matematik I"
    tekrar = depo.bulVeYaOlustur("matematik i")
    assert tekrar.ders_id == ders.ders_id


def test_ders_ad_eslesmesi_harf_duyarsiz():
    depo = DersDeposu(gecici_db())
    depo.bulVeYaOlustur("Matematik I")
    bulunan = depo.adIleBul("MATEMATIK I")
    assert bulunan is not None
    assert bulunan.ad == "Matematik I"
    assert depo.adIleBul("Olmayan Ders") is None


def test_ders_hepsini_listele_siralama():
    depo = DersDeposu(gecici_db())
    depo.bulVeYaOlustur("Fizik I")
    depo.bulVeYaOlustur("Matematik I")
    assert [d.ad for d in depo.hepsiniListele()] == ["Fizik I", "Matematik I"]


def test_ders_takip_et_ve_birak():
    depo = DersDeposu(gecici_db())
    ders = depo.bulVeYaOlustur("Fizik I")
    depo.takipEt(1, ders.ders_id)
    assert depo.takipteMi(1, ders.ders_id)
    assert depo.kullanicininDersIdleri(1) == {ders.ders_id}
    assert [d.ders_id for d in depo.kullanicininDersleri(1)] == [ders.ders_id]
    depo.takibiBirak(1, ders.ders_id)
    assert not depo.takipteMi(1, ders.ders_id)
    assert depo.kullanicininDersIdleri(1) == set()


def test_ders_ara():
    depo = DersDeposu(gecici_db())
    depo.bulVeYaOlustur("Matematik I")
    depo.bulVeYaOlustur("Fizik I")
    sonuc = depo.ara("mat")
    assert [d.ad for d in sonuc] == ["Matematik I"]


def test_kullanici_plan_varsayilan_ucrtsiz():
    depo = KullaniciDeposu(gecici_db())
    depo.kaydet(Kullanici(
        ad_soyad="Ali Veli", eposta="ali@x.edu.tr", sifre_hash="x", rol=Rol.OGRENCI,
    ))
    okunan = depo.epostaIleBul("ali@x.edu.tr")
    assert okunan.plan == Plan.UCRETSIZ
    assert not okunan.proMu()
    okunan.plan = Plan.PRO
    depo.kaydet(okunan)
    assert depo.epostaIleBul("ali@x.edu.tr").proMu()


def test_soru_kaydi_kullanici_id_kalici():
    depo = SoruKaydiDeposu(gecici_db())
    depo.kaydet(SoruKaydi(
        zaman=datetime.now(), kategori="Burs", yanitlandi=True, kullanici_id=7,
    ))
    kayitlar = depo.araliktakiKayitlar(
        datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
        datetime.now(),
    )
    assert len(kayitlar) == 1
    assert kayitlar[0].kullanici_id == 7
