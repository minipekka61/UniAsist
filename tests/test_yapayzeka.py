import json

import pytest
import requests

import config
from tests.yardimci import SahteYZ, gecici_db, yerel_gomme
from uniasist.entity import IcerikParcasi, Mesaj
from uniasist.enumlar import GonderenTuru
from uniasist.hatalar import IsKuraliIhlaliException
from uniasist.servis.arama_dizini import AramaDizini
from uniasist.yapayzeka.hazir_llm_servisi import HazirLLMServisi
from uniasist.yapayzeka.yerel_arama_servisi import YerelAramaServisi


def parca(metin, kaynak_id=1, sira=1):
    return IcerikParcasi(
        kaynak_id=kaynak_id,
        sira=sira,
        metin=metin,
        gomme=yerel_gomme(metin),
        gomme_saglayici="sahte:test",
        kaynak_adi="burs.txt",
    )


def test_yerel_gomme_deterministik():
    yz = YerelAramaServisi()
    v1 = yz.gommeUret("Burs başvurusu ne zaman yapılır?")
    v2 = yz.gommeUret("Burs başvurusu ne zaman yapılır?")
    assert v1 == v2
    benzer_konum = yz.gommeUret("burs basvurusu ne zaman")
    uzak = yz.gommeUret("bugün hava nasıl")
    from uniasist.entity import IcerikParcasi

    p = IcerikParcasi(kaynak_id=1, sira=1, metin="x", gomme=benzer_konum)
    assert p.benzerlikHesapla(v1) > p.benzerlikHesapla(uzak)


def test_yerel_gomme_surecler_arasi_kararli():
    import json
    import subprocess
    import sys

    yz = YerelAramaServisi()
    beklenen = yz.gommeUret("Burs başvurusu ne zaman yapılır?")
    kod = (
        "import json; "
        "from uniasist.yapayzeka.yerel_arama_servisi import YerelAramaServisi; "
        "print(json.dumps(YerelAramaServisi().gommeUret('Burs başvurusu ne zaman yapılır?')))"
    )
    sonuc = subprocess.run(
        [sys.executable, "-c", kod], capture_output=True, text=True, check=True
    )
    assert json.loads(sonuc.stdout) == beklenen


def test_yerel_yanit_extractive():
    yz = YerelAramaServisi()
    p = parca("Staj başvurusu için en az 60 gün çalışma şartıdır. Başvuru öğrenci işlerine yapılır. Staj defteri teslim edilir.")
    yanit = yz.yanitUret("Staj şartı nedir?", [p], [])
    assert "60 gün" in yanit


def test_yerel_yanit_ilgili_cumleyi_secer():
    yz = YerelAramaServisi()
    metin = (
        "Bu yönerge kapsamında tüm lisans öğrencileri yararlanır. "
        "Yönerge Senato tarafından onaylanmıştır. "
        "Danışman onayı ile ders yükü en fazla 40 AKTS'ye kadar artırılabilir. "
        "İtirazlar beş iş günü içinde Öğrenci İşlerine yapılır."
    )
    p = parca(metin)
    yanit = yz.yanitUret("Ders yükü en fazla kaç AKTS'ye kadar artırılabilir?", [p], [])
    assert "40 AKTS" in yanit


def test_arama_dizini_siralama_ve_skor():
    db = gecici_db()
    dizin = AramaDizini(db)
    p1 = parca("Burs başvuru tarihleri eylül ayında açıklanır.", kaynak_id=1, sira=1)
    p2 = parca("Yurt başvuruları ağustos sonunda başlar.", kaynak_id=2, sira=1)
    p3 = parca("Burs başvurusu için transkript gerekir.", kaynak_id=3, sira=1)
    for p in (p1, p2, p3):
        dizin.parcaEkle(p)

    sorgu = yerel_gomme("burs başvurusu")
    sonuclar = dizin.enYakinParcalar(sorgu, 5)
    assert len(sonuclar) == 3
    assert sonuclar[0].skor >= sonuclar[1].skor >= sonuclar[2].skor
    assert "Burs" in sonuclar[0].parca.metin or "burs" in sonuclar[0].parca.metin
    assert sonuclar[0].skor > 0

    kalici = AramaDizini(db)
    assert len(kalici.enYakinParcalar(sorgu, 5)) == 3


def test_arama_dizini_kaynaga_gore_sil():
    db = gecici_db()
    dizin = AramaDizini(db)
    p1 = parca("Burs metni.", kaynak_id=1, sira=1)
    p2 = parca("Yurt metni.", kaynak_id=2, sira=1)
    dizin.parcaEkle(p1)
    dizin.parcaEkle(p2)
    dizin.kaynagaGoreSil(1)
    sonuclar = dizin.enYakinParcalar(yerel_gomme("burs"), 5)
    assert len(sonuclar) == 1
    assert sonuclar[0].parca.kaynak_id == 2

    db2 = gecici_db()
    dizin2 = AramaDizini(db2)
    dizin2.parcaEkle(p1)
    dizin2.surumeGoreSil(1, 1)
    assert dizin2.enYakinParcalar(yerel_gomme("burs"), 5) == []


