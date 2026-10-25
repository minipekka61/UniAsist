from datetime import datetime, timedelta

from uniasist.dto import KullanimRaporu
from uniasist.hatalar import IsKuraliIhlaliException


class RaporServisi:
    def __init__(self, soru_kaydi_deposu, geri_bildirim_deposu):
        self.soru_kaydi_deposu = soru_kaydi_deposu
        self.geri_bildirim_deposu = geri_bildirim_deposu

    def raporOlustur(self, baslangic=None, bitis=None):
        if bitis is None:
            bitis = datetime.now()
        if baslangic is None:
            baslangic = bitis - timedelta(days=30)
        if bitis < baslangic:
            raise IsKuraliIhlaliException(
                "IK-33", "Bitiş tarihi başlangıç tarihinden önce olamaz."
            )
        kayitlar = self.soru_kaydi_deposu.araliktakiKayitlar(baslangic, bitis)
        toplam = len(kayitlar)
        yanitlanamayan = sum(1 for k in kayitlar if not k.yanitlandi)
        kategori_sayilari = {}
        for k in kayitlar:
            if k.kategori:
                kategori_sayilari[k.kategori] = kategori_sayilari.get(k.kategori, 0) + 1
        en_cok = dict(
            sorted(kategori_sayilari.items(), key=lambda o: o[1], reverse=True)[:5]
        )
        return KullanimRaporu(
            baslangic=baslangic,
            bitis=bitis,
            toplam_soru=toplam,
            yanitlanamayan_orani=(yanitlanamayan / toplam) if toplam else 0.0,
            olumlu_geri_bildirim_orani=self.geri_bildirim_deposu.araliktakiOlumluOrani(
                baslangic, bitis
            ),
            en_cok_sorulan_kategoriler=en_cok,
        )

    def csvHazirla(self, rapor):
        return rapor.csvOlustur()
