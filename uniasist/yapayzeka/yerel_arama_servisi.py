import hashlib
import math
import re

from uniasist.yapayzeka.i_yapay_zeka_servisi import IYapayZekaServisi

_BOYUT = 512


class YerelAramaServisi(IYapayZekaServisi):
    @property
    def saglayici_etiketi(self):
        return "yerel:tfidf-2"

    def gommeUret(self, metin):
        sayimlar = {}
        metin = metin.lower()
        for n in (3, 4, 5):
            for i in range(len(metin) - n + 1):
                anahtar = self._sabit_hash(metin[i : i + n])
                sayimlar[anahtar] = sayimlar.get(anahtar, 0.0) + 1.0
        for kelime in metin.split():
            anahtar = self._sabit_hash(kelime)
            sayimlar[anahtar] = sayimlar.get(anahtar, 0.0) + 2.0
        v = [0.0] * _BOYUT
        for anahtar, sayi in sayimlar.items():
            v[anahtar % _BOYUT] += 1.0 + math.log(sayi)
        norm = math.sqrt(sum(x * x for x in v))
        if norm > 0:
            v = [x / norm for x in v]
        return v

    @staticmethod
    def _sabit_hash(metin):
        return int.from_bytes(hashlib.md5(metin.encode("utf-8")).digest()[:8], "big")

    def yanitUret(self, soru_metni, parcalar, baglam):
        if not parcalar:
            return "Belgeye göre: ilgili bilgi bulunamadı."
        metin = parcalar[0].metin
        cumleler = [c.strip() for c in re.split(r"(?<=[.!?])\s+|\n", metin) if c.strip()]
        if not cumleler:
            return "Belgeye göre: ilgili bilgi bulunamadı."
        soru_gomme = self.gommeUret(soru_metni)
        puanlar = [self._kosinus(self.gommeUret(c), soru_gomme) for c in cumleler]
        sirali = sorted(range(len(cumleler)), key=lambda i: puanlar[i], reverse=True)
        secilen = sorted(sirali[:3])
        govde = " ".join(cumleler[i] for i in secilen)
        return f"Belgeye göre: {govde}"

    def _kosinus(self, a, b):
        pay = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return pay / (na * nb)
