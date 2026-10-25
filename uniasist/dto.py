from uniasist.enumlar import SonucDurumu


class YanitSonucu:
    def __init__(self, durum, metin="", kaynaklar=None):
        self.durum = durum
        self.metin = metin
        self.kaynaklar = kaynaklar if kaynaklar is not None else []

    def basarili(self):
        return self.durum == SonucDurumu.YANIT


class AramaSonucu:
    def __init__(self, parca, skor):
        self.parca = parca
        self.skor = skor


class KullanimRaporu:
    def __init__(self, baslangic, bitis, toplam_soru=0,
                 yanitlanamayan_orani=0.0, olumlu_geri_bildirim_orani=0.0,
                 en_cok_sorulan_kategoriler=None):
        self.baslangic = baslangic
        self.bitis = bitis
        self.toplam_soru = toplam_soru
        self.yanitlanamayan_orani = yanitlanamayan_orani
        self.olumlu_geri_bildirim_orani = olumlu_geri_bildirim_orani
        self.en_cok_sorulan_kategoriler = (
            en_cok_sorulan_kategoriler if en_cok_sorulan_kategoriler is not None else {}
        )

    def tarihAraligiGecerliMi(self):
        return self.bitis >= self.baslangic

    def csvOlustur(self):
        def yuzde(oran):
            return "%" + f"{oran * 100:.1f}".replace(".", ",")

        satirlar = ["Metrik;Değer"]
        satirlar.append(
            "Rapor Dönemi;{} - {}".format(
                self.baslangic.strftime("%d.%m.%Y"), self.bitis.strftime("%d.%m.%Y")
            )
        )
        satirlar.append(f"Toplam Soru;{self.toplam_soru}")
        satirlar.append(f"Yanıtlanamayan Soru Oranı;{yuzde(self.yanitlanamayan_orani)}")
        satirlar.append(
            f"Olumlu Geri Bildirim Oranı;{yuzde(self.olumlu_geri_bildirim_orani)}"
        )
        satirlar.append("")
        satirlar.append("En Çok Sorulan Kategoriler;Adet")
        for kategori, adet in self.en_cok_sorulan_kategoriler.items():
            satirlar.append(f"{kategori};{adet}")
        return "\n".join(satirlar) + "\n"


class GeriBildirimOzeti:
    def __init__(self, soru, yanit, kaynaklar=None, aciklama="", tarih=None):
        self.soru = soru
        self.yanit = yanit
        self.kaynaklar = kaynaklar if kaynaklar is not None else []
        self.aciklama = aciklama
        self.tarih = tarih
