from datetime import datetime

import config
from uniasist.dto import Kapsam
from uniasist.entity import Mesaj, Sohbet, SoruKaydi
from uniasist.enumlar import GonderenTuru, Gorunurluk, SonucDurumu
from uniasist.hatalar import IsKuraliIhlaliException


class SohbetServisi:
    def __init__(self, sohbet_deposu, soru_kaydi_deposu, yanit_uretme_servisi,
                 yanitlanamayan_soru_servisi, bilgi_kaynagi_deposu=None,
                 kullanici_deposu=None, ders_deposu=None, plan_servisi=None):
        self.sohbet_deposu = sohbet_deposu
        self.soru_kaydi_deposu = soru_kaydi_deposu
        self.yanit_uretme_servisi = yanit_uretme_servisi
        self.yanitlanamayan_soru_servisi = yanitlanamayan_soru_servisi
        self.bilgi_kaynagi_deposu = bilgi_kaynagi_deposu
        self.kullanici_deposu = kullanici_deposu
        self.ders_deposu = ders_deposu
        self.plan_servisi = plan_servisi

    def _kapsamiKur(self, sohbet):
        if self.kullanici_deposu is None or sohbet.kullanici_id is None:
            return None
        kullanici = self.kullanici_deposu.idIleBul(sohbet.kullanici_id)
        if kullanici is None:
            return None
        ders_idler = set()
        if self.ders_deposu is not None:
            ders_idler = self.ders_deposu.kullanicininDersIdleri(kullanici.kullanici_id)
        return Kapsam(kullanici.kullanici_id, ders_idler)

    def _soruGecerliMi(self, soru_metni):
        if not soru_metni or not soru_metni.strip():
            return False
        return len(soru_metni.strip()) <= config.AZAMI_SORU_UZUNLUGU

    def _soruHakkiVar(self, sohbet):
        if self.plan_servisi is None or self.kullanici_deposu is None:
            return True
        if sohbet.kullanici_id is None:
            return True
        kullanici = self.kullanici_deposu.idIleBul(sohbet.kullanici_id)
        if kullanici is None:
            return True
        return self.plan_servisi.soruHakkiVarMi(kullanici)

    def yeniSohbetBaslat(self, kullanici):
        return Sohbet(
            baslik="Yeni sohbet",
            olusturma_zamani=datetime.now(),
            kullanici_id=kullanici.kullanici_id,
        )

    def soruSorAkis(self, sohbet, soru_metni):
        if not self._soruGecerliMi(soru_metni):
            yield {
                "tur": "hata",
                "kural": "IK-11",
                "mesaj": f"Soru 1 ile {config.AZAMI_SORU_UZUNLUGU} karakter arasında olmalıdır.",
            }
            return
        soru_metni = soru_metni.strip()
        if not self._soruHakkiVar(sohbet):
            yield {
                "tur": "hata",
                "kural": "IK-33",
                "mesaj": (
                    f"Günlük soru limitine ulaştınız "
                    f"({config.UCRETSIZ_GUNLUK_SORU}). Sınırsız sohbet için "
                    "Pro'ya geçin."
                ),
            }
            return
        baglam = sohbet.sonMesajlariGetir(config.BAGLAM_MESAJ_SAYISI)

        sonuc = None
        kapsam = self._kapsamiKur(sohbet)
        for olay in self.yanit_uretme_servisi.yanitUretAkis(
            soru_metni, baglam, kapsam=kapsam
        ):
            if olay["tur"] == "parca":
                yield {"tur": "parca", "metin": olay["metin"]}
            else:
                sonuc = olay["sonuc"]

        if sonuc.durum == SonucDurumu.SERVIS_HATASI:
            yield {
                "tur": "sonuc",
                "durum": sonuc.durum.value,
                "metin": sonuc.metin,
                "kaynaklar": [],
                "uyarilar": [],
                "yanit": None,
            }
            return

        if sohbet.bosMu() and sohbet.baslik in (None, "", "Yeni sohbet"):
            sohbet.baslik = soru_metni[:50]
        soru_mesaji = Mesaj(
            gonderen=GonderenTuru.KULLANICI, metin=soru_metni, zaman=datetime.now()
        )
        sohbet.mesajEkle(soru_mesaji)
        yanit_mesaji = Mesaj(
            gonderen=GonderenTuru.SISTEM, metin=sonuc.metin, zaman=datetime.now()
        )
        for referans in sonuc.kaynaklar:
            yanit_mesaji.kaynakEkle(referans)
        sohbet.mesajEkle(yanit_mesaji)
        self.sohbet_deposu.kaydet(sohbet)

        kategori = None
        if sonuc.kaynaklar:
            kategori = sonuc.kaynaklar[0].kategori or None
        if sonuc.durum == SonucDurumu.ICERIK_BULUNAMADI:
            self.yanitlanamayan_soru_servisi.kaydet(soru_metni)
        self.soru_kaydi_deposu.kaydet(
            SoruKaydi(
                zaman=datetime.now(),
                kategori=kategori,
                yanitlandi=sonuc.durum == SonucDurumu.YANIT,
                kullanici_id=sohbet.kullanici_id,
            )
        )
        yield {
            "tur": "sonuc",
            "durum": sonuc.durum.value,
            "metin": sonuc.metin,
            "kaynaklar": sonuc.kaynaklar,
            "uyarilar": [config.RESMI_UYARI, config.KISISEL_VERI_UYARISI],
            "yanit": yanit_mesaji,
        }

    def soruSor(self, sohbet, soru_metni):
        yanit = None
        for olay in self.soruSorAkis(sohbet, soru_metni):
            if olay["tur"] == "hata":
                raise IsKuraliIhlaliException(olay["kural"], olay["mesaj"])
            if olay["tur"] == "sonuc":
                yanit = olay["yanit"]
        return yanit

    def sohbetleriListele(self, kullanici_id):
        return self.sohbet_deposu.kullaniciSohbetleri(kullanici_id)

    def sohbetGetir(self, sohbet_id, kullanici_id):
        sohbet = self.sohbet_deposu.idIleBul(sohbet_id)
        if sohbet is None:
            raise IsKuraliIhlaliException("IK-21", "Sohbet bulunamadı.")
        if sohbet.kullanici_id != kullanici_id:
            raise IsKuraliIhlaliException(
                "IK-21", "Bu sohbeti görüntüleme yetkiniz yok."
            )
        return sohbet

    def sohbetSil(self, sohbet_id, kullanici_id):
        sohbet = self.sohbetGetir(sohbet_id, kullanici_id)
        self.sohbet_deposu.sil(sohbet.sohbet_id)

    def tumSohbetleriSil(self, kullanici_id):
        self.sohbet_deposu.kullaniciSohbetleriniSil(kullanici_id)

    def kaynagiGoruntule(self, referans, kullanici):
        if referans is None or referans.kaynak_id is None:
            return None
        if self.bilgi_kaynagi_deposu is None:
            return None
        kaynak = self.bilgi_kaynagi_deposu.idIleBul(referans.kaynak_id)
        if kaynak is None or not kaynak.aktifMi():
            return None
        if not self._kaynakErisilebilirMi(kaynak, kullanici):
            return None
        return kaynak

    def _kaynakErisilebilirMi(self, kaynak, kullanici):
        if kullanici is None:
            return False
        if kaynak.sahip_id == kullanici.kullanici_id:
            return True
        if kaynak.gorunurluk != Gorunurluk.PAYLASILAN:
            return False
        if self.ders_deposu is None:
            return False
        return kaynak.ders_id in self.ders_deposu.kullanicininDersIdleri(
            kullanici.kullanici_id
        )
