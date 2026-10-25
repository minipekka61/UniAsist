from datetime import datetime, timedelta

from tests.yardimci import gecici_db
from uniasist.depo.bilgi_kaynagi_deposu import BilgiKaynagiDeposu
from uniasist.depo.geri_bildirim_deposu import GeriBildirimDeposu
from uniasist.depo.kullanici_deposu import KullaniciDeposu
from uniasist.depo.soru_kaydi_deposu import SoruKaydiDeposu
from uniasist.depo.sohbet_deposu import SohbetDeposu
from uniasist.depo.yanitlanamayan_soru_deposu import YanitlanamayanSoruDeposu
from uniasist.entity import (
    Belge,
    GeriBildirim,
    KaynakReferansi,
    Kullanici,
    Mesaj,
    SSSGirdisi,
    Sohbet,
    SoruKaydi,
    YanitlanamayanSoru,
)
from uniasist.enumlar import (
    GeriBildirimTuru,
    GonderenTuru,
    KayitDurumu,
    KaynakDurumu,
    Rol,
)
from uniasist.guvenlik import sifre_hashle


def kullanici(eposta="ali@universite.edu.tr", rol=Rol.OGRENCI):
    return Kullanici(
        ad_soyad="Ali Veli",
        eposta=eposta,
        sifre_hash=sifre_hashle("Gizli1234"),
        rol=rol,
    )


def test_kullanici_roundtrip():
    db = gecici_db()
    depo = KullaniciDeposu(db)
    k = kullanici()
    depo.kaydet(k)
    assert k.kullanici_id is not None

    bulunan = depo.epostaIleBul("ali@universite.edu.tr")
    assert bulunan is not None
    assert bulunan.kullanici_id == k.kullanici_id
    assert bulunan.ad_soyad == "Ali Veli"
    assert bulunan.rol == Rol.OGRENCI
    assert bulunan.sifre_hash.startswith("pbkdf2_sha256$")

    assert depo.idIleBul(k.kullanici_id).eposta == "ali@universite.edu.tr"
    assert depo.epostaVarMi("ali@universite.edu.tr")
    assert not depo.epostaVarMi("baska@universite.edu.tr")
    assert depo.ara("ali") != []
    assert depo.aktifYoneticiSayisi() == 0

    k.rolDegistir(Rol.YONETICI)
    depo.kaydet(k)
    assert depo.aktifYoneticiSayisi() == 1
    assert depo.epostaIleBul("ali@universite.edu.tr").rol == Rol.YONETICI


def test_sohbet_kaydet_mesajlarla():
    db = gecici_db()
    kullanici_depo = KullaniciDeposu(db)
    depo = SohbetDeposu(db)
    k = kullanici()
    kullanici_depo.kaydet(k)

    simdi = datetime.now()
    s = Sohbet(baslik="Burs sorusu", olusturma_zamani=simdi, kullanici_id=k.kullanici_id)
    soru = Mesaj(gonderen=GonderenTuru.KULLANICI, metin="Burs ne zaman yatıyor?", zaman=simdi)
    yanit = Mesaj(gonderen=GonderenTuru.SISTEM, metin="Her ayın 5'inde.", zaman=simdi)
    yanit.kaynakEkle(KaynakReferansi(bolum_bilgisi="Burs Yönergesi — parça 1", kaynak_adi="burs.txt", benzerlik_skoru=0.81))
    s.mesajEkle(soru)
    s.mesajEkle(yanit)
    depo.kaydet(s)

    assert s.sohbet_id is not None
    assert soru.mesaj_id is not None and yanit.mesaj_id is not None

    getirilen = depo.idIleBul(s.sohbet_id)
    assert getirilen.baslik == "Burs sorusu"
    assert len(getirilen.mesajlar) == 2
    assert getirilen.mesajlar[0].metin == "Burs ne zaman yatıyor?"
    yanit_getirilen = [m for m in getirilen.mesajlar if m.gonderen == GonderenTuru.SISTEM][0]
    kaynaklar = yanit_getirilen.kaynaklariGetir()
    assert len(kaynaklar) == 1
    assert kaynaklar[0].kaynak_adi == "burs.txt"
    assert kaynaklar[0].benzerlik_skoru == 0.81

    assert depo.mesajBul(yanit.mesaj_id).metin == "Her ayın 5'inde."
    liste = depo.kullaniciSohbetleri(k.kullanici_id)
    assert len(liste) == 1

    depo.kaydet(s)
    assert len(depo.kullaniciSohbetleri(k.kullanici_id)) == 1


def test_sohbet_sil_kaskat():
    db = gecici_db()
    kullanici_depo = KullaniciDeposu(db)
    depo = SohbetDeposu(db)
    k = kullanici()
    kullanici_depo.kaydet(k)
    s = Sohbet(baslik="b", olusturma_zamani=datetime.now(), kullanici_id=k.kullanici_id)
    m = Mesaj(gonderen=GonderenTuru.KULLANICI, metin="soru", zaman=datetime.now())
    m.kaynakEkle(KaynakReferansi(kaynak_adi="a.txt"))
    s.mesajEkle(m)
    depo.kaydet(s)

    depo.sil(s.sohbet_id)
    assert depo.idIleBul(s.sohbet_id) is None
    assert depo.mesajBul(m.mesaj_id) is None

    s2 = Sohbet(baslik="b2", olusturma_zamani=datetime.now(), kullanici_id=k.kullanici_id)
    s2.mesajEkle(Mesaj(gonderen=GonderenTuru.KULLANICI, metin="x", zaman=datetime.now()))
    depo.kaydet(s2)
    depo.kullaniciSohbetleriniSil(k.kullanici_id)
    assert depo.kullaniciSohbetleri(k.kullanici_id) == []


