import pytest

from tests.yardimci import SahteYZ, gecici_db
from uniasist.entity import Kullanici
from uniasist.enumlar import Rol
from uniasist.guvenlik import sifre_hashle
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


def kullanici_ekle(paket, ad_soyad, eposta, rol, sifre="Gizli1234"):
    kullanici = Kullanici(
        ad_soyad=ad_soyad,
        eposta=eposta,
        sifre_hash=sifre_hashle(sifre),
        rol=rol,
    )
    paket.kimlik.kullanici_deposu.kaydet(kullanici)
    return kullanici


def yonetici_giris_yap(istemci, paket):
    kullanici_ekle(paket, "Yönetici Hanım", "admin@universite.edu.tr", Rol.YONETICI, "Yonetici1234")
    istemci.post("/giris", data={"eposta": "admin@universite.edu.tr", "sifre": "Yonetici1234"})


def soru_kaydi_ekle(paket, kategori, yanitlandi=True, gun_once=0):
    from datetime import datetime, timedelta

    zaman = datetime.now() - timedelta(days=gun_once)
    imlec = paket.db.execute(
        "INSERT INTO soru_kaydi (zaman, kategori, yanitlandi) VALUES (?,?,?)",
        (zaman.isoformat(), kategori, 1 if yanitlandi else 0),
    )
    return imlec.lastrowid


def test_uc20_liste_ve_arama(ortam):
    istemci, paket = ortam
    yonetici_giris_yap(istemci, paket)
    kullanici_ekle(paket, "Ali Veli", "ali@universite.edu.tr", Rol.OGRENCI)
    kullanici_ekle(paket, "Ayşe Can", "ayse@universite.edu.tr", Rol.OGRENCI)

    yanit = istemci.get("/yonetici/kullanicilar")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "Ali Veli" in metin
    assert "Ayşe Can" in metin
    assert "ali@universite.edu.tr" in metin
    assert "Kayıt Tarihi" in metin or "kayıt" in metin.lower()

    yanit = istemci.get("/yonetici/kullanicilar?q=Ayşe")
    metin = yanit.get_data(as_text=True)
    assert "Ayşe Can" in metin
    assert "Ali Veli" not in metin


def test_uc21_rol_degistirme(ortam):
    istemci, paket = ortam
    yonetici = None
    yonetici_giris_yap(istemci, paket)
    yonetici = paket.kimlik.kullanici_deposu.epostaIleBul("admin@universite.edu.tr")
    ali = kullanici_ekle(paket, "Ali Veli", "ali@universite.edu.tr", Rol.OGRENCI)

    yanit = istemci.post(
        f"/yonetici/kullanicilar/{ali.kullanici_id}/rol",
        data={"yeni_rol": "PERSONEL"},
        follow_redirects=True,
    )
    assert yanit.status_code == 200
    assert "güncellendi" in yanit.get_data(as_text=True)
    assert paket.kimlik.kullanici_deposu.idIleBul(ali.kullanici_id).rol == Rol.PERSONEL

    yanit = istemci.post(
        f"/yonetici/kullanicilar/{yonetici.kullanici_id}/rol",
        data={"yeni_rol": "PERSONEL"},
        follow_redirects=True,
    )
    assert yanit.status_code == 200
    assert "kendi rolünü" in yanit.get_data(as_text=True)
    assert paket.kimlik.kullanici_deposu.idIleBul(yonetici.kullanici_id).rol == Rol.YONETICI