def test_arama_dizini_saglayici_uyumu():
    db = gecici_db()
    dizin = AramaDizini(db)
    assert dizin.saglayiciUyumlu("sahte:test") is True
    p1 = parca("Burs metni.", kaynak_id=1, sira=1)
    dizin.parcaEkle(p1)
    assert dizin.saglayiciUyumlu("sahte:test") is True
    assert dizin.saglayiciUyumlu("yerel:tfidf-1") is False

    yz = SahteYZ()
    dizin.yenidenGomme(yz)
    assert dizin.saglayiciUyumlu("sahte:test") is True
    assert AramaDizini(db).saglayiciUyumlu("sahte:test") is True


class SahteYanit:
    def __init__(self, durum_kodu=200, gomdu=None, parcalar=None):
        self.status_code = durum_kodu
        self._gomdu = gomdu
        self._parcalar = parcalar or []

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if self._gomdu is not None:
            return {"data": [{"embedding": self._gomdu}]}
        return {"choices": [{"message": {"content": " ".join(self._parcalar)}}]}


class SahteAkisYanit:
    def __init__(self, durum_kodu=200, parcalar=None):
        self.status_code = durum_kodu
        self._parcalar = parcalar or []

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def iter_lines(self):
        for p in self._parcalar:
            yield b"data: " + json.dumps(
                {"choices": [{"delta": {"content": p}}]}, ensure_ascii=False
            ).encode("utf-8")
        yield b"data: [DONE]"


def test_hazir_llm_gomme_cagrisi(monkeypatch):
    cagrilar = []

    def sahte_post(url, **kw):
        cagrilar.append((url, kw))
        return SahteYanit(gomdu=[0.1, 0.2, 0.3])

    monkeypatch.setattr(requests, "post", sahte_post)
    servis = HazirLLMServisi(api_anahtari="anahtar")
    gomme = servis.gommeUret("deneme metni")
    assert gomme == [0.1, 0.2, 0.3]
    url, kw = cagrilar[0]
    assert url == f"{config.API_BASE}/embeddings"
    assert kw["json"]["model"] == config.EMBEDDING_MODEL
    assert kw["json"]["input"] == ["deneme metni"]
    assert kw["headers"]["Authorization"] == "Bearer anahtar"
    assert servis.saglayici_etiketi == f"api:{config.EMBEDDING_MODEL}"


def test_hazir_llm_yanit_akisi(monkeypatch):
    parcalar = []

    def sahte_post(url, **kw):
        return SahteAkisYanit(parcalar=["Merhaba ", "dünya", "!"])

    monkeypatch.setattr(requests, "post", sahte_post)
    servis = HazirLLMServisi(api_anahtari="anahtar")
    akis = list(servis.yanitUretAkis("soru", [], []))
    assert akis == ["Merhaba ", "dünya", "!"]
    assert servis.yanitUret("soru", [], []) == "Merhaba dünya!"


def test_hazir_llm_istek_govdesi(monkeypatch):
    yakalanan = {}

    def sahte_post(url, **kw):
        yakalanan["url"] = url
        yakalanan["govde"] = kw["json"]
        return SahteAkisYanit(parcalar=["tamam"])

    monkeypatch.setattr(requests, "post", sahte_post)
    servis = HazirLLMServisi(api_anahtari="anahtar")
    p = parca("Burs kapsamı eğitim ve barınmayı içerir.")
    baglam = [Mesaj(gonderen=GonderenTuru.KULLANICI, metin="Bursu sordum", zaman=None)]
    servis.yanitUret("Burs neleri kapsar?", [p], baglam)
    govde = yakalanan["govde"]
    assert govde["stream"] is True
    assert "BELGE İÇERİĞİ" in govde["messages"][1]["content"]
    assert "BILGI_YOK" in govde["messages"][0]["content"]
    assert "ÖNCEKİ KONUŞMA" in govde["messages"][1]["content"]


def test_hazir_llm_hata(monkeypatch):
    def sahte_post(url, **kw):
        return SahteYanit(durum_kodu=500)

    monkeypatch.setattr(requests, "post", sahte_post)
    servis = HazirLLMServisi(api_anahtari="anahtar")
    with pytest.raises(IsKuraliIhlaliException) as h:
        servis.yanitUret("soru", [], [])
    assert h.value.kural_no_getir() == "IK-19"
    assert h.value.mesaj == config.SERVIS_HATA_METNI


def test_hazir_llm_zaman_asimi(monkeypatch):
    def sahte_post(url, **kw):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "post", sahte_post)
    servis = HazirLLMServisi(api_anahtari="anahtar")
    with pytest.raises(IsKuraliIhlaliException) as h:
        servis.gommeUret("metin")
    assert h.value.kural_no_getir() == "IK-19"