def test_bilgi_kaynagi_tur_ayrimi():
    db = gecici_db()
    depo = BilgiKaynagiDeposu(db)
    b = Belge(baslik="Burs Yönergesi", kategori="Burs", dosya_adi="burs.txt", dosya_turu="txt", boyut_byte=10, dosya_yolu="p")
    s = SSSGirdisi(baslik="SSS", kategori="Burs", soru="Soru?", cevap="Cevap.")
    depo.kaydet(b)
    depo.kaydet(s)

    gelen_b = depo.idIleBul(b.kaynak_id)
    assert isinstance(gelen_b, Belge)
    assert gelen_b.dosya_adi == "burs.txt" and gelen_b.boyut_byte == 10
    gelen_s = depo.idIleBul(s.kaynak_id)
    assert isinstance(gelen_s, SSSGirdisi)
    assert gelen_s.soru == "Soru?" and gelen_s.cevap == "Cevap."

    b.aktifYap()
    depo.kaydet(b)
    assert all(k.aktifMi() for k in depo.aktifKaynaklar())
    assert len(depo.belgeler()) == 1

    depo.sil(b.kaynak_id)
    assert depo.idIleBul(b.kaynak_id) is None


def test_yanitlanamayan_metne_gore_bul():
    db = gecici_db()
    depo = YanitlanamayanSoruDeposu(db)
    y = YanitlanamayanSoru(soru_metni="Yurt başvurusu ne zaman?", ilk_tarih=datetime.now())
    depo.kaydet(y)
    bulunan = depo.metneGoreBul("Yurt başvurusu ne zaman?")
    assert bulunan.kayit_id == y.kayit_id
    assert depo.metneGoreBul("Yok") is None

    y.tekrarArtir()
    depo.kaydet(y)
    assert depo.durumaGoreListele(KayitDurumu.ACIK)[0].tekrar_sayisi == 2

    y.coz()
    depo.kaydet(y)
    assert len(depo.durumaGoreListele(KayitDurumu.ACIK)) == 0
    assert len(depo.durumaGoreListele(KayitDurumu.COZULDU)) == 1


def test_soru_kaydi_aralik():
    db = gecici_db()
    depo = SoruKaydiDeposu(db)
    simdi = datetime.now()
    depo.kaydet(SoruKaydi(zaman=simdi - timedelta(days=40), kategori="Burs", yanitlandi=True))
    depo.kaydet(SoruKaydi(zaman=simdi - timedelta(days=5), kategori="Yurt", yanitlandi=False))
    depo.kaydet(SoruKaydi(zaman=simdi, kategori="Burs", yanitlandi=True))

    kayitlar = depo.araliktakiKayitlar(simdi - timedelta(days=30), simdi + timedelta(days=1))
    assert len(kayitlar) == 2
    assert all(k.zaman >= simdi - timedelta(days=30) for k in kayitlar)


def test_geri_bildirim_yararsizlar_ve_oran():
    db = gecici_db()
    depo = GeriBildirimDeposu(db)
    simdi = datetime.now()
    depo.kaydet(GeriBildirim(mesaj_id=1, kullanici_id=1, tur=GeriBildirimTuru.YARARSIZ, aciklama="yanlış", zaman=simdi))
    depo.kaydet(GeriBildirim(mesaj_id=2, kullanici_id=1, tur=GeriBildirimTuru.YARARLI, aciklama=None, zaman=simdi))
    depo.kaydet(GeriBildirim(mesaj_id=3, kullanici_id=2, tur=GeriBildirimTuru.YARARLI, aciklama=None, zaman=simdi - timedelta(days=40)))

    yararsiz = depo.yararsizlar()
    assert len(yararsiz) == 1 and yararsiz[0].aciklama == "yanlış"
    assert depo.mesajIcininBul(1, 1).tur == GeriBildirimTuru.YARARSIZ
    assert depo.mesajIcininBul(1, 2) is None

    oran = depo.araliktakiOlumluOrani(simdi - timedelta(days=1), simdi + timedelta(days=1))
    assert abs(oran - 0.5) < 1e-9


def test_oturum_kaydet_ve_bul():
    from uniasist.entity import Oturum

    db = gecici_db()
    kullanici_depo = KullaniciDeposu(db)
    k = kullanici()
    kullanici_depo.kaydet(k)
    o = Oturum(oturum_id="tok123", kullanici_id=k.kullanici_id, olusturma_zamani=datetime.now(), son_etkinlik_zamani=datetime.now())
    from uniasist.depo.veritabani import oturum_kaydet, oturum_bul, oturum_sil

    oturum_kaydet(db, o)
    bulunan = oturum_bul(db, "tok123")
    assert bulunan is not None and bulunan.kullanici_id == k.kullanici_id
    o.etkinlikGuncelle()
    oturum_kaydet(db, o)
    assert oturum_bul(db, "tok123").aktif
    oturum_sil(db, "tok123")
    assert oturum_bul(db, "tok123") is None
