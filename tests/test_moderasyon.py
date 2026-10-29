import pytest

from tests.yardimci import SahteYZ, gecici_db
from uniasist.depo.bilgi_kaynagi_deposu import BilgiKaynagiDeposu
from uniasist.depo.bildirim_deposu import BildirimDeposu
from uniasist.depo.kullanici_deposu import KullaniciDeposu
from uniasist.entity import Kullanici
from uniasist.enumlar import Gorunurluk, KayitDurumu, Rol
from uniasist.hatalar import IsKuraliIhlaliException
from uniasist.servis.arama_dizini import AramaDizini
from uniasist.servis.belge_isleme_servisi import BelgeIslemeServisi
from uniasist.servis.bilgi_tabani_servisi import BilgiTabaniServisi
from uniasist.servis.moderasyon_servisi import ModerasyonServisi

STAJ_METNI = (
    "Staj yonergesi ogrencilerin yaz stajlarini duzenler ve zorunlu kilar. "
    "Staj basvurusu icin en az 60 gun kesintisiz calisma sarti vardir. "
    "Staj defteri staj bitiminden sonraki 15 gun icinde teslim edilir. "
    "Staj degerlendirme formu isyeri yetkilisi tarafindan doldurulur. "
) * 3


def ogrenci_olustur(db, eposta, bolum="Bilgisayar Mühendisliği", universite_id=1):
    depo = KullaniciDeposu(db)
    k = Kullanici(
        ad_soyad="Öğrenci",
        eposta=eposta,
        sifre_hash="x",
        rol=Rol.OGRENCI,
        universite_id=universite_id,
        bolum=bolum,
        eposta_dogrulandi=True,
    )
    depo.kaydet(k)
    return k


@pytest.fixture
def ortam(tmp_path):
    db = gecici_db()
    yz = SahteYZ()
    dizin = AramaDizini(db)
    isleme = BelgeIslemeServisi(dizin, yz)
    bilgi_depo = BilgiKaynagiDeposu(db)
    bilgi_tabani = BilgiTabaniServisi(bilgi_depo, isleme, dizin)
    bildirim_depo = BildirimDeposu(db)
    moderasyon = ModerasyonServisi(bildirim_depo, bilgi_tabani)

    sahip = ogrenci_olustur(db, "sahip@universite.edu.tr")
    baska = ogrenci_olustur(db, "baska@universite.edu.tr")

    dosya = tmp_path / "staj.txt"
    dosya.write_text(STAJ_METNI, encoding="utf-8")
    paylasilan = bilgi_tabani.belgeYukle(
        "staj.txt", str(dosya), 1000, "Staj Yönergesi", "Staj",
        sahip=sahip, gorunurluk=Gorunurluk.PAYLASILAN,
    )
    return {
        "db": db,
        "bilgi_tabani": bilgi_tabani,
        "moderasyon": moderasyon,
        "bildirim_depo": bildirim_depo,
        "sahip": sahip,
        "baska": baska,
        "paylasilan": paylasilan,
    }


def test_bildir_paylasilan_belge(ortam):
    bildirim = ortam["moderasyon"].bildir(
        ortam["paylasilan"].kaynak_id, ortam["baska"], "Uygunsuz içerik"
    )
    assert bildirim.bildirim_id is not None
    assert bildirim.durum == KayitDurumu.ACIK
    assert bildirim.neden == "Uygunsuz içerik"
    aciklar = ortam["moderasyon"].acikBildirimler()
    assert len(aciklar) == 1
    bildirim_, belge = aciklar[0]
    assert belge.kaynak_id == ortam["paylasilan"].kaynak_id


def test_ik31_paylasilmayan_belge_bildirilemez(ortam, tmp_path):
    ozel_dosya = tmp_path / "ozel.txt"
    ozel_dosya.write_text(STAJ_METNI, encoding="utf-8")
    ozel = ortam["bilgi_tabani"].belgeYukle(
        "ozel.txt", str(ozel_dosya), 1000, "Özel", "Staj",
        sahip=ortam["sahip"],
    )
    with pytest.raises(IsKuraliIhlaliException) as h:
        ortam["moderasyon"].bildir(ozel.kaynak_id, ortam["baska"], "Deneme")
    assert h.value.kural_no_getir() == "IK-31"


