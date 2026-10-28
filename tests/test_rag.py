from datetime import datetime

import config
from tests.yardimci import SahteYZ
from uniasist.dto import AramaSonucu, YanitSonucu
from uniasist.entity import IcerikParcasi, Mesaj
from uniasist.enumlar import GonderenTuru, SonucDurumu
from uniasist.servis.yanit_uretme_servisi import YanitUretmeServisi
from uniasist.yapayzeka.yerel_arama_servisi import YerelAramaServisi


def parca(metin, kaynak_id=1, sira=1, kaynak_adi="burs.txt"):
    return IcerikParcasi(
        kaynak_id=kaynak_id,
        sira=sira,
        metin=metin,
        gomme=[0.1],
        gomme_saglayici="sahte:test",
        kaynak_adi=kaynak_adi,
        bolum_bilgisi=f"Burs Yönergesi — parça {sira}",
    )


def servis(yz=None, sonuclar=None, esik=None):
    yz = yz or SahteYZ()
    dizin = type(
        "D", (), {"enYakinParcalar": lambda self, s, a, kapsam=None: (sonuclar or [])[:a]}
    )()
    return YanitUretmeServisi(dizin, yz, benzerlik_esigi=esik)


def test_ik14_esik_alti_llm_cagrilamaz():
    yz = SahteYZ()
    s = servis(yz=yz, sonuclar=[AramaSonucu(parca=parca("burs"), skor=0.59)], esik=0.60)
    sonuc = s.yanitUret("Burs ne zaman?", [])
    assert sonuc.durum == SonucDurumu.ICERIK_BULUNAMADI
    assert sonuc.metin == config.BILGI_YOK_METNI
    assert sonuc.kaynaklar == []
    assert yz.cagri_sayisi == 0


def test_ik14_sonuç_yok_llm_cagrilamaz():
    yz = SahteYZ()
    s = servis(yz=yz, sonuclar=[], esik=0.60)
    sonuc = s.yanitUret("Burs ne zaman?", [])
    assert sonuc.durum == SonucDurumu.ICERIK_BULUNAMADI
    assert yz.cagri_sayisi == 0


def test_ik13_yanit_kaynaklarla_donar():
    yz = SahteYZ()
    p1 = parca("Burs başvurusu eylülde yapılır.", sira=1)
    p2 = parca("Burs ücreti öğrenim ücretini kapsar.", sira=2)
    s = servis(yz=yz, sonuclar=[AramaSonucu(parca=p1, skor=0.9), AramaSonucu(parca=p2, skor=0.8)], esik=0.60)
    sonuc = s.yanitUret("Burs ne zaman?", [])
    assert sonuc.durum == SonucDurumu.YANIT
    assert sonuc.basarili()
    assert "Burs" in sonuc.metin
    assert len(sonuc.kaynaklar) == 2
    assert sonuc.kaynaklar[0].kaynak_adi == "burs.txt"
    assert sonuc.kaynaklar[0].bolum_bilgisi == "Burs Yönergesi — parça 1"
    assert sonuc.kaynaklar[0].benzerlik_skoru == 0.9
    assert yz.gorunen_parcalar[0].metin == p1.metin


def test_ik12_bilgi_yok_isareti_bulunamadi_dali():
    yz = SahteYZ(mod="bilgi_yok")
    s = servis(yz=yz, sonuclar=[AramaSonucu(parca=parca("burs"), skor=0.9)], esik=0.60)
    sonuc = s.yanitUret("Burs ne zaman?", [])
    assert sonuc.durum == SonucDurumu.ICERIK_BULUNAMADI
    assert sonuc.metin == config.BILGI_YOK_METNI
    assert sonuc.kaynaklar == []


def test_ik19_servis_hatasi_dali():
    yz = SahteYZ(mod="hata")
    s = servis(yz=yz, sonuclar=[AramaSonucu(parca=parca("burs"), skor=0.9)], esik=0.60)
    sonuc = s.yanitUret("Burs ne zaman?", [])
    assert sonuc.durum == SonucDurumu.SERVIS_HATASI
    assert sonuc.metin == config.SERVIS_HATA_METNI
    assert sonuc.kaynaklar == []


def test_akis_parcalari_ve_sonuc():
    yz = SahteYZ()
    p = parca("Burs başvurusu eylül ayında yapılır. Transkript gerekir.")
    s = servis(yz=yz, sonuclar=[AramaSonucu(parca=p, skor=0.9)], esik=0.60)
    olaylar = list(s.yanitUretAkis("Burs ne zaman?", []))
    parcalar = [o for o in olaylar if o["tur"] == "parca"]
    sonuc_olayi = [o for o in olaylar if o["tur"] == "sonuc"][0]
    assert len(parcalar) > 1
    assert "".join(o["metin"] for o in parcalar) == sonuc_olayi["sonuc"].metin
    assert sonuc_olayi["sonuc"].basarili()


def test_bilgi_yok_akista_parca_sizmaz():
    yz = SahteYZ(mod="bilgi_yok")
    s = servis(yz=yz, sonuclar=[AramaSonucu(parca=parca("burs"), skor=0.9)], esik=0.60)
    olaylar = list(s.yanitUretAkis("Burs ne zaman?", []))
    assert [o for o in olaylar if o["tur"] == "parca"] == []
    sonuc_olayi = olaylar[-1]
    assert sonuc_olayi["sonuc"].durum == SonucDurumu.ICERIK_BULUNAMADI


def test_en_fazla_5_parca():
    yz = SahteYZ()
    sonuclar = [AramaSonucu(parca=parca(f"parça {i}", sira=i), skor=0.9) for i in range(1, 9)]
    s = servis(yz=yz, sonuclar=sonuclar, esik=0.60)
    sonuc = s.yanitUret("Burs ne zaman?", [])
    assert len(yz.gorunen_parcalar) == 5
    assert len(sonuc.kaynaklar) == 5


def test_baglam_llm_e_tasiniyor():
    yz = SahteYZ()
    baglam = [
        Mesaj(gonderen=GonderenTuru.KULLANICI, metin="Bursu sormuştum", zaman=datetime.now()),
        Mesaj(gonderen=GonderenTuru.SISTEM, metin="Eylülde.", zaman=datetime.now()),
    ]
    s = servis(yz=yz, sonuclar=[AramaSonucu(parca=parca("burs"), skor=0.9)], esik=0.60)
    s.yanitUret("Peki son tarihi ne zaman?", baglam)
    assert yz.gorunen_baglam == baglam


def test_esik_servis_turune_gore():
    yz = YerelAramaServisi()
    s = YanitUretmeServisi(None, yz)
    assert s.benzerlik_esigi == config.YEREL_ESIK
    s2 = YanitUretmeServisi(None, SahteYZ())
    assert s2.benzerlik_esigi == config.BENZERLIK_ESIGI


def test_ik13_kaynaksiz_yanit_gosterilmez():
    yz = SahteYZ()
    p = parca("burs")
    p.kaynak_adi = ""
    s = servis(yz=yz, sonuclar=[AramaSonucu(parca=p, skor=0.9)], esik=0.60)
    sonuc = s.yanitUret("Burs ne zaman?", [])
    assert sonuc.durum == SonucDurumu.ICERIK_BULUNAMADI
