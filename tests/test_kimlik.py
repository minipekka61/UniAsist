import logging
import re
from datetime import datetime, timedelta

import pytest

import config
from tests.yardimci import gecici_db
from uniasist.depo.kullanici_deposu import KullaniciDeposu
from uniasist.depo.universite_deposu import UniversiteDeposu
from uniasist.depo.veritabani import oturum_bul
from uniasist.entity import Universite
from uniasist.enumlar import HesapDurumu, Rol
from uniasist.eposta import KonsolEpostaServisi
from uniasist.guvenlik import sifre_hashle
from uniasist.hatalar import IsKuraliIhlaliException
from uniasist.servis.kimlik_dogrulama_servisi import KimlikDogrulamaServisi
from uniasist.servis.kullanici_yonetim_servisi import KullaniciYonetimServisi
from uniasist.veri.bolumler import BOLUMLER
from uniasist.veri.universiteler import UNIVERSITELER

BOLUM = "Bilgisayar Mühendisliği"


@pytest.fixture
def servisler():
    db = gecici_db()
    kullanici_deposu = KullaniciDeposu(db)
    universite_deposu = UniversiteDeposu(db)
    for ad, alan_adi in UNIVERSITELER:
        universite_deposu.kaydet(Universite(ad=ad, eposta_alan_adi=alan_adi))
    for bolum in BOLUMLER:
        universite_deposu.bolumEkle(bolum)
    kimlik = KimlikDogrulamaServisi(
        kullanici_deposu, universite_deposu, KonsolEpostaServisi()
    )
    yonetim = KullaniciYonetimServisi(kullanici_deposu, kimlik)
    return kimlik, yonetim, kullanici_deposu


def test_ik01_alan_adi_kontrolu(servisler):
    kimlik, _, _ = servisler
    with pytest.raises(IsKuraliIhlaliException) as h:
        kimlik.kayitOl("Ali Veli", "ali@gmail.com", "Gizli1234", "Gizli1234", BOLUM)
    assert h.value.kural_no_getir() == "IK-01"


