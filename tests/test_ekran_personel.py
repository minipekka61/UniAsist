import io

import pytest

import config
from tests.yardimci import SahteYZ, gecici_db
from uniasist.entity import Kullanici
from uniasist.enumlar import GeriBildirimTuru, Rol
from uniasist.guvenlik import sifre_hashle
from uniasist.kurulum import kur
from uniasist.uygulama import uygulama_olustur

BELGE_METNI = (
    "Burs yonergesi universite ogrencilerine saglanan destegi duzenler. "
    "Basari bursu icin genel not ortalamasinin en az 3.00 olmasi gerekir. "
    "Burs basvurusu eylul ayinin ilk haftasinda ogrenci isleri tarafindan alinir. "
    "Ihtiyac bursu icin gelir belgesi talep edilir ve aile geliri kontrol edilir. "
    "Burs kapsaminda ogrenim ucreti destegi ve harc destegi saglanir. "
    "Yurt basvurusu ayri olarak KYK sistemi uzerinden yapilir ve temmuz ayinda acilir. "
) * 3

STAJ_METNI = (
    "Staj yonergesi ogrencilerin staj basvuru surecini duzenler. "
    "Staj suresi en az 60 gundur ve staj defteri doldurulmalidir. "
    "Staj basvurusu derslerin baslamasindan once bolum baskanligina yapilir. "
    "Staj degerlendirmesi isyeri muduru raporu ile yapilir. "
) * 3


@pytest.fixture
def paket():
    paket = kur(db=gecici_db(), yapay_zeka=SahteYZ())
    paket.sohbet.yanit_uretme_servisi.benzerlik_esigi = config.YEREL_ESIK
    return paket


