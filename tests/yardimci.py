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
    def __init__(self, mod="yanit"):
        self.mod = mod
        self.cagri_sayisi = 0
        self.gorulen_baglam = None
        self.gorulen_parcalar = None

    @property
    def saglayici_etiketi(self):
        return "sahte:test"

    def gommeUret(self, metin):
        return yerel_gomme(metin)

    def yanitUret(self, soru_metni, parcalar, baglam):
        self.cagri_sayisi += 1
        self.gorulen_baglam = baglam
        self.gorulen_parcalar = parcalar
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