def test_ik02_eposta_benzersiz(servisler):
    kimlik, _, _ = servisler
    kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    with pytest.raises(IsKuraliIhlaliException) as h:
        kimlik.kayitOl("Başka", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    assert h.value.kural_no_getir() == "IK-02"


def test_ik03_sifre_kurallari(servisler):
    kimlik, _, _ = servisler
    for sifre, tekrar in [("Kisa1", "Kisa1"), ("12345678", "12345678"), ("sifresifre", "sifresifre"), ("Gizli1234", "Baska1234")]:
        with pytest.raises(IsKuraliIhlaliException) as h:
            kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", sifre, tekrar, BOLUM)
        assert h.value.kural_no_getir() == "IK-03"


def test_ik06_kayit_rolu_ogrenci(servisler):
    kimlik, _, _ = servisler
    k = kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    assert k.rol == Rol.OGRENCI
    assert k.aktifMi()
    assert k.sifreDogrula("Gizli1234")


def test_ik04_5_denemede_kilit_ve_mesaj(servisler):
    kimlik, _, _ = servisler
    kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    for i in range(config.AZAMI_HATALI_DENEME - 1):
        with pytest.raises(IsKuraliIhlaliException) as h:
            kimlik.girisYap("ali@universite.edu.tr", "yanlis")
        assert h.value.kural_no_getir() == "IK-04"
        assert h.value.mesaj == config.HATA_EPOSTA_SIFRE
    with pytest.raises(IsKuraliIhlaliException):
        kimlik.girisYap("ali@universite.edu.tr", "yanlis")
    with pytest.raises(IsKuraliIhlaliException) as h:
        kimlik.girisYap("ali@universite.edu.tr", "Gizli1234")
    assert h.value.kural_no_getir() == "IK-04"
    assert h.value.mesaj == config.HATA_KILIT


def test_ik04_4_denemeden_sonra_dogru_giris(servisler):
    kimlik, _, _ = servisler
    kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    for _ in range(config.AZAMI_HATALI_DENEME - 1):
        with pytest.raises(IsKuraliIhlaliException):
            kimlik.girisYap("ali@universite.edu.tr", "yanlis")
    oturum = kimlik.girisYap("ali@universite.edu.tr", "Gizli1234")
    assert oturum is not None and oturum.oturum_id


def test_ik04_olmayan_eposta_ayni_mesaj(servisler):
    kimlik, _, _ = servisler
    with pytest.raises(IsKuraliIhlaliException) as h:
        kimlik.girisYap("yok@universite.edu.tr", "yanlis")
    assert h.value.mesaj == config.HATA_EPOSTA_SIFRE


def test_ik05_devre_disi_giris_engellenir(servisler):
    kimlik, yonetim, depo = servisler
    k = kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    k.devreDisiBirak()
    depo.kaydet(k)
    with pytest.raises(IsKuraliIhlaliException) as h:
        kimlik.girisYap("ali@universite.edu.tr", "Gizli1234")
    assert h.value.kural_no_getir() == "IK-05"


def test_ik07_sifre_degistirme_kurallari(servisler):
    kimlik, _, _ = servisler
    k = kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    with pytest.raises(IsKuraliIhlaliException):
        kimlik.sifreDegistir(k.kullanici_id, "yanlis", "Yeni1234", "Yeni1234")
    with pytest.raises(IsKuraliIhlaliException):
        kimlik.sifreDegistir(k.kullanici_id, "Gizli1234", "Gizli1234", "Gizli1234")
    with pytest.raises(IsKuraliIhlaliException):
        kimlik.sifreDegistir(k.kullanici_id, "Gizli1234", "zayif", "zayif")
    with pytest.raises(IsKuraliIhlaliException):
        kimlik.sifreDegistir(k.kullanici_id, "Gizli1234", "Yeni1234", "Baska1234")
    kimlik.sifreDegistir(k.kullanici_id, "Gizli1234", "Yeni12345", "Yeni12345")
    oturum = kimlik.girisYap("ali@universite.edu.tr", "Yeni12345")
    assert oturum is not None


def test_ik08_oturum_30_dk_sure_doldu(servisler):
    kimlik, _, _ = servisler
    k = kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    oturum = kimlik.girisYap("ali@universite.edu.tr", "Gizli1234")
    oturum.son_etkinlik_zamani = datetime.now() - timedelta(minutes=config.OTURUM_SURESI_DK + 1)
    from uniasist.depo.veritabani import oturum_kaydet

    oturum_kaydet(kimlik.kullanici_deposu.db, oturum)
    assert kimlik.oturumDogrula(oturum.oturum_id) is None
    assert oturum_bul(kimlik.kullanici_deposu.db, oturum.oturum_id) is None


def test_ik08_etkinlikte_sure_uzar(servisler):
    kimlik, _, _ = servisler
    kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    oturum = kimlik.girisYap("ali@universite.edu.tr", "Gizli1234")
    bulunan = kimlik.oturumDogrula(oturum.oturum_id)
    assert bulunan is not None
    assert bulunan.eposta == "ali@universite.edu.tr"


def test_cikis_yap(servisler):
    kimlik, _, _ = servisler
    kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    oturum = kimlik.girisYap("ali@universite.edu.tr", "Gizli1234")
    kimlik.cikisYap(oturum.oturum_id)
    assert kimlik.oturumDogrula(oturum.oturum_id) is None


def test_ik10_kendi_rolunu_degistiremez(servisler):
    kimlik, yonetim, _ = servisler
    yonetici = kimlik.kayitOl("Admin", "admin@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    yonetici.rolDegistir(Rol.YONETICI)
    kimlik.kullanici_deposu.kaydet(yonetici)
    with pytest.raises(IsKuraliIhlaliException) as h:
        yonetim.rolDegistir(yonetici.kullanici_id, yonetici.kullanici_id, Rol.OGRENCI)
    assert h.value.kural_no_getir() == "IK-10"


def test_ik10_son_aktif_yonetici_korunur(servisler):
    kimlik, yonetim, depo = servisler
    yonetici = kimlik.kayitOl("Admin", "admin@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    yonetici.rolDegistir(Rol.YONETICI)
    depo.kaydet(yonetici)
    with pytest.raises(IsKuraliIhlaliException) as h:
        yonetim.hesapDevreDisiBirak(yonetici.kullanici_id, yonetici.kullanici_id)
    assert h.value.kural_no_getir() == "IK-10"
    hedef = kimlik.kayitOl("Hedef Kullanıcı", "hedef@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    hedef.rolDegistir(Rol.YONETICI)
    depo.kaydet(hedef)
    yonetim.hesapDevreDisiBirak(yonetici.kullanici_id, hedef.kullanici_id)
    assert depo.idIleBul(hedef.kullanici_id).durum == HesapDurumu.DEVRE_DISI


def test_ik32_yonetici_hedefin_rolu_degistirilemez(servisler):
    kimlik, yonetim, depo = servisler
    yonetici = kimlik.kayitOl("Admin", "admin@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    yonetici.rolDegistir(Rol.YONETICI)
    depo.kaydet(yonetici)
    ikinci = kimlik.kayitOl("Ayse", "ayse@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    ikinci.rolDegistir(Rol.YONETICI)
    depo.kaydet(ikinci)
    with pytest.raises(IsKuraliIhlaliException) as h:
        yonetim.rolDegistir(yonetici.kullanici_id, ikinci.kullanici_id, Rol.OGRENCI)
    assert "değiştirilemez" in h.value.mesaj
    assert depo.idIleBul(ikinci.kullanici_id).rol == Rol.YONETICI


def test_ik32_yonetici_rolu_verilemez(servisler):
    kimlik, yonetim, depo = servisler
    yonetici = kimlik.kayitOl("Admin", "admin@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    yonetici.rolDegistir(Rol.YONETICI)
    depo.kaydet(yonetici)
    ogrenci = kimlik.kayitOl("Ali", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    with pytest.raises(IsKuraliIhlaliException):
        yonetim.rolDegistir(yonetici.kullanici_id, ogrenci.kullanici_id, Rol.YONETICI)


def test_ik31_devre_disi_oturumlar_sonlanir(servisler):
    kimlik, yonetim, depo = servisler
    yonetici = kimlik.kayitOl("Admin", "admin@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    yonetici.rolDegistir(Rol.YONETICI)
    depo.kaydet(yonetici)
    hedef = kimlik.kayitOl("Ali", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    oturum = kimlik.girisYap("ali@universite.edu.tr", "Gizli1234")
    yonetim.hesapDevreDisiBirak(yonetici.kullanici_id, hedef.kullanici_id)
    assert kimlik.oturumDogrula(oturum.oturum_id) is None


def test_kullanicilari_listele_ve_ara(servisler):
    kimlik, yonetim, _ = servisler
    kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    kimlik.kayitOl("Ayşe Can", "ayse@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM)
    assert len(yonetim.kullanicilariListele("")) == 2
    assert len(yonetim.kullanicilariListele("ali")) == 1
    assert yonetim.kullanicilariListele("ali")[0].ad_soyad == "Ali Veli"


def test_kayit_bolum_ve_universite_atanir(servisler):
    kimlik, _, depo = servisler
    k = kimlik.kayitOl(
        "Ali Veli", "ali@ogrenci.istanbul.edu.tr", "Gizli1234", "Gizli1234", BOLUM
    )
    assert k.universite_id is not None
    assert k.bolum == BOLUM
    assert not k.eposta_dogrulandi
    assert k.dogrulama_token
    assert k.dogrulama_bitis > datetime.now()
    u = UniversiteDeposu(depo.db).idIleBul(k.universite_id)
    assert u.ad == "İstanbul Üniversitesi"


def test_kayit_bilinmeyen_alan_adi_reddedilir(servisler):
    kimlik, _, _ = servisler
    with pytest.raises(IsKuraliIhlaliException) as h:
        kimlik.kayitOl("Ali Veli", "ali@bilinmeyen.edu.tr", "Gizli1234", "Gizli1234", "Hukuk")
    assert h.value.kural_no_getir() == "IK-01"
    assert "henüz desteklenmiyor" in h.value.mesaj


def test_kayit_gecersiz_bolum_reddedilir(servisler):
    kimlik, _, _ = servisler
    with pytest.raises(IsKuraliIhlaliException) as h:
        kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", "Uzay Mühendisliği")
    assert h.value.kural_no_getir() == "IK-01"


def test_dogrula_token_ile_hesap_aktifleşir(servisler):
    kimlik, _, depo = servisler
    k = kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", "Hukuk")
    dogrulanmis = kimlik.dogrula(k.dogrulama_token)
    assert dogrulanmis.eposta_dogrulandi
    assert dogrulanmis.dogrulama_token is None
    assert dogrulanmis.dogrulama_bitis is None
    assert depo.idIleBul(k.kullanici_id).dogrulanmisMi()


def test_dogrulama_sure_dolmus_token_red(servisler):
    kimlik, _, depo = servisler
    k = kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", "Hukuk")
    k.dogrulama_bitis = datetime.now() - timedelta(hours=1)
    depo.kaydet(k)
    with pytest.raises(IsKuraliIhlaliException) as h:
        kimlik.dogrula(k.dogrulama_token)
    assert h.value.kural_no_getir() == "IK-29"
    assert not depo.idIleBul(k.kullanici_id).dogrulanmisMi()


def test_dogrulama_token_tek_kullanim(servisler):
    kimlik, _, _ = servisler
    k = kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", "Hukuk")
    kimlik.dogrula(k.dogrulama_token)
    with pytest.raises(IsKuraliIhlaliException) as h:
        kimlik.dogrula(k.dogrulama_token)
    assert h.value.kural_no_getir() == "IK-29"


def test_dogrulama_gonder_yeniden(servisler):
    kimlik, _, depo = servisler
    k = kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234", "Hukuk")
    eski_token = k.dogrulama_token
    kimlik.dogrulamaGonder("ali@universite.edu.tr")
    taze = depo.epostaIleBul("ali@universite.edu.tr")
    assert taze.dogrulama_token != eski_token
    with pytest.raises(IsKuraliIhlaliException):
        kimlik.dogrula(eski_token)
    assert kimlik.dogrula(taze.dogrulama_token).dogrulanmisMi()


def test_dogrulama_epostasi_mutlak_baglanti(servisler, caplog):
    kimlik, _, _ = servisler
    with caplog.at_level(logging.INFO, logger="uniasist.eposta"):
        kimlik.kayitOl(
            "Mutlak Url", "mutlak@universite.edu.tr", "Gizli1234", "Gizli1234", BOLUM
        )
    eslesme = re.search(r"bağlantı: (\S+)", caplog.text)
    assert eslesme is not None
    baglanti = eslesme.group(1)
    assert baglanti.startswith("http://")
    assert "/dogrula/" in baglanti
