import json

import pytest

import config
from tests.yardimci import SahteYZ, gecici_db
from uniasist.enumlar import KayitDurumu
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


@pytest.fixture
def paket(tmp_path):
    paket = kur(db=gecici_db(), yapay_zeka=SahteYZ())
    paket.sohbet.yanit_uretme_servisi.benzerlik_esigi = config.YEREL_ESIK
    dosya = tmp_path / "burs.txt"
    dosya.write_text(BELGE_METNI, encoding="utf-8")
    paket.bilgi_tabani.belgeYukle("burs.txt", str(dosya), 2000, "Burs Yönergesi", "Burs")
    return paket


@pytest.fixture
def ortam(paket):
    uygulama = uygulama_olustur(paket)
    uygulama.config["TESTING"] = True
    with uygulama.test_client() as istemci:
        yield istemci, paket, uygulama


def giris_yap(istemci, paket, eposta="ali@universite.edu.tr"):
    paket.kimlik.kayitOl("Ali Veli", eposta, "Gizli1234", "Gizli1234", "Bilgisayar Mühendisliği")
    istemci.post("/giris", data={"eposta": eposta, "sifre": "Gizli1234"})


def test_kayitsiz_anasayfa_girise_yonlendirir(ortam):
    istemci, _, _ = ortam
    yanit = istemci.get("/")
    assert yanit.status_code == 302
    assert "/giris" in yanit.headers["Location"]


def test_kayitsiz_soru_gonderemez(ortam):
    istemci, _, _ = ortam
    yanit = istemci.post("/sohbet/yanit", data={"soru": "Burs başvurusu ne zaman yapılır?"})
    assert yanit.status_code == 302
    assert "/giris" in yanit.headers["Location"]


def test_fr14_yaziyor_gostergesi_ve_script(ortam):
    istemci, paket, uygulama = ortam
    giris_yap(istemci, paket)
    yanit = istemci.get("/")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert "yaziyor" in metin
    import pathlib

    js = pathlib.Path(uygulama.static_folder) / "sohbet.js"
    icerik = js.read_text(encoding="utf-8")
    assert "yaziyor" in icerik
    assert "fetch" in icerik or "EventSource" in icerik


def test_ogrenci_sohbeti_kalici(ortam):
    istemci, paket, _ = ortam
    giris_yap(istemci, paket)
    istemci.post("/sohbet/yanit", data={"soru": "Burs başvurusu ne zaman yapılır?"}).get_data(as_text=True)
    istemci.post("/sohbet/yanit", data={"soru": "Burs için ortalama şartı nedir?"}).get_data(as_text=True)
    gecmis = istemci.get("/gecmis")
    metin = gecmis.get_data(as_text=True)
    assert gecmis.status_code == 200
    assert "Burs başvurusu" in metin


def test_ik16_anasayfa_son_sohbetle_devam_eder(ortam):
    istemci, paket, uygulama = ortam
    giris_yap(istemci, paket)
    istemci.post("/sohbet/yanit", data={"soru": "Burs başvurusu ne zaman yapılır?"}).get_data(as_text=True)
    sohbet_id = paket.sohbet.sohbetleriListele(1)[0].sohbet_id

    yanit = istemci.get("/")
    assert yanit.status_code == 200
    metin = yanit.get_data(as_text=True)
    assert f"window.uniasistSohbetId = {sohbet_id}" in metin

    import pathlib

    js = pathlib.Path(uygulama.static_folder) / "sohbet.js"
    icerik = js.read_text(encoding="utf-8")
    assert "uniasistSohbetId" in icerik


def test_ik21_baskasi_gecmisine_url_ile_ulasamaz(ortam):
    istemci, paket, _ = ortam
    giris_yap(istemci, paket, "ali@universite.edu.tr")
    istemci.post("/sohbet/yanit", data={"soru": "Burs başvurusu ne zaman yapılır?"}).get_data(as_text=True)
    sohbet_id = paket.sohbet.sohbetleriListele(1)[0].sohbet_id

    giris_yap(istemci, paket, "ayse@universite.edu.tr")
    yanit = istemci.get(f"/gecmis/{sohbet_id}")
    assert yanit.status_code == 403


def test_uc07a1_silinen_kaynak_mesaji(ortam):
    istemci, paket, _ = ortam
    giris_yap(istemci, paket)
    istemci.post("/sohbet/yanit", data={"soru": "Burs başvurusu ne zaman yapılır?"}).get_data(as_text=True)
    sohbet = paket.sohbet.sohbetleriListele(1)[0]
    yanit_mesaji = sohbet.mesajlar[1]
    ref = yanit_mesaji.kaynaklariGetir()[0]
    belge = paket.bilgi_tabani.belgeleriListele()[0]
    ref.kaynak_id = belge.kaynak_id

    url = f"/kaynak/{ref.kaynak_id}"
    acilan = istemci.get(url)
    assert acilan.status_code == 200
    assert "Burs Yönergesi" in acilan.get_data(as_text=True)

    paket.bilgi_tabani.belgeSil(belge.kaynak_id)
    acilan = istemci.get(url)
    assert acilan.status_code == 200
    assert "mevcut değil" in acilan.get_data(as_text=True)


def test_uc10_geri_bildirim_gonder(ortam):
    istemci, paket, _ = ortam
    giris_yap(istemci, paket)
    istemci.post("/sohbet/yanit", data={"soru": "Burs başvurusu ne zaman yapılır?"}).get_data(as_text=True)
    sohbet = paket.sohbet.sohbetleriListele(1)[0]
    mesaj_id = sohbet.mesajlar[1].mesaj_id

    yanit = istemci.post("/geri-bildirim", json={
        "mesaj_id": mesaj_id, "tur": "YARARSIZ", "aciklama": "yetersiz",
    })
    assert yanit.status_code == 200
    yanit = istemci.post("/geri-bildirim", json={
        "mesaj_id": mesaj_id, "tur": "YARARLI", "aciklama": None,
    })
    assert yanit.status_code == 200
    ozetler = paket.geri_bildirim.yararsizlariListele()
    assert len(ozetler) == 0


def test_uc12_sohbet_sil(ortam):
    istemci, paket, _ = ortam
    giris_yap(istemci, paket)
    istemci.post("/sohbet/yanit", data={"soru": "Burs başvurusu ne zaman yapılır?"}).get_data(as_text=True)
    sohbet_id = paket.sohbet.sohbetleriListele(1)[0].sohbet_id

    paket.yanitlanamayan.kaydet("Silinmeyecek anonim soru")
    yanit = istemci.post(f"/gecmis/{sohbet_id}/sil", follow_redirects=True)
    assert yanit.status_code == 200
    assert paket.sohbet.sohbetleriListele(1) == []
    assert len(paket.db.execute("SELECT * FROM yanitlanamayan_soru").fetchall()) == 1


def test_nfr06_mobil_gorunum():
    import pathlib

    dosya = pathlib.Path("statik") / "stil.css"
    icerik = dosya.read_text(encoding="utf-8")
    assert "@media" in icerik


def test_sohbet_yeni(ortam):
    istemci, paket, _ = ortam
    giris_yap(istemci, paket)
    istemci.post("/sohbet/yanit", data={"soru": "Burs başvurusu ne zaman yapılır?"}).get_data(as_text=True)
    yanit = istemci.post("/sohbet/yeni", follow_redirects=True)
    assert yanit.status_code == 200
    assert len(paket.sohbet.sohbetleriListele(1)) == 1
