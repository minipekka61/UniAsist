from datetime import datetime

import pytest

import config
from tests.yardimci import SahteYZ, gecici_db
from uniasist.depo.bilgi_kaynagi_deposu import BilgiKaynagiDeposu
from uniasist.depo.geri_bildirim_deposu import GeriBildirimDeposu
from uniasist.depo.kullanici_deposu import KullaniciDeposu
from uniasist.depo.soru_kaydi_deposu import SoruKaydiDeposu
from uniasist.depo.sohbet_deposu import SohbetDeposu
from uniasist.depo.yanitlanamayan_soru_deposu import YanitlanamayanSoruDeposu
from uniasist.entity import Kullanici
from uniasist.enumlar import (
    GeriBildirimTuru,
    GonderenTuru,
    KayitDurumu,
    Rol,
)
from uniasist.guvenlik import sifre_hashle
from uniasist.hatalar import IsKuraliIhlaliException
from uniasist.servis.arama_dizini import AramaDizini
from uniasist.servis.belge_isleme_servisi import BelgeIslemeServisi
from uniasist.servis.bilgi_tabani_servisi import BilgiTabaniServisi
from uniasist.servis.geri_bildirim_servisi import GeriBildirimServisi
from uniasist.servis.sohbet_servisi import SohbetServisi
from uniasist.servis.yanit_uretme_servisi import YanitUretmeServisi
from uniasist.servis.yanitlanamayan_soru_servisi import YanitlanamayanSoruServisi

BELGE_METNI = (
    "Burs yonergesi universite ogrencilerine saglanan destegi duzenler. "
    "Basari bursu icin genel not ortalamasinin en az 3.00 olmasi gerekir. "
    "Burs basvurusu eylul ayinin ilk haftasinda ogrenci isleri tarafindan alinir. "
    "Ihtiyac bursu icin gelir belgesi talep edilir ve aile geliri siniri kontrol edilir. "
    "Burs kapsaminda ogrenim ucreti destegi ve harc destegi saglanir. "
    "Yurt basvurusu ayri olarak KYK sistemi uzerinden yapilir ve temmuz ayinda acilir. "
)


@pytest.fixture
def servisler(tmp_path):
    db = gecici_db()
    yz = SahteYZ()
    dizin = AramaDizini(db)
    isleme = BelgeIslemeServisi(dizin, yz)
    bilgi_depo = BilgiKaynagiDeposu(db)
    bilgi_tabani = BilgiTabaniServisi(bilgi_depo, isleme, dizin)
    dosya = tmp_path / "burs.txt"
    dosya.write_text(BELGE_METNI * 3, encoding="utf-8")
    bilgi_tabani.belgeYukle("burs.txt", str(dosya), 1000, "Burs Yönergesi", "Burs")

    kullanici_depo = KullaniciDeposu(db)
    sohbet_depo = SohbetDeposu(db)
    soru_kaydi_depo = SoruKaydiDeposu(db)
    yanitlanamayan_depo = YanitlanamayanSoruDeposu(db)
    geri_bildirim_depo = GeriBildirimDeposu(db)

    yanit_uretme = YanitUretmeServisi(dizin, yz, benzerlik_esigi=config.YEREL_ESIK)
    yanitlanamayan = YanitlanamayanSoruServisi(yanitlanamayan_depo)
    sohbet = SohbetServisi(sohbet_depo, soru_kaydi_depo, yanit_uretme, yanitlanamayan, bilgi_depo)
    geri_bildirim = GeriBildirimServisi(sohbet_depo, geri_bildirim_depo)

    kullanici = Kullanici(ad_soyad="Ali Veli", eposta="ali@universite.edu.tr",
                          sifre_hash=sifre_hashle("Gizli1234"), rol=Rol.OGRENCI)
    kullanici_depo.kaydet(kullanici)

    return {
        "db": db,
        "yz": yz,
        "sohbet": sohbet,
        "yanitlanamayan": yanitlanamayan,
        "geri_bildirim": geri_bildirim,
        "bilgi_tabani": bilgi_tabani,
        "sohbet_depo": sohbet_depo,
        "soru_kaydi_depo": soru_kaydi_depo,
        "yanitlanamayan_depo": yanitlanamayan_depo,
        "kullanici": kullanici,
        "kullanici_depo": kullanici_depo,
    }