def test_ik31_ayni_kisi_tek_bildirim(ortam):
    ortam["moderasyon"].bildir(ortam["paylasilan"].kaynak_id, ortam["baska"], "Birinci")
    with pytest.raises(IsKuraliIhlaliException) as h:
        ortam["moderasyon"].bildir(ortam["paylasilan"].kaynak_id, ortam["baska"], "İkinci")
    assert h.value.kural_no_getir() == "IK-31"


def test_ik31_kendi_belgesi_bildirilemez(ortam):
    with pytest.raises(IsKuraliIhlaliException) as h:
        ortam["moderasyon"].bildir(ortam["paylasilan"].kaynak_id, ortam["sahip"], "Kendi belgem")
    assert h.value.kural_no_getir() == "IK-31"


def test_degerlendir_sil(ortam):
    bildirim = ortam["moderasyon"].bildir(
        ortam["paylasilan"].kaynak_id, ortam["baska"], "Uygunsuz"
    )
    ortam["moderasyon"].bildirimiDegerlendir(bildirim.bildirim_id, silinsin=True)
    assert ortam["moderasyon"].acikBildirimler() == []
    assert ortam["bilgi_tabani"].kaynagiGetir(ortam["paylasilan"].kaynak_id) is None
    assert ortam["bildirim_depo"].idIleBul(bildirim.bildirim_id).durum == KayitDurumu.DEGERLENDIRILDI


def test_degerlendir_yoksay(ortam):
    bildirim = ortam["moderasyon"].bildir(
        ortam["paylasilan"].kaynak_id, ortam["baska"], "Yanlış anlaşılmış"
    )
    ortam["moderasyon"].bildirimiDegerlendir(bildirim.bildirim_id, silinsin=False)
    assert ortam["moderasyon"].acikBildirimler() == []
    assert ortam["bilgi_tabani"].kaynagiGetir(ortam["paylasilan"].kaynak_id) is not None
    assert ortam["bildirim_depo"].idIleBul(bildirim.bildirim_id).durum == KayitDurumu.DEGERLENDIRILDI


def test_ik31_baska_bolum_belgeyi_bildiremez(ortam):
    baska_bolum = ogrenci_olustur(ortam["db"], "hukuk@universite.edu.tr", bolum="Hukuk")
    with pytest.raises(IsKuraliIhlaliException) as h:
        ortam["moderasyon"].bildir(
            ortam["paylasilan"].kaynak_id, baska_bolum, "Deneme"
        )
    assert h.value.kural_no_getir() == "IK-31"
    assert h.value.mesaj == "Belge bulunamadı."


def test_ik31_baska_universite_belgeyi_bildiremez(ortam):
    baska_universite = ogrenci_olustur(
        ortam["db"], "baska@itu.edu.tr", universite_id=2
    )
    with pytest.raises(IsKuraliIhlaliException) as h:
        ortam["moderasyon"].bildir(
            ortam["paylasilan"].kaynak_id, baska_universite, "Deneme"
        )
    assert h.value.kural_no_getir() == "IK-31"
    assert h.value.mesaj == "Belge bulunamadı."


def test_ik32_karar_verilen_bildirim_tekrar_degerlendirilemez(ortam):
    bildirim = ortam["moderasyon"].bildir(
        ortam["paylasilan"].kaynak_id, ortam["baska"], "Uygunsuz"
    )
    ortam["moderasyon"].bildirimiDegerlendir(bildirim.bildirim_id, silinsin=False)
    with pytest.raises(IsKuraliIhlaliException) as h:
        ortam["moderasyon"].bildirimiDegerlendir(bildirim.bildirim_id, silinsin=True)
    assert h.value.kural_no_getir() == "IK-32"
    assert ortam["bilgi_tabani"].kaynagiGetir(ortam["paylasilan"].kaynak_id) is not None
