from datetime import datetime

import pytest

import config
from tests.yardimci import SahteYZ, gecici_db
from uniasist.depo.bilgi_kaynagi_deposu import BilgiKaynagiDeposu
from uniasist.depo.ders_deposu import DersDeposu
from uniasist.depo.geri_bildirim_deposu import GeriBildirimDeposu
from uniasist.depo.kullanici_deposu import KullaniciDeposu
from uniasist.depo.soru_kaydi_deposu import SoruKaydiDeposu
from uniasist.depo.sohbet_deposu import SohbetDeposu
from uniasist.depo.yanitlanamayan_soru_deposu import YanitlanamayanSoruDeposu
from uniasist.entity import Kullanici
from uniasist.enumlar import (
    GeriBildirimTuru,
    GonderenTuru,
    Gorunurluk,
    KayitDurumu,
    Plan,
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
    kullanici_depo = KullaniciDeposu(db)
    bilgi_depo = BilgiKaynagiDeposu(db)
    bilgi_tabani = BilgiTabaniServisi(bilgi_depo, isleme, dizin, DersDeposu(db))
    kullanici = Kullanici(
        ad_soyad="Ali Veli",
        eposta="ali@universite.edu.tr",
        sifre_hash=sifre_hashle("Gizli1234"),
        rol=Rol.OGRENCI,
        bolum="Bilgisayar Mühendisliği",
        eposta_dogrulandi=True,
    )
    kullanici_depo.kaydet(kullanici)

    dosya = tmp_path / "burs.txt"
    dosya.write_text(BELGE_METNI * 3, encoding="utf-8")
    bilgi_tabani.belgeYukle("burs.txt", str(dosya), 1000, "Burs Yönergesi", "Burs", sahip=kullanici)

    sohbet_depo = SohbetDeposu(db)
    soru_kaydi_depo = SoruKaydiDeposu(db)
    yanitlanamayan_depo = YanitlanamayanSoruDeposu(db)
    geri_bildirim_depo = GeriBildirimDeposu(db)

    ders_depo = DersDeposu(db)
    yanit_uretme = YanitUretmeServisi(dizin, yz, benzerlik_esigi=config.YEREL_ESIK)
    yanitlanamayan = YanitlanamayanSoruServisi(yanitlanamayan_depo)
    sohbet = SohbetServisi(sohbet_depo, soru_kaydi_depo, yanit_uretme, yanitlanamayan, bilgi_depo, kullanici_depo, ders_depo)
    geri_bildirim = GeriBildirimServisi(sohbet_depo, geri_bildirim_depo)

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
        "ders_depo": ders_depo,
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


def test_kapsam_filtresi_kalkti(servisler):
    s = ogrenci_sohbeti(servisler)
    yanit = servisler["sohbet"].soruSor(s, "Futbol nasıl bir spordur?")
    assert yanit is not None


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
    ref.kaynak_id = servisler["bilgi_tabani"].belgeleriListele(
        servisler["kullanici"].kullanici_id
    )[0].kaynak_id
    assert servisler["sohbet"].kaynagiGoruntule(ref, servisler["kullanici"]) is not None
    servisler["bilgi_tabani"].belgeSil(ref.kaynak_id, servisler["kullanici"].kullanici_id)
    assert servisler["sohbet"].kaynagiGoruntule(ref, servisler["kullanici"]) is None


def test_yanitlanamayan_cozuldu_isaretlenir(servisler):
    servisler["yanitlanamayan"].kaydet("Yurt kayıt ücreti iade ediliyor mu?")
    kayit = servisler["yanitlanamayan_depo"].durumaGoreListele(KayitDurumu.ACIK)[0]
    servisler["yanitlanamayan"].cozulduIsaretle(kayit.kayit_id)
    assert servisler["yanitlanamayan_depo"].durumaGoreListele(KayitDurumu.ACIK) == []
    assert len(servisler["yanitlanamayan_depo"].durumaGoreListele(KayitDurumu.COZULDU)) == 1


def test_tum_sohbetleri_sil(servisler):
    s1 = ogrenci_sohbeti(servisler)
    servisler["sohbet"].soruSor(s1, "Burs başvurusu ne zaman yapılır?")
    s2 = ogrenci_sohbeti(servisler)
    servisler["sohbet"].soruSor(s2, "Burs için ortalama şartı nedir?")
    servisler["sohbet"].tumSohbetleriSil(servisler["kullanici"].kullanici_id)
    assert servisler["sohbet"].sohbetleriListele(servisler["kullanici"].kullanici_id) == []


STAJ_METNI = (
    "Staj yonergesi ogrencilerin yaz stajlarini duzenler ve zorunlu kilar. "
    "Staj basvurusu icin en az 60 gun kesintisiz calisma sarti vardir. "
    "Staj defteri staj bitiminden sonraki 15 gun icinde teslim edilir. "
    "Staj degerlendirme formu isyeri yetkilisi tarafindan doldurulur. "
    "Staj sigortasi universite tarafindan yaptirilir. "
) * 3


def _baska_ogrenci(servisler, eposta, pro=False):
    k = Kullanici(
        ad_soyad="Başka Öğrenci",
        eposta=eposta,
        sifre_hash="x",
        rol=Rol.OGRENCI,
        eposta_dogrulandi=True,
        plan=Plan.PRO if pro else None,
    )
    servisler["kullanici_depo"].kaydet(k)
    return k


def _staj_belgesi_yukle(servisler, sahip, tmp_path, gorunurluk=Gorunurluk.OZEL):
    dosya = tmp_path / f"staj-{sahip.kullanici_id}-{gorunurluk.value}.txt"
    dosya.write_text(STAJ_METNI, encoding="utf-8")
    return servisler["bilgi_tabani"].belgeYukle(
        "staj.txt", str(dosya), 1000, "Staj Yönergesi", "Staj",
        sahip=sahip, gorunurluk=gorunurluk,
        ders_adi="Staj Dersi" if gorunurluk == Gorunurluk.PAYLASILAN else "",
    )


def test_kapsam_kendi_belgesinden_yanit_alir(servisler):
    s = ogrenci_sohbeti(servisler)
    yanit = servisler["sohbet"].soruSor(s, "Burs başvurusu ne zaman yapılır?")
    assert yanit is not None
    assert len(yanit.kaynaklariGetir()) >= 1


def test_kapsam_takip_ettigi_dersin_paylasilanini_gorur(servisler, tmp_path):
    baska = _baska_ogrenci(servisler, "baska@universite.edu.tr", pro=True)
    paylasilan = _staj_belgesi_yukle(servisler, baska, tmp_path, gorunurluk=Gorunurluk.PAYLASILAN)
    servisler["ders_depo"].takipEt(
        servisler["kullanici"].kullanici_id, paylasilan.ders_id
    )
    s = ogrenci_sohbeti(servisler)
    yanit = servisler["sohbet"].soruSor(s, "Staj defteri ne zaman teslim edilir?")
    assert yanit is not None
    alinti_idler = {r.kaynak_id for r in yanit.kaynaklariGetir()}
    assert paylasilan.kaynak_id in alinti_idler


def test_kapsam_takip_etmedigi_dersi_gormez(servisler, tmp_path):
    baska = _baska_ogrenci(servisler, "baska@universite.edu.tr", pro=True)
    paylasilan = _staj_belgesi_yukle(servisler, baska, tmp_path, gorunurluk=Gorunurluk.PAYLASILAN)
    s = ogrenci_sohbeti(servisler)
    yanit = servisler["sohbet"].soruSor(s, "Staj defteri ne zaman teslim edilir?")
    assert yanit is not None
    alinti_idler = {r.kaynak_id for r in yanit.kaynaklariGetir()}
    assert paylasilan.kaynak_id not in alinti_idler

    kapsam = servisler["sohbet"]._kapsamiKur(s)
    sorgu = servisler["yz"].gommeUret("staj defteri teslim")
    dizin = servisler["sohbet"].yanit_uretme_servisi.arama_dizini
    sonuclar = dizin.enYakinParcalar(sorgu, 100, kapsam=kapsam)
    assert all(s.parca.kaynak_id != paylasilan.kaynak_id for s in sonuclar)


def test_kapsam_baskasinin_ozelini_gormez(servisler, tmp_path):
    baska = _baska_ogrenci(servisler, "baska@universite.edu.tr")
    ozel = _staj_belgesi_yukle(servisler, baska, tmp_path, gorunurluk=Gorunurluk.OZEL)
    ders = servisler["ders_depo"].bulVeYaOlustur("Staj Dersi")
    servisler["ders_depo"].takipEt(servisler["kullanici"].kullanici_id, ders.ders_id)
    s = ogrenci_sohbeti(servisler)
    yanit = servisler["sohbet"].soruSor(s, "Staj defteri ne zaman teslim edilir?")
    assert yanit is not None
    alinti_idler = {r.kaynak_id for r in yanit.kaynaklariGetir()}
    assert ozel.kaynak_id not in alinti_idler

    kapsam = servisler["sohbet"]._kapsamiKur(s)
    sorgu = servisler["yz"].gommeUret("staj defteri teslim")
    dizin = servisler["sohbet"].yanit_uretme_servisi.arama_dizini
    sonuclar = dizin.enYakinParcalar(sorgu, 100, kapsam=kapsam)
    assert all(s.parca.kaynak_id != ozel.kaynak_id for s in sonuclar)


def test_kaynak_rotasi_ders_izolasyonu(servisler, tmp_path):
    from uniasist.entity import KaynakReferansi

    kullanici = servisler["kullanici"]
    kendi = servisler["bilgi_tabani"].belgeleriListele(kullanici.kullanici_id)[0]
    baska = _baska_ogrenci(servisler, "baska@universite.edu.tr", pro=True)

    paylasilan = _staj_belgesi_yukle(servisler, baska, tmp_path, gorunurluk=Gorunurluk.PAYLASILAN)
    ozel = _staj_belgesi_yukle(servisler, baska, tmp_path, gorunurluk=Gorunurluk.OZEL)
    servisler["ders_depo"].takipEt(kullanici.kullanici_id, paylasilan.ders_id)

    sohbet = servisler["sohbet"]
    assert sohbet.kaynagiGoruntule(KaynakReferansi(kaynak_id=kendi.kaynak_id), kullanici) is not None
    assert sohbet.kaynagiGoruntule(KaynakReferansi(kaynak_id=paylasilan.kaynak_id), kullanici) is not None
    assert sohbet.kaynagiGoruntule(KaynakReferansi(kaynak_id=ozel.kaynak_id), kullanici) is None
    assert sohbet.kaynagiGoruntule(KaynakReferansi(kaynak_id=paylasilan.kaynak_id), baska) is not None
    takip_etmeyen = _baska_ogrenci(servisler, "ucuncu@universite.edu.tr")
    assert sohbet.kaynagiGoruntule(KaynakReferansi(kaynak_id=paylasilan.kaynak_id), takip_etmeyen) is None
    assert sohbet.kaynagiGoruntule(KaynakReferansi(kaynak_id=kendi.kaynak_id), None) is None


def test_kapsam_none_tum_parcalar(servisler, tmp_path):
    baska = _baska_ogrenci(servisler, "baska@universite.edu.tr")
    _staj_belgesi_yukle(servisler, baska, tmp_path, gorunurluk=Gorunurluk.OZEL)
    dizin = servisler["sohbet"].yanit_uretme_servisi.arama_dizini
    sorgu = servisler["yz"].gommeUret("staj defteri teslim")
    sonuclar = dizin.enYakinParcalar(sorgu, 10, kapsam=None)
    assert any(s.parca.sahip_id == baska.kullanici_id for s in sonuclar)