def ogrenci_sohbeti(servisler):
    return servisler["sohbet"].yeniSohbetBaslat(kullanici=servisler["kullanici"])


def test_ik11_bos_ve_uzun_soru(servisler):
    s = ogrenci_sohbeti(servisler)
    with pytest.raises(IsKuraliIhlaliException) as h:
        servisler["sohbet"].soruSor(s, "   ")
    assert h.value.kural_no_getir() == "IK-11"
    with pytest.raises(IsKuraliIhlaliException):
        servisler["sohbet"].soruSor(s, "x" * (config.AZAMI_SORU_UZUNLUGU + 1))


def test_ik11_500_karakter_siniri(servisler):
    s = ogrenci_sohbeti(servisler)
    soru = ("Burs başvurusu için gerekli belgeler nelerdir? " * 11)[:500]
    yanit = servisler["sohbet"].soruSor(s, soru)
    assert yanit is not None
    s2 = ogrenci_sohbeti(servisler)
    with pytest.raises(IsKuraliIhlaliException):
        servisler["sohbet"].soruSor(s2, "burs " + "x" * 501)


def test_ik15_kapsam_disi_soru(servisler):
    s = ogrenci_sohbeti(servisler)
    with pytest.raises(IsKuraliIhlaliException) as h:
        servisler["sohbet"].soruSor(s, "Bugün hava nasıl?")
    assert h.value.kural_no_getir() == "IK-15"
    assert h.value.mesaj == config.KAPSAM_METNI


def test_ik15_takip_sorusu_kapsamda(servisler):
    s = ogrenci_sohbeti(servisler)
    servisler["sohbet"].soruSor(s, "Burs başvurusu ne zaman yapılır?")
    yanit = servisler["sohbet"].soruSor(s, "Peki son tarihi ne zaman?")
    assert yanit is not None


def test_ik16_baglam_son_10_mesaj(servisler):
    s = ogrenci_sohbeti(servisler)
    for i in range(6):
        servisler["sohbet"].soruSor(s, f"Burs başvurusu {i}. adım nedir?")
    servisler["sohbet"].soruSor(s, "Peki son tarihi ne zaman?")
    baglam = servisler["yz"].gorunen_baglam
    assert baglam is not None
    assert len(baglam) == config.BAGLAM_MESAJ_SAYISI
    assert baglam[-1].gonderen == GonderenTuru.SISTEM


def test_ik17_yanit_uyarilar_tasir(servisler):
    s = ogrenci_sohbeti(servisler)
    olaylar = list(servisler["sohbet"].soruSorAkis(s, "Burs başvurusu ne zaman yapılır?"))
    sonuc = [o for o in olaylar if o["tur"] == "sonuc"][0]
    assert config.RESMI_UYARI in sonuc["uyarilar"]
    assert config.KISISEL_VERI_UYARISI in sonuc["uyarilar"]


def test_soru_yanit_kaydi_ve_kaynaklar(servisler):
    s = ogrenci_sohbeti(servisler)
    yanit = servisler["sohbet"].soruSor(s, "Burs başvurusu ne zaman yapılır?")
    assert yanit.gonderen == GonderenTuru.SISTEM
    assert len(yanit.kaynaklariGetir()) >= 1
    assert yanit.kaynaklariGetir()[0].kaynak_adi == "burs.txt"
    assert s.bosMu() is False
    assert s.baslik.startswith("Burs")

    kayitlar = servisler["soru_kaydi_depo"].araliktakiKayitlar(
        datetime(2000, 1, 1), datetime(2100, 1, 1)
    )
    assert len(kayitlar) == 1
    assert kayitlar[0].yanitlandi is True
    assert kayitlar[0].kategori == "Burs"


def test_ik20_ziyaretci_sohbeti_kalici_degil(servisler):
    sohbet = servisler["sohbet"].yeniSohbetBaslat(ziyaretci_oturum_id="ziyaretci-1")
    assert sohbet.kaliciMi() is False
    yanit = servisler["sohbet"].soruSor(sohbet, "Burs başvurusu ne zaman yapılır?")
    assert yanit is not None
    assert servisler["sohbet_depo"].kullaniciSohbetleri(servisler["kullanici"].kullanici_id) == []


