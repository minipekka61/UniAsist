import pytest

import config
from tests.yardimci import SahteYZ, gecici_db
from uniasist.depo.bilgi_kaynagi_deposu import BilgiKaynagiDeposu
from uniasist.entity import Belge, IcerikParcasi
from uniasist.enumlar import KaynakDurumu
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
    bilgi_tabani = BilgiTabaniServisi(depo, isleme, dizin)
    return bilgi_tabani, dizin, depo, yz, db


@pytest.fixture
def belge_dosyasi(tmp_path):
    dosya = tmp_path / "yonetmelik.txt"
    dosya.write_text(UZUN_METIN, encoding="utf-8")
    return str(dosya)


def test_ik24_gecersiz_tur_ve_boyut(servisler, tmp_path):
    bilgi_tabani, dizin, depo, _, _ = servisler
    dosya = tmp_path / "belge.docx"
    dosya.write_text("x", encoding="utf-8")
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeYukle("belge.docx", str(dosya), 100, "Yönetmelik", "Kayıt")
    assert h.value.kural_no_getir() == "IK-24"
    with pytest.raises(IsKuraliIhlaliException):
        bilgi_tabani.belgeYukle("buyuk.txt", str(dosya), config.AZAMI_BELGE_BOYUTU + 1, "B", "K")
    with pytest.raises(IsKuraliIhlaliException):
        bilgi_tabani.belgeYukle("bos-baslik.txt", str(dosya), 100, "", "Kayıt")
    assert bilgi_tabani.belgeleriListele() == []


def test_ik25_bos_txt_pasif_kalir(servisler, tmp_path):
    bilgi_tabani, dizin, depo, _, _ = servisler
    dosya = tmp_path / "bos.txt"
    dosya.write_text("kısa", encoding="utf-8")
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeYukle("bos.txt", str(dosya), 5, "Boş Belge", "Kayıt")
    assert h.value.kural_no_getir() == "IK-25"
    belgeler = bilgi_tabani.belgeleriListele()
    assert len(belgeler) == 1
    assert belgeler[0].durum == KaynakDurumu.PASIF
    assert dizin.enYakinParcalar([0.1] * 512, 5) == []


def test_ik25_bozuk_pdf_pasif_kalir(servisler, tmp_path):
    bilgi_tabani, _, _, _, _ = servisler
    dosya = tmp_path / "bozuk.pdf"
    dosya.write_bytes(b"%PDF-1.4 bozuk icerik")
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeYukle("bozuk.pdf", str(dosya), 100, "Bozuk PDF", "Kayıt")
    assert h.value.kural_no_getir() == "IK-25"
    assert bilgi_tabani.belgeleriListele()[0].durum == KaynakDurumu.PASIF


def test_ik25_kismi_indeksleme_dizinden_temizlenir(servisler, belge_dosyasi):
    bilgi_tabani, dizin, _, yz, _ = servisler
    yz.gomme_hata_sonrasi = 1
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Öğrenci Yönetmeliği", "Kayıt")
    assert h.value.kural_no_getir() == "IK-25"
    assert bilgi_tabani.belgeleriListele()[0].durum == KaynakDurumu.PASIF
    assert dizin.enYakinParcalar(SahteYZ().gommeUret("burs basvurusu ne zaman"), 5) == []


def test_ik25_gecerli_pdf_islenir(servisler, tmp_path):
    bilgi_tabani, dizin, _, _, _ = servisler
    dosya = tmp_path / "gecerli.pdf"
    dosya.write_bytes(pdf_uret("Staj basvurusu icin en az 60 gun calisma sartidir. Staj defteri 15 gun icinde teslim edilir."))
    belge = bilgi_tabani.belgeYukle("gecerli.pdf", str(dosya), dosya.stat().st_size, "Staj Yönergesi", "Staj")
    assert belge.durum == KaynakDurumu.AKTIF
    sonuclar = dizin.enYakinParcalar(SahteYZ().gommeUret("staj calisma sarti"), 5)
    assert len(sonuclar) > 0
    assert "60 gun" in sonuclar[0].parca.metin