@pytest.fixture
def ortam(paket, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DOSYA_KLASORU", str(tmp_path / "dosyalar"))
    uygulama = uygulama_olustur(paket)
    uygulama.config["TESTING"] = True
    with uygulama.test_client() as istemci:
        yield istemci, paket, tmp_path


def personel_giris_yap(istemci, paket):
    personel = Kullanici(
        ad_soyad="Personel Bey",
        eposta="personel@universite.edu.tr",
        sifre_hash=sifre_hashle("Personel1234"),
        rol=Rol.PERSONEL,
    )
    paket.kimlik.kullanici_deposu.kaydet(personel)
    istemci.post("/giris", data={"eposta": "personel@universite.edu.tr", "sifre": "Personel1234"})


def belge_yukle(istemci, dosya_adi="burs.txt", icerik=None, baslik="Burs Yönergesi"):
    icerik = icerik or BELGE_METNI
    return istemci.post(
        "/personel/belge-yukle",
        data={
            "dosya": (io.BytesIO(icerik.encode("utf-8")), dosya_adi),
            "baslik": baslik,
            "kategori": "Burs",
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_uc13_belge_yukleme(ortam):
    istemci, paket, _ = ortam
    personel_giris_yap(istemci, paket)
    yanit = belge_yukle(istemci)
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "yüklendi ve aktif" in metin
    assert "AKTIF" in metin
    belgeler = paket.bilgi_tabani.belgeleriListele()
    assert len(belgeler) == 1
    assert belgeler[0].aktifMi()
    parcalar = paket.db.execute(
        "SELECT * FROM icerik_parcasi WHERE kaynak_id=?", (belgeler[0].kaynak_id,)
    ).fetchall()
    assert len(parcalar) > 0


def test_uc13_gecersiz_dosya_hata(ortam):
    istemci, paket, _ = ortam
    personel_giris_yap(istemci, paket)
    yanit = belge_yukle(istemci, dosya_adi="belge.docx")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "Belge yüklenemedi" in metin
    assert paket.bilgi_tabani.belgeleriListele() == []


def test_uc15_baslik_guncelleme(ortam):
    istemci, paket, _ = ortam
    personel_giris_yap(istemci, paket)
    belge_yukle(istemci)
    belge = paket.bilgi_tabani.belgeleriListele()[0]
    yanit = istemci.post(
        f"/personel/belge-guncelle/{belge.kaynak_id}",
        data={"baslik": "Burs Yönergesi 2026", "kategori": "Burs"},
        follow_redirects=True,
    )
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "Burs Yönergesi 2026" in metin
    assert paket.bilgi_tabani.belgeleriListele()[0].baslik == "Burs Yönergesi 2026"


def test_uc15_yeni_dosya_ile_guncelleme(ortam):
    istemci, paket, _ = ortam
    personel_giris_yap(istemci, paket)
    belge_yukle(istemci)
    belge = paket.bilgi_tabani.belgeleriListele()[0]
    yanit = istemci.post(
        f"/personel/belge-guncelle/{belge.kaynak_id}",
        data={
            "baslik": "Staj Yönergesi",
            "kategori": "Staj",
            "dosya": (io.BytesIO(STAJ_METNI.encode("utf-8")), "staj.txt"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert yanit.status_code == 200
    guncel = paket.bilgi_tabani.belgeleriListele()[0]
    assert guncel.surum_no == 2
    satirlar = paket.db.execute(
        "SELECT * FROM icerik_parcasi WHERE kaynak_id=?", (belge.kaynak_id,)
    ).fetchall()
    assert len(satirlar) > 0
    assert all(s["surum_no"] == 2 for s in satirlar)
    assert all("Staj" in s["metin"] for s in satirlar)


def test_uc16_silme_onay_ve_sonuc(ortam):
    istemci, paket, _ = ortam
    personel_giris_yap(istemci, paket)
    belge_yukle(istemci)
    belge = paket.bilgi_tabani.belgeleriListele()[0]

    import pathlib

    sablon = pathlib.Path("sablonlar") / "belgeler.html"
    assert "confirm" in sablon.read_text(encoding="utf-8")

    yanit = istemci.post(f"/personel/belge-sil/{belge.kaynak_id}", follow_redirects=True)
    assert yanit.status_code == 200
    assert paket.bilgi_tabani.belgeleriListele() == []
    kalan = paket.db.execute(
        "SELECT * FROM icerik_parcasi WHERE kaynak_id=?", (belge.kaynak_id,)
    ).fetchall()
    assert kalan == []
    assert "Burs Yönergesi" not in yanit.get_data(as_text=True)


def test_uc17_sss_ekle(ortam):
    istemci, paket, _ = ortam
    personel_giris_yap(istemci, paket)
    yanit = istemci.post(
        "/personel/sss-ekle",
        data={
            "soru": "Kayıt yenileme ne zaman yapılır?",
            "cevap": "Kayıt yenileme her dönem başında öğrenci işleri üzerinden yapılır.",
            "kategori": "Kayıt",
        },
        follow_redirects=True,
    )
    assert yanit.status_code == 200
    assert "eklendi" in yanit.get_data(as_text=True)
    satir = paket.db.execute("SELECT * FROM bilgi_kaynagi WHERE tur='SSS'").fetchone()
    assert satir is not None
    assert satir["durum"] == "AKTIF"
    parcalar = paket.db.execute(
        "SELECT * FROM icerik_parcasi WHERE kaynak_id=?", (satir["kaynak_id"],)
    ).fetchall()
    assert len(parcalar) == 1


def test_uc17_yanitlanamayandan_sss(ortam):
    istemci, paket, _ = ortam
    personel_giris_yap(istemci, paket)
    kayit = paket.yanitlanamayan.kaydet("Diploma teslim süresi nedir?")
    yanit = istemci.get(f"/personel/sss-ekle?kayit_id={kayit.kayit_id}")
    assert yanit.status_code == 200
    assert "Diploma teslim süresi nedir?" in yanit.get_data(as_text=True)

    yanit = istemci.post(
        "/personel/sss-ekle",
        data={
            "soru": "Diploma teslim süresi nedir?",
            "cevap": "Diplomalar mezuniyeti izleyen 30 gün içinde teslim edilir.",
            "kategori": "Mezuniyet",
            "kayit_id": kayit.kayit_id,
        },
        follow_redirects=True,
    )
    assert yanit.status_code == 200
    satir = paket.db.execute(
        "SELECT durum FROM yanitlanamayan_soru WHERE kayit_id=?", (kayit.kayit_id,)
    ).fetchone()
    assert satir["durum"] == "COZULDU"


def test_uc18_liste_filtre_ve_anonimlik(ortam):
    istemci, paket, _ = ortam
    personel_giris_yap(istemci, paket)
    paket.yanitlanamayan.kaydet("Yurt başvurusu ne zaman açılır?")
    for _ in range(3):
        paket.yanitlanamayan.kaydet("Ders ekleme nasıl yapılır?")
    cozulen = paket.yanitlanamayan.kaydet("Mezuniyet töreni ne zaman?")
    cozulen.coz()
    paket.yanitlanamayan.yanitlanamayan_soru_deposu.kaydet(cozulen)

    yanit = istemci.get("/personel/yanitlanamayan-sorular")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "Yurt başvurusu" in metin
    assert "Ders ekleme" in metin
    assert "Mezuniyet töreni" not in metin
    assert metin.index("Ders ekleme") < metin.index("Yurt başvurusu")
    assert "@" not in metin

    yanit = istemci.get("/personel/yanitlanamayan-sorular?durum=COZULDU")
    metin = yanit.get_data(as_text=True)
    assert "Mezuniyet töreni" in metin
    assert "Yurt başvurusu" not in metin


def test_uc19_yararsizlar_listelenir(ortam):
    istemci, paket, tmp_path = ortam
    personel_giris_yap(istemci, paket)
    dosya = tmp_path / "burs.txt"
    dosya.write_text(BELGE_METNI, encoding="utf-8")
    paket.bilgi_tabani.belgeYukle("burs.txt", str(dosya), 2000, "Burs Yönergesi", "Burs")

    ogrenci = paket.kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234")
    sohbet = paket.sohbet.yeniSohbetBaslat(kullanici=ogrenci)
    mesaj = paket.sohbet.soruSor(sohbet, "Burs başvurusu ne zaman yapılır?")
    paket.geri_bildirim.geriBildirimVer(
        ogrenci.kullanici_id, mesaj.mesaj_id, GeriBildirimTuru.YARARSIZ, "Yanıt yetersiz kaldı."
    )

    yanit = istemci.get("/personel/geri-bildirimler")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "Burs başvurusu ne zaman yapılır?" in metin
    assert "Belgeye göre" in metin
    assert "burs.txt" in metin
    assert "Yanıt yetersiz kaldı." in metin
    assert "ali@universite.edu.tr" not in metin
    assert "Ali Veli" not in metin


def test_nfr03_ogrenci_personel_sayfasina_ulasamaz(ortam):
    istemci, paket, _ = ortam
    assert istemci.get("/personel/belgeler").status_code == 302

    paket.kimlik.kayitOl("Ali Veli", "ali@universite.edu.tr", "Gizli1234", "Gizli1234")
    istemci.post("/giris", data={"eposta": "ali@universite.edu.tr", "sifre": "Gizli1234"})
    for yol in (
        "/personel/belgeler",
        "/personel/sss-ekle",
        "/personel/yanitlanamayan-sorular",
        "/personel/geri-bildirimler",
    ):
        assert istemci.get(yol).status_code == 403
