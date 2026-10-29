import pytest

import config
from tests.yardimci import SahteYZ, gecici_db
from uniasist.depo.bilgi_kaynagi_deposu import BilgiKaynagiDeposu
from uniasist.depo.ders_deposu import DersDeposu
from uniasist.depo.kullanici_deposu import KullaniciDeposu
from uniasist.entity import Belge, IcerikParcasi, Kullanici
from uniasist.enumlar import Gorunurluk, KaynakDurumu, Rol
from uniasist.hatalar import IsKuraliIhlaliException
from uniasist.servis.arama_dizini import AramaDizini
from uniasist.servis.belge_isleme_servisi import BelgeIslemeServisi
from uniasist.servis.bilgi_tabani_servisi import BilgiTabaniServisi


def pdf_uret(metin):
    icerik = f"BT /F1 12 Tf 72 720 Td ({metin}) Tj ET".encode("latin-1")
    objeler = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(icerik)).encode() + b" >>\nstream\n" + icerik + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, govde in enumerate(objeler, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + govde + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode() + b"\n%%EOF\n"
    return bytes(out)


UZUN_METIN = (
    "Universite ogrenci destek birimi ogrencilerin tum sorularini yanitlar. "
    "Kayit yenileme islemleri her donem basinda ogrenci bilgileri sistemi uzerinden yapilir. "
    "Kayit yenileme icin odenmesi gereken katki payi ogrencinin ogrenim turune gore degisir. "
    "Ders ekleme ve birakma islemleri donemin ilk iki haftasinda yapilabilir. "
    "Ders birakma isleminde ogrencinin danisman onayi zorunludur. "
    "Burs basvurulari her yil eylul ayinin ilk haftasinda alinir. "
    "Basari bursu icin en az 3.00 genel not ortalamasi gerekir. "
    "Yurt basvurulari KYK sistemi uzerinden online yapilir. "
    "Staj basvurusu icin en az 60 gun calisma sarti vardir. "
    "Staj defteri staj bitiminden sonraki 15 gun icinde teslim edilir. "
    "Mezuniyet icin 240 AKTS kredinin tamamlanmis olmasi gerekir. "
    "Cift anadal programina basvurmak icin ilk donem not ortalamasi en az 3.20 olmalidir. "
) * 3


@pytest.fixture
def servisler():
    db = gecici_db()
    yz = SahteYZ()
    dizin = AramaDizini(db)
    isleme = BelgeIslemeServisi(dizin, yz)
    depo = BilgiKaynagiDeposu(db)
    bilgi_tabani = BilgiTabaniServisi(depo, isleme, dizin, DersDeposu(db))
    return bilgi_tabani, dizin, depo, yz, db


@pytest.fixture
def belge_dosyasi(tmp_path):
    dosya = tmp_path / "yonetmelik.txt"
    dosya.write_text(UZUN_METIN, encoding="utf-8")
    return str(dosya)


def ogrenci_olustur(db, eposta="ali@universite.edu.tr", bolum="Bilgisayar Mühendisliği",
                    universite_id=1, dogrulanmis=True):
    depo = KullaniciDeposu(db)
    k = Kullanici(
        ad_soyad="Öğrenci",
        eposta=eposta,
        sifre_hash="x",
        rol=Rol.OGRENCI,
        universite_id=universite_id,
        bolum=bolum,
        eposta_dogrulandi=dogrulanmis,
    )
    depo.kaydet(k)
    return k


def test_ik24_gecersiz_tur_ve_boyut(servisler, tmp_path):
    bilgi_tabani, dizin, depo, _, db = servisler
    ogr = ogrenci_olustur(db)
    dosya = tmp_path / "belge.docx"
    dosya.write_text("x", encoding="utf-8")
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeYukle("belge.docx", str(dosya), 100, "Yönetmelik", "Kayıt", sahip=ogr)
    assert h.value.kural_no_getir() == "IK-24"
    with pytest.raises(IsKuraliIhlaliException):
        bilgi_tabani.belgeYukle("buyuk.txt", str(dosya), config.AZAMI_BELGE_BOYUTU + 1, "B", "K", sahip=ogr)
    with pytest.raises(IsKuraliIhlaliException):
        bilgi_tabani.belgeYukle("bos-baslik.txt", str(dosya), 100, "", "Kayıt", sahip=ogr)
    assert bilgi_tabani.belgeleriListele(ogr.kullanici_id) == []


def test_ik25_bos_txt_pasif_kalir(servisler, tmp_path):
    bilgi_tabani, dizin, depo, _, db = servisler
    ogr = ogrenci_olustur(db)
    dosya = tmp_path / "bos.txt"
    dosya.write_text("kısa", encoding="utf-8")
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeYukle("bos.txt", str(dosya), 5, "Boş Belge", "Kayıt", sahip=ogr)
    assert h.value.kural_no_getir() == "IK-25"
    belgeler = bilgi_tabani.belgeleriListele(ogr.kullanici_id)
    assert len(belgeler) == 1
    assert belgeler[0].durum == KaynakDurumu.PASIF
    assert dizin.enYakinParcalar([0.1] * 512, 5) == []


def test_ik25_bozuk_pdf_pasif_kalir(servisler, tmp_path):
    bilgi_tabani, _, _, _, db = servisler
    ogr = ogrenci_olustur(db)
    dosya = tmp_path / "bozuk.pdf"
    dosya.write_bytes(b"%PDF-1.4 bozuk icerik")
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeYukle("bozuk.pdf", str(dosya), 100, "Bozuk PDF", "Kayıt", sahip=ogr)
    assert h.value.kural_no_getir() == "IK-25"
    assert bilgi_tabani.belgeleriListele(ogr.kullanici_id)[0].durum == KaynakDurumu.PASIF


def test_ik25_kismi_indeksleme_dizinden_temizlenir(servisler, belge_dosyasi):
    bilgi_tabani, dizin, _, yz, db = servisler
    ogr = ogrenci_olustur(db)
    yz.gomme_hata_sonrasi = 1
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Öğrenci Yönetmeliği", "Kayıt", sahip=ogr)
    assert h.value.kural_no_getir() == "IK-25"
    assert bilgi_tabani.belgeleriListele(ogr.kullanici_id)[0].durum == KaynakDurumu.PASIF
    assert dizin.enYakinParcalar(SahteYZ().gommeUret("burs basvurusu ne zaman"), 5) == []


def test_ik25_gecerli_pdf_islenir(servisler, tmp_path):
    bilgi_tabani, dizin, _, _, db = servisler
    ogr = ogrenci_olustur(db)
    dosya = tmp_path / "gecerli.pdf"
    dosya.write_bytes(pdf_uret("Staj basvurusu icin en az 60 gun calisma sartidir. Staj defteri 15 gun icinde teslim edilir."))
    belge = bilgi_tabani.belgeYukle("gecerli.pdf", str(dosya), dosya.stat().st_size, "Staj Yönergesi", "Staj", sahip=ogr)
    assert belge.durum == KaynakDurumu.AKTIF
    sonuclar = dizin.enYakinParcalar(SahteYZ().gommeUret("staj calisma sarti"), 5)
    assert len(sonuclar) > 0
    assert "60 gun" in sonuclar[0].parca.metin


def test_ik25_basarili_yukleme_aktif(servisler, belge_dosyasi):
    bilgi_tabani, dizin, depo, yz, db = servisler
    ogr = ogrenci_olustur(db)
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Öğrenci Yönetmeliği", "Kayıt", sahip=ogr)
    assert belge.kaynak_id is not None
    assert belge.durum == KaynakDurumu.AKTIF
    belgeler = bilgi_tabani.belgeleriListele(ogr.kullanici_id)
    assert len(belgeler) == 1 and belgeler[0].baslik == "Öğrenci Yönetmeliği"
    sonuclar = dizin.enYakinParcalar(yz.gommeUret("burs basvurusu ne zaman"), 5)
    assert len(sonuclar) > 0
    ilk = sonuclar[0].parca
    assert ilk.kaynak_id == belge.kaynak_id
    assert ilk.kaynak_adi == "yonetmelik.txt"
    assert ilk.bolumBilgisiGetir() == f"Öğrenci Yönetmeliği — parça {ilk.sira}"
    assert ilk.gomme_saglayici == "sahte:test"


def test_parcalama_boyut_ve_ortusme():
    db = gecici_db()
    isleme = BelgeIslemeServisi(AramaDizini(db), SahteYZ())
    parcalar = isleme.parcalaraBol(UZUN_METIN)
    assert len(parcalar) >= 3
    for p in parcalar:
        assert len(p.metin) <= config.PARCA_BOYUTU + 250
    cumleler_0 = set(parcalar[0].metin.split(". "))
    cumleler_1 = set(parcalar[1].metin.split(". "))
    assert cumleler_0 & cumleler_1
    assert [p.sira for p in parcalar] == list(range(1, len(parcalar) + 1))


def test_ik26_guncelleme_basarili_yeni_surum(servisler, belge_dosyasi, tmp_path):
    bilgi_tabani, dizin, _, yz, db = servisler
    ogr = ogrenci_olustur(db)
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt", sahip=ogr)
    eski_surum = belge.surum_no
    eski_parca_sayisi = len(dizin.enYakinParcalar(yz.gommeUret("kayit"), 100))

    yeni_dosya = tmp_path / "yeni.txt"
    yeni_dosya.write_text("Burs basvuru tarihi eylul ayinin ilk haftasidir. Basari bursu icin 3.00 ortalama gerekir. " * 5, encoding="utf-8")
    guncel = bilgi_tabani.belgeGuncelle(
        belge.kaynak_id, ogr.kullanici_id, "Yönetmelik 2027", "Burs",
        yeni_dosya_yolu=str(yeni_dosya), yeni_dosya_adi="yeni.txt", yeni_boyut_byte=100,
    )

    assert guncel.surum_no == eski_surum + 1
    assert guncel.baslik == "Yönetmelik 2027" and guncel.kategori == "Burs"
    assert guncel.dosya_adi == "yeni.txt"
    tumu = dizin.enYakinParcalar(yz.gommeUret("burs"), 100)
    assert all(p.parca.surum_no == guncel.surum_no for p in tumu)
    yeni_parca_sayisi = len(dizin.enYakinParcalar(yz.gommeUret("kayit"), 100))
    assert yeni_parca_sayisi < eski_parca_sayisi


def test_ik26_guncelleme_basarisiz_eski_kalir(servisler, belge_dosyasi, tmp_path):
    bilgi_tabani, dizin, depo, yz, db = servisler
    ogr = ogrenci_olustur(db)
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt", sahip=ogr)
    eski_sorgu = yz.gommeUret("kayit yenileme")
    eski_sonuc = dizin.enYakinParcalar(eski_sorgu, 100)
    assert len(eski_sonuc) > 0
    eski_sira = eski_sonuc[0].parca.sira

    yz.mod = "gomme_hata"
    yeni_dosya = tmp_path / "yeni.txt"
    yeni_dosya.write_text("Yeni icerik burs kurallari hakkinda. " * 10, encoding="utf-8")
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeGuncelle(
            belge.kaynak_id, ogr.kullanici_id, "Yönetmelik 2", "Burs",
            yeni_dosya_yolu=str(yeni_dosya), yeni_dosya_adi="yeni.txt", yeni_boyut_byte=500,
        )
    assert h.value.kural_no_getir() == "IK-25"

    yz.mod = "yanit"
    kalan = dizin.enYakinParcalar(eski_sorgu, 100)
    assert len(kalan) > 0
    assert kalan[0].parca.sira == eski_sira
    belge_son = bilgi_tabani.belgeleriListele(ogr.kullanici_id)[0]
    assert belge_son.dosya_adi == "yonetmelik.txt"
    assert belge_son.baslik == "Yönetmelik"
    assert dizin.enYakinParcalar(yz.gommeUret("yeni icerik burs"), 100) == [] or all(
        p.parca.surum_no == 1 for p in dizin.enYakinParcalar(yz.gommeUret("yeni icerik burs"), 100)
    )


def test_ik26_sadece_baslik_guncellenirse(servisler, belge_dosyasi):
    bilgi_tabani, dizin, _, yz, db = servisler
    ogr = ogrenci_olustur(db)
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt", sahip=ogr)
    onceki = dizin.enYakinParcalar(yz.gommeUret("kayit"), 100)
    guncel = bilgi_tabani.belgeGuncelle(belge.kaynak_id, ogr.kullanici_id, "Yeni Başlık", "Yeni Kategori")
    assert guncel.baslik == "Yeni Başlık"
    assert guncel.surum_no == belge.surum_no
    sonraki = dizin.enYakinParcalar(yz.gommeUret("kayit"), 100)
    assert len(onceki) == len(sonraki)


def test_ik27_silme_dizinden_kaldirir(servisler, belge_dosyasi):
    bilgi_tabani, dizin, _, yz, db = servisler
    ogr = ogrenci_olustur(db)
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt", sahip=ogr)
    assert len(dizin.enYakinParcalar(yz.gommeUret("kayit"), 100)) > 0
    bilgi_tabani.belgeSil(belge.kaynak_id, ogr.kullanici_id)
    assert bilgi_tabani.belgeleriListele(ogr.kullanici_id) == []
    assert bilgi_tabani.kaynagiGetir(belge.kaynak_id) is None
    assert dizin.enYakinParcalar(yz.gommeUret("kayit"), 100) == []


def test_belge_sahiplik_alanlari_atanir(servisler, belge_dosyasi):
    bilgi_tabani, dizin, _, _, db = servisler
    ogr = ogrenci_olustur(db)
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt", sahip=ogr)
    assert belge.sahip_id == ogr.kullanici_id
    assert belge.universite_id == ogr.universite_id
    assert belge.bolum == ogr.bolum
    assert belge.gorunurluk == Gorunurluk.OZEL
    for parca in dizin.parcalar:
        if parca.kaynak_id == belge.kaynak_id:
            assert parca.sahip_id == ogr.kullanici_id
            assert parca.gorunurluk == Gorunurluk.OZEL
            assert parca.universite_id == ogr.universite_id
            assert parca.bolum == ogr.bolum


def test_ik29_dogrulanmamis_paylasamaz(servisler, belge_dosyasi):
    bilgi_tabani, _, _, _, db = servisler
    ogr = ogrenci_olustur(db, dogrulanmis=False)
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeYukle(
            "yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt",
            sahip=ogr, gorunurluk=Gorunurluk.PAYLASILAN,
        )
    assert h.value.kural_no_getir() == "IK-29"
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt", sahip=ogr)
    assert belge.durum == KaynakDurumu.AKTIF
    assert belge.gorunurluk == Gorunurluk.OZEL


def test_ik30_baskasi_belgeyi_guncelleyemez(servisler, belge_dosyasi):
    bilgi_tabani, _, _, _, db = servisler
    ogr = ogrenci_olustur(db)
    baska = ogrenci_olustur(db, eposta="baska@universite.edu.tr")
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt", sahip=ogr)
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeGuncelle(belge.kaynak_id, baska.kullanici_id, "Başkası", "Burs")
    assert h.value.kural_no_getir() == "IK-30"


def test_ik30_baskasi_belgeyi_silemez(servisler, belge_dosyasi):
    bilgi_tabani, _, _, _, db = servisler
    ogr = ogrenci_olustur(db)
    baska = ogrenci_olustur(db, eposta="baska@universite.edu.tr")
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt", sahip=ogr)
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeSil(belge.kaynak_id, baska.kullanici_id)
    assert h.value.kural_no_getir() == "IK-30"
    assert bilgi_tabani.belgeleriListele(ogr.kullanici_id) != []


def test_gorunurluk_degisimi_parcalara_yansir(servisler, belge_dosyasi):
    bilgi_tabani, dizin, _, _, db = servisler
    ogr = ogrenci_olustur(db)
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt", sahip=ogr)
    bilgi_tabani.gorunurlukDegistir(belge.kaynak_id, ogr, Gorunurluk.PAYLASILAN)
    assert bilgi_tabani.belgeleriListele(ogr.kullanici_id)[0].gorunurluk == Gorunurluk.PAYLASILAN
    taze_dizin = AramaDizini(bilgi_tabani.bilgi_kaynagi_deposu.db)
    paylasilan = [
        p for p in taze_dizin.parcalar if p.kaynak_id == belge.kaynak_id
    ]
    assert paylasilan
    assert all(p.gorunurluk == Gorunurluk.PAYLASILAN for p in paylasilan)
    bilgi_tabani.gorunurlukDegistir(belge.kaynak_id, ogr, Gorunurluk.OZEL)
    taze_dizin2 = AramaDizini(bilgi_tabani.bilgi_kaynagi_deposu.db)
    assert all(
        p.gorunurluk == Gorunurluk.OZEL
        for p in taze_dizin2.parcalar if p.kaynak_id == belge.kaynak_id
    )


def test_ik29_dogrulanmamis_gorunurluk_degistiremez(servisler, belge_dosyasi):
    bilgi_tabani, _, _, _, db = servisler
    ogr = ogrenci_olustur(db, dogrulanmis=False)
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt", sahip=ogr)
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.gorunurlukDegistir(belge.kaynak_id, ogr, Gorunurluk.PAYLASILAN)
    assert h.value.kural_no_getir() == "IK-29"


def test_bolumun_paylasilanlari_listeler(servisler, belge_dosyasi, tmp_path):
    bilgi_tabani, _, _, _, db = servisler
    ogr_a = ogrenci_olustur(db, eposta="a@u.edu.tr", bolum="Bilgisayar Mühendisliği", universite_id=1)
    ogr_b = ogrenci_olustur(db, eposta="b@u.edu.tr", bolum="Hukuk", universite_id=1)
    ogr_c = ogrenci_olustur(db, eposta="c@diger.edu.tr", bolum="Bilgisayar Mühendisliği", universite_id=2)

    paylasilan = bilgi_tabani.belgeYukle(
        "p.txt", belge_dosyasi, 5000, "Paylaşılan Yönetmelik", "Kayıt",
        sahip=ogr_a, gorunurluk=Gorunurluk.PAYLASILAN, ders_adi="Matematik I",
    )
    bilgi_tabani.belgeYukle("o.txt", belge_dosyasi, 5000, "Özel Yönetmelik", "Kayıt", sahip=ogr_a)
    baska_bolum_paylasilan = bilgi_tabani.belgeYukle(
        "h.txt", belge_dosyasi, 5000, "Hukuk Notları", "Hukuk",
        sahip=ogr_b, gorunurluk=Gorunurluk.PAYLASILAN, ders_adi="Hukuka Giriş",
    )
    baska_universite = bilgi_tabani.belgeYukle(
        "d.txt", belge_dosyasi, 5000, "Diğer Üniversite", "Kayıt",
        sahip=ogr_c, gorunurluk=Gorunurluk.PAYLASILAN, ders_adi="Matematik I",
    )

    liste = bilgi_tabani.bolumunPaylasilanlari(1, "Bilgisayar Mühendisliği")
    kaynaklar = {b.kaynak_id for b in liste}
    assert paylasilan.kaynak_id in kaynaklar
    assert baska_bolum_paylasilan.kaynak_id not in kaynaklar
    assert baska_universite.kaynak_id not in kaynaklar
    assert bilgi_tabani.bolumunPaylasilanlari(2, "Hukuk") == []


def test_belge_ders_etiketi_atanir(servisler, belge_dosyasi):
    bilgi_tabani, dizin, _, _, db = servisler
    ogr = ogrenci_olustur(db)
    belge = bilgi_tabani.belgeYukle(
        "yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt",
        sahip=ogr, ders_adi="Matematik I",
    )
    ders = DersDeposu(db).adIleBul("matematik i")
    assert ders is not None
    assert belge.ders_id == ders.ders_id
    parcalar = [p for p in dizin.parcalar if p.kaynak_id == belge.kaynak_id]
    assert parcalar
    assert all(p.ders_id == ders.ders_id for p in parcalar)


def test_paylasilan_belge_ders_ister(servisler, belge_dosyasi):
    bilgi_tabani, _, _, _, db = servisler
    ogr = ogrenci_olustur(db)
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeYukle(
            "yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt",
            sahip=ogr, gorunurluk=Gorunurluk.PAYLASILAN,
        )
    assert h.value.kural_no_getir() == "IK-24"


def test_belge_ders_degistirilebilir(servisler, belge_dosyasi):
    bilgi_tabani, dizin, _, _, db = servisler
    ogr = ogrenci_olustur(db)
    belge = bilgi_tabani.belgeYukle(
        "yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt",
        sahip=ogr, ders_adi="Matematik I",
    )
    bilgi_tabani.belgeGuncelle(
        belge.kaynak_id, ogr.kullanici_id, "Yönetmelik", "Kayıt",
        yeni_ders_adi="Fizik I",
    )
    ders_depo = DersDeposu(db)
    fizik = ders_depo.adIleBul("Fizik I")
    assert fizik is not None
    taze = bilgi_tabani.kaynagiGetir(belge.kaynak_id)
    assert taze.ders_id == fizik.ders_id
    parcalar = [p for p in AramaDizini(db).parcalar if p.kaynak_id == belge.kaynak_id]
    assert parcalar
    assert all(p.ders_id == fizik.ders_id for p in parcalar)


def test_dersin_paylasilanlari_listeler(servisler, belge_dosyasi):
    bilgi_tabani, _, _, _, db = servisler
    ogr_a = ogrenci_olustur(db, eposta="a@u.edu.tr")
    ogr_b = ogrenci_olustur(db, eposta="b@u.edu.tr")

    mat_paylasilan = bilgi_tabani.belgeYukle(
        "p.txt", belge_dosyasi, 5000, "Mat Paylaşılan", "Kayıt",
        sahip=ogr_a, gorunurluk=Gorunurluk.PAYLASILAN, ders_adi="Matematik I",
    )
    fizik_paylasilan = bilgi_tabani.belgeYukle(
        "f.txt", belge_dosyasi, 5000, "Fizik Paylaşılan", "Kayıt",
        sahip=ogr_a, gorunurluk=Gorunurluk.PAYLASILAN, ders_adi="Fizik I",
    )
    mat_ozel = bilgi_tabani.belgeYukle(
        "o.txt", belge_dosyasi, 5000, "Mat Özel", "Kayıt",
        sahip=ogr_b, ders_adi="Matematik I",
    )

    ders_depo = DersDeposu(db)
    mat = ders_depo.adIleBul("Matematik I")
    liste = bilgi_tabani.dersinPaylasilanlari(mat.ders_id)
    kaynaklar = {b.kaynak_id for b in liste}
    assert mat_paylasilan.kaynak_id in kaynaklar
    assert fizik_paylasilan.kaynak_id not in kaynaklar
    assert mat_ozel.kaynak_id not in kaynaklar
