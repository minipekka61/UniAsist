import math
import re

from uniasist.yapayzeka.i_yapay_zeka_servisi import IYapayZekaServisi

_BOYUT = 512


class YerelAramaServisi(IYapayZekaServisi):
    @property
    def saglayici_etiketi(self):
        return "yerel:tfidf-1"

    def gommeUret(self, metin):
        sayimlar = {}
        metin = metin.lower()
        for n in (3, 4, 5):
            for i in range(len(metin) - n + 1):
                anahtar = hash(metin[i : i + n])
                sayimlar[anahtar] = sayimlar.get(anahtar, 0.0) + 1.0
        for kelime in metin.split():
            anahtar = hash(kelime)
            sayimlar[anahtar] = sayimlar.get(anahtar, 0.0) + 2.0
        v = [0.0] * _BOYUT
        for anahtar, sayi in sayimlar.items():
            v[anahtar % _BOYUT] += 1.0 + math.log(sayi)
        norm = math.sqrt(sum(x * x for x in v))
        if norm > 0:
            v = [x / norm for x in v]
        return v

    def yanitUret(self, soru_metni, parcalar, baglam):
        if not parcalar:
            return "Belgeye göre: ilgili bilgi bulunamadı."
        metin = parcalar[0].metin
        cumleler = [c.strip() for c in re.split(r"[.\n]", metin) if c.strip()]
        govde = ". ".join(cumleler[:2])
        if govde and not govde.endswith("."):
            govde += "."
        return f"Belgeye göre: {govde}"