def test_ik25_basarili_yukleme_aktif(servisler, belge_dosyasi):
    bilgi_tabani, dizin, depo, yz, _ = servisler
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Öğrenci Yönetmeliği", "Kayıt")
    assert belge.kaynak_id is not None
    assert belge.durum == KaynakDurumu.AKTIF
    belgeler = bilgi_tabani.belgeleriListele()
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
    bilgi_tabani, dizin, _, yz, _ = servisler
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt")
    eski_surum = belge.surum_no
    eski_parca_sayisi = len(dizin.enYakinParcalar(yz.gommeUret("kayit"), 100))

    yeni_dosya = tmp_path / "yeni.txt"
    yeni_dosya.write_text("Burs basvuru tarihi eylul ayinin ilk haftasidir. Basari bursu icin 3.00 ortalama gerekir. " * 5, encoding="utf-8")
    guncel = bilgi_tabani.belgeGuncelle(belge.kaynak_id, "Yönetmelik 2027", "Burs", yeni_dosya_yolu=str(yeni_dosya), yeni_dosya_adi="yeni.txt", yeni_boyut_byte=100)

    assert guncel.surum_no == eski_surum + 1
    assert guncel.baslik == "Yönetmelik 2027" and guncel.kategori == "Burs"
    assert guncel.dosya_adi == "yeni.txt"
    tumu = dizin.enYakinParcalar(yz.gommeUret("burs"), 100)
    assert all(p.parca.surum_no == guncel.surum_no for p in tumu)
    yeni_parca_sayisi = len(dizin.enYakinParcalar(yz.gommeUret("kayit"), 100))
    assert yeni_parca_sayisi < eski_parca_sayisi


def test_ik26_guncelleme_basarisiz_eski_kalir(servisler, belge_dosyasi, tmp_path):
    bilgi_tabani, dizin, depo, yz, _ = servisler
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt")
    eski_sorgu = yz.gommeUret("kayit yenileme")
    eski_sonuc = dizin.enYakinParcalar(eski_sorgu, 100)
    assert len(eski_sonuc) > 0
    eski_sira = eski_sonuc[0].parca.sira

    yz.mod = "gomme_hata"
    yeni_dosya = tmp_path / "yeni.txt"
    yeni_dosya.write_text("Yeni icerik burs kurallari hakkinda. " * 10, encoding="utf-8")
    with pytest.raises(IsKuraliIhlaliException) as h:
        bilgi_tabani.belgeGuncelle(
            belge.kaynak_id, "Yönetmelik 2", "Burs",
            yeni_dosya_yolu=str(yeni_dosya), yeni_dosya_adi="yeni.txt", yeni_boyut_byte=500,
        )
    assert h.value.kural_no_getir() == "IK-25"

    yz.mod = "yanit"
    kalan = dizin.enYakinParcalar(eski_sorgu, 100)
    assert len(kalan) > 0
    assert kalan[0].parca.sira == eski_sira
    belge_son = bilgi_tabani.belgeleriListele()[0]
    assert belge_son.dosya_adi == "yonetmelik.txt"
    assert belge_son.baslik == "Yönetmelik"
    assert dizin.enYakinParcalar(yz.gommeUret("yeni icerik burs"), 100) == [] or all(
        p.parca.surum_no == 1 for p in dizin.enYakinParcalar(yz.gommeUret("yeni icerik burs"), 100)
    )


def test_ik26_sadece_baslik_guncellenirse(servisler, belge_dosyasi):
    bilgi_tabani, dizin, _, yz, _ = servisler
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt")
    onceki = dizin.enYakinParcalar(yz.gommeUret("kayit"), 100)
    guncel = bilgi_tabani.belgeGuncelle(belge.kaynak_id, "Yeni Başlık", "Yeni Kategori")
    assert guncel.baslik == "Yeni Başlık"
    assert guncel.surum_no == belge.surum_no
    sonraki = dizin.enYakinParcalar(yz.gommeUret("kayit"), 100)
    assert len(onceki) == len(sonraki)


def test_ik27_silme_dizinden_kaldirir(servisler, belge_dosyasi):
    bilgi_tabani, dizin, _, yz, _ = servisler
    belge = bilgi_tabani.belgeYukle("yonetmelik.txt", belge_dosyasi, 5000, "Yönetmelik", "Kayıt")
    assert len(dizin.enYakinParcalar(yz.gommeUret("kayit"), 100)) > 0
    bilgi_tabani.belgeSil(belge.kaynak_id)
    assert bilgi_tabani.belgeleriListele() == []
    assert bilgi_tabani.kaynagiGetir(belge.kaynak_id) is None
    assert dizin.enYakinParcalar(yz.gommeUret("kayit"), 100) == []