def test_ik21_baskasina_ait_sohbet_reddedilir(servisler):
    baska = Kullanici(ad_soyad="Ayşe", eposta="ayse@universite.edu.tr",
                      sifre_hash="x", rol=Rol.OGRENCI)
    servisler["kullanici_depo"].kaydet(baska)
    s = ogrenci_sohbeti(servisler)
    servisler["sohbet"].soruSor(s, "Burs başvurusu ne zaman yapılır?")
    with pytest.raises(IsKuraliIhlaliException) as h:
        servisler["sohbet"].sohbetGetir(s.sohbet_id, baska.kullanici_id)
    assert h.value.kural_no_getir() == "IK-21"
    with pytest.raises(IsKuraliIhlaliException):
        servisler["sohbet"].sohbetSil(s.sohbet_id, baska.kullanici_id)


def test_ik22_tek_geri_bildirim_guncellenebilir(servisler):
    s = ogrenci_sohbeti(servisler)
    yanit = servisler["sohbet"].soruSor(s, "Burs başvurusu ne zaman yapılır?")
    gb = servisler["geri_bildirim"].geriBildirimVer(
        servisler["kullanici"].kullanici_id, yanit.mesaj_id, GeriBildirimTuru.YARARLI, None
    )
    gb2 = servisler["geri_bildirim"].geriBildirimVer(
        servisler["kullanici"].kullanici_id, yanit.mesaj_id, GeriBildirimTuru.YARARSIZ, "Yetersiz oldu."
    )
    yararsizlar = servisler["geri_bildirim"].yararsizlariListele()
    assert len(yararsizlar) == 1
    assert yararsizlar[0].aciklama == "Yetersiz oldu."
    assert yararsizlar[0].soru.startswith("Burs")
    assert yararsizlar[0].yanit
    with pytest.raises(IsKuraliIhlaliException):
        servisler["geri_bildirim"].geriBildirimVer(
            servisler["kullanici"].kullanici_id, yanit.mesaj_id, GeriBildirimTuru.YARARSIZ, "a" * 301
        )


def test_nfr04_baskasinin_mesajina_geri_bildirim_red(servisler):
    baska = Kullanici(ad_soyad="Ayşe", eposta="ayse@universite.edu.tr",
                      sifre_hash="x", rol=Rol.OGRENCI)
    servisler["kullanici_depo"].kaydet(baska)
    s = ogrenci_sohbeti(servisler)
    yanit = servisler["sohbet"].soruSor(s, "Burs başvurusu ne zaman yapılır?")
    with pytest.raises(IsKuraliIhlaliException):
        servisler["geri_bildirim"].geriBildirimVer(
            baska.kullanici_id, yanit.mesaj_id, GeriBildirimTuru.YARARLI, None
        )


def test_ik23_sohbet_silince_yanitlanamayan_kalir(servisler):
    servisler["yz"].mod = "yanit"
    s = ogrenci_sohbeti(servisler)
    from uniasist.enumlar import SonucDurumu

    from tests.yardimci import SahteYZ

    eski_mod = servisler["yz"].mod
    servisler["yz"].mod = "bilgi_yok"
    servisler["sohbet"].soruSor(s, "Yurt kayıt ücreti iade ediliyor mu?")
    servisler["yz"].mod = eski_mod
    servisler["sohbet"].sohbetSil(s.sohbet_id, servisler["kullanici"].kullanici_id)
    assert servisler["sohbet"].sohbetleriListele(servisler["kullanici"].kullanici_id) == []
    aciklar = servisler["yanitlanamayan_depo"].durumaGoreListele(KayitDurumu.ACIK)
    assert len(aciklar) == 1


def test_ik29_ayni_soru_tekrar_sayisi_artar(servisler):
    s = ogrenci_sohbeti(servisler)
    servisler["yz"].mod = "bilgi_yok"
    servisler["sohbet"].soruSor(s, "Yurt kayıt ücreti iade ediliyor mu?")
    servisler["sohbet"].soruSor(s, "Yurt kayıt ücreti iade ediliyor mu?")
    servisler["yz"].mod = "yanit"
    aciklar = servisler["yanitlanamayan_depo"].durumaGoreListele(KayitDurumu.ACIK)
    assert len(aciklar) == 1
    assert aciklar[0].tekrar_sayisi == 2


