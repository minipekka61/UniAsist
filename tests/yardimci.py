import math
import sqlite3

from uniasist.depo.veritabani import sema_olustur
from uniasist.enumlar import SonucDurumu
from uniasist.hatalar import IsKuraliIhlaliException
from uniasist.yapayzeka.i_yapay_zeka_servisi import IYapayZekaServisi


def gecici_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    sema_olustur(conn)
    return conn


def yerel_gomme(metin, boyut=512):
    v = [0.0] * boyut
    metin = metin.lower()
    for n in (3, 4, 5):
        for i in range(len(metin) - n + 1):
            v[hash(metin[i : i + n]) % boyut] += 1.0
    for kelime in metin.split():
        v[hash(kelime) % boyut] += 2.0
    norm = math.sqrt(sum(x * x for x in v))
    if norm > 0:
        v = [x / norm for x in v]
    return v


class SahteYZ(IYapayZekaServisi):
    def __init__(self, mod="yanit", gomme_hata_sonrasi=None):
        self.mod = mod
        self.gomme_hata_sonrasi = gomme_hata_sonrasi
        self.gomme_cagri_sayisi = 0
        self.cagri_sayisi = 0
        self.gorunen_baglam = None
        self.gorunen_parcalar = None

    @property
    def saglayici_etiketi(self):
        return "sahte:test"

    def gommeUret(self, metin):
        if self.mod == "gomme_hata":
            raise IsKuraliIhlaliException("IK-19", "test gomme hatası")
        self.gomme_cagri_sayisi += 1
        if (
            self.gomme_hata_sonrasi is not None
            and self.gomme_cagri_sayisi > self.gomme_hata_sonrasi
        ):
            raise IsKuraliIhlaliException("IK-19", "test gomme hatası")
        return yerel_gomme(metin)

    def yanitUret(self, soru_metni, parcalar, baglam):
        self.cagri_sayisi += 1
        self.gorunen_baglam = baglam
        self.gorunen_parcalar = parcalar
        if self.mod == "hata":
            raise IsKuraliIhlaliException("IK-19", "test hatası")
        if self.mod == "bilgi_yok":
            return "BILGI_YOK"
        if parcalar:
            metin = parcalar[0].metin
            cumleler = [c.strip() for c in metin.replace("\n", " ").split(".") if c.strip()]
            govde = ". ".join(cumleler[:2]) + ("." if cumleler else "")
            return f"Belgeye göre: {govde}"
        return "Belgeye göre: bilgi bulunamadı."

    def yanitUretAkis(self, soru_metni, parcalar, baglam):
        tam = self.yanitUret(soru_metni, parcalar, baglam)
        for i in range(0, len(tam), 25):
            yield tam[i : i + 25]


class SahteAramaDizini:
    def __init__(self, sonuclar=None, sorgu_gommesi=None):
        self.sonuclar = sonuclar or []
        self.sorgu_gommesi = sorgu_gommesi
        self.gorulen_adet = None

    def enYakinParcalar(self, sorgu_gommesi, adet):
        self.gorulen_adet = adet
        return self.sonuclar[:adet]