def test_uc22_devre_disi_birakma(ortam):
    istemci, paket = ortam
    yonetici_giris_yap(istemci, paket)
    ali = kullanici_ekle(paket, "Ali Veli", "ali@universite.edu.tr", Rol.OGRENCI)
    istemci.post("/giris", data={"eposta": "ali@universite.edu.tr", "sifre": "Gizli1234"})
    istemci.post("/giris", data={"eposta": "admin@universite.edu.tr", "sifre": "Yonetici1234"})

    yanit = istemci.post(
        f"/yonetici/kullanicilar/{ali.kullanici_id}/devre-disi",
        follow_redirects=True,
    )
    assert yanit.status_code == 200
    hedef = paket.kimlik.kullanici_deposu.idIleBul(ali.kullanici_id)
    assert not hedef.aktifMi()
    oturumlar = paket.db.execute(
        "SELECT aktif FROM oturum WHERE kullanici_id=?", (ali.kullanici_id,)
    ).fetchall()
    assert oturumlar and all(o["aktif"] == 0 for o in oturumlar)

    from uniasist.enumlar import HesapDurumu

    ikinci = Kullanici(
        ad_soyad="Yönetici İki",
        eposta="admin2@universite.edu.tr",
        sifre_hash=sifre_hashle("Yonetici1234"),
        rol=Rol.YONETICI,
        durum=HesapDurumu.DEVRE_DISI,
    )
    paket.kimlik.kullanici_deposu.kaydet(ikinci)
    yanit = istemci.post(
        f"/yonetici/kullanicilar/{ikinci.kullanici_id}/devre-disi",
        follow_redirects=True,
    )
    assert "en az bir aktif yönetici" in yanit.get_data(as_text=True)


def test_uc23_rapor_goruntuleme(ortam):
    istemci, paket = ortam
    yonetici_giris_yap(istemci, paket)
    soru_kaydi_ekle(paket, "Burs")
    soru_kaydi_ekle(paket, "Burs")
    soru_kaydi_ekle(paket, "Burs")
    soru_kaydi_ekle(paket, "Öğrenci Hizmetleri", yanitlandi=False)
    soru_kaydi_ekle(paket, "Eski Kategori", gun_once=400)

    yanit = istemci.get("/yonetici/rapor")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "Toplam Soru" in metin
    assert "<svg" in metin
    assert "Burs" in metin
    assert "Öğrenci Hizmetleri" in metin
    assert "Eski Kategori" not in metin

    yanit = istemci.get("/yonetici/rapor?baslangic=2026-12-31&bitis=2026-01-01")
    metin = yanit.get_data(as_text=True)
    assert "önce olamaz" in metin


def test_uc24_csv_indirme(ortam):
    istemci, paket = ortam
    yonetici_giris_yap(istemci, paket)
    soru_kaydi_ekle(paket, "Burs")
    soru_kaydi_ekle(paket, "Öğrenci Hizmetleri", yanitlandi=False)

    yanit = istemci.get("/yonetici/rapor/csv")
    assert yanit.status_code == 200
    baslik = yanit.headers.get("Content-Disposition", "")
    assert "attachment" in baslik
    assert "UniAsist_Rapor_" in baslik
    assert baslik.endswith(".csv")
    assert yanit.data.startswith(b"\xef\xbb\xbf")
    icerik = yanit.data.decode("utf-8-sig")
    assert "Metrik;Değer" in icerik
    assert "Öğrenci Hizmetleri" in icerik
    assert ";" in icerik


def test_uc24_csv_baglantisi_filtre_tarihlerini_tasir(ortam):
    istemci, paket = ortam
    yonetici_giris_yap(istemci, paket)
    yanit = istemci.get("/yonetici/rapor?baslangic=2026-01-01&bitis=2026-10-31")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert (
        'href="/yonetici/rapor/csv?baslangic=2026-01-01&bitis=2026-10-31"' in metin
    )


def test_nfr03_personel_yonetici_sayfasina_ulasamaz(ortam):
    istemci, paket = ortam
    assert istemci.get("/yonetici/kullanicilar").status_code == 302

    kullanici_ekle(paket, "Personel Bey", "personel@universite.edu.tr", Rol.PERSONEL)
    istemci.post("/giris", data={"eposta": "personel@universite.edu.tr", "sifre": "Gizli1234"})
    assert istemci.get("/yonetici/kullanicilar").status_code == 403
    assert istemci.get("/yonetici/rapor").status_code == 403
    assert istemci.get("/yonetici/rapor/csv").status_code == 403