def test_soru_kaydi_bilgi_yokta_yanitlandi_false(servisler):
    s = ogrenci_sohbeti(servisler)
    servisler["yz"].mod = "bilgi_yok"
    servisler["sohbet"].soruSor(s, "Yurt kayıt ücreti iade ediliyor mu?")
    servisler["yz"].mod = "yanit"
    kayitlar = servisler["soru_kaydi_depo"].araliktakiKayitlar(
        datetime(2000, 1, 1), datetime(2100, 1, 1)
    )
    assert len(kayitlar) == 1
    assert kayitlar[0].yanitlandi is False


def test_ik19_servis_hatasi_soru_kaydi_yok(servisler):
    s = ogrenci_sohbeti(servisler)
    servisler["yz"].mod = "hata"
    olaylar = list(servisler["sohbet"].soruSorAkis(s, "Burs başvurusu ne zaman yapılır?"))
    servisler["yz"].mod = "yanit"
    sonuc = [o for o in olaylar if o["tur"] == "sonuc"][0]
    assert sonuc["durum"] == "SERVIS_HATASI"
    assert sonuc["metin"] == config.SERVIS_HATA_METNI
    kayitlar = servisler["soru_kaydi_depo"].araliktakiKayitlar(
        datetime(2000, 1, 1), datetime(2100, 1, 1)
    )
    assert kayitlar == []
    assert servisler["yanitlanamayan_depo"].durumaGoreListele(KayitDurumu.ACIK) == []


def test_ik35_yeni_sohbet_bos_olmayani_kaydeder(servisler):
    s1 = ogrenci_sohbeti(servisler)
    servisler["sohbet"].soruSor(s1, "Burs başvurusu ne zaman yapılır?")
    s2 = servisler["sohbet"].yeniSohbetBaslat(kullanici=servisler["kullanici"])
    assert s2.sohbet_id is None or s2.sohbet_id != s1.sohbet_id
    liste = servisler["sohbet"].sohbetleriListele(servisler["kullanici"].kullanici_id)
    assert len(liste) == 1
    assert liste[0].sohbet_id == s1.sohbet_id

    bos = servisler["sohbet"].yeniSohbetBaslat(kullanici=servisler["kullanici"])
    servisler["sohbet"].yeniSohbetBaslat(kullanici=servisler["kullanici"])
    assert servisler["sohbet"].sohbetleriListele(servisler["kullanici"].kullanici_id) == [liste[0]] or \
        len(servisler["sohbet"].sohbetleriListele(servisler["kullanici"].kullanici_id)) == 1


def test_uc07_silinen_kaynak_none_doner(servisler):
    s = ogrenci_sohbeti(servisler)
    yanit = servisler["sohbet"].soruSor(s, "Burs başvurusu ne zaman yapılır?")
    ref = yanit.kaynaklariGetir()[0]
    ref.kaynak_id = servisler["bilgi_tabani"].belgeleriListele()[0].kaynak_id
    assert servisler["sohbet"].kaynagiGoruntule(ref) is not None
    servisler["bilgi_tabani"].belgeSil(ref.kaynak_id)
    assert servisler["sohbet"].kaynagiGoruntule(ref) is None


def test_yanitlanamayan_sss_ile_cozulur(servisler):
    servisler["yanitlanamayan"].kaydet("Yurt kayıt ücreti iade ediliyor mu?")
    kayit = servisler["yanitlanamayan_depo"].durumaGoreListele(KayitDurumu.ACIK)[0]
    girdi = servisler["bilgi_tabani"].sssEkle(
        "Yurt kayıt ücreti iade ediliyor mu?", "Evet, iade edilir.", "Yurt"
    )
    servisler["yanitlanamayan"].sssIleCoz(kayit.kayit_id, girdi)
    assert servisler["yanitlanamayan_depo"].durumaGoreListele(KayitDurumu.ACIK) == []
    assert len(servisler["yanitlanamayan_depo"].durumaGoreListele(KayitDurumu.COZULDU)) == 1


def test_tum_sohbetleri_sil(servisler):
    s1 = ogrenci_sohbeti(servisler)
    servisler["sohbet"].soruSor(s1, "Burs başvurusu ne zaman yapılır?")
    s2 = ogrenci_sohbeti(servisler)
    servisler["sohbet"].soruSor(s2, "Burs için ortalama şartı nedir?")
    servisler["sohbet"].tumSohbetleriSil(servisler["kullanici"].kullanici_id)
    assert servisler["sohbet"].sohbetleriListele(servisler["kullanici"].kullanici_id) == []
