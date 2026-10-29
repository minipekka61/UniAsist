import re

import config
from uniasist.entity import IcerikParcasi
from uniasist.hatalar import IsKuraliIhlaliException


class BelgeIslemeServisi:
    def __init__(self, arama_dizini, yapay_zeka_servisi, yeniden_deneme=None):
        self.arama_dizini = arama_dizini
        self.yapay_zeka_servisi = yapay_zeka_servisi
        self.yeniden_deneme = yeniden_deneme or config.YENIDEN_DENEME

    def parcalaraBol(self, metin):
        temiz = re.sub(r"\s+", " ", metin.strip())
        cumleler = [c for c in re.split(r"(?<=[.!?])\s+", temiz) if c.strip()]
        parcalar = []
        su_anki = []
        uzunluk = 0
        for cumle in cumleler:
            ek = len(cumle) + (1 if uzunluk > 0 else 0)
            if uzunluk + ek > config.PARCA_BOYUTU and su_anki:
                parcalar.append(" ".join(su_anki))
                kalan = []
                toplam = 0
                for onceki in reversed(su_anki):
                    if toplam + len(onceki) + 1 > config.PARCA_ORTUSME:
                        break
                    kalan.insert(0, onceki)
                    toplam += len(onceki) + 1
                su_anki = kalan
                uzunluk = sum(len(x) + 1 for x in kalan)
            su_anki.append(cumle)
            uzunluk += ek
        if su_anki:
            parcalar.append(" ".join(su_anki))
        return [
            IcerikParcasi(kaynak_id=None, sira=i + 1, metin=p)
            for i, p in enumerate(parcalar)
        ]

    def _gommeUret(self, metin):
        for _ in range(self.yeniden_deneme):
            try:
                return self.yapay_zeka_servisi.gommeUret(metin)
            except Exception:
                continue
        raise IsKuraliIhlaliException(
            "IK-25", "Belge işlenemedi: indeksleme başarısız oldu."
        )

    def isleVeIndeksle(self, belge):
        try:
            metin = belge.icerikMetniGetir()
        except Exception:
            raise IsKuraliIhlaliException(
                "IK-25", "Belge işlenemedi: metin okunamadı."
            )
        if not metin or len(metin.strip()) < 50:
            raise IsKuraliIhlaliException(
                "IK-25", "Belge işlenemedi: metin okunamadı."
            )
        parcalar = self.parcalaraBol(metin)
        for parca in parcalar:
            parca.kaynak_id = belge.kaynak_id
            parca.surum_no = belge.surum_no
            parca.kaynak_adi = belge.kaynakAdiGetir()
            parca.kategori = belge.kategori
            parca.gomme_saglayici = self.yapay_zeka_servisi.saglayici_etiketi
            parca._bolum_bilgisi = f"{belge.baslik} — parça {parca.sira}"
            parca.sahip_id = belge.sahip_id
            parca.gorunurluk = belge.gorunurluk
            parca.universite_id = belge.universite_id
            parca.bolum = belge.bolum
            parca.ders_id = belge.ders_id
            parca.gomme = self._gommeUret(parca.metin)
            self.arama_dizini.parcaEkle(parca)
        return parcalar
