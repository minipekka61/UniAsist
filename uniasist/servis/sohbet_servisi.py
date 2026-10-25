from datetime import datetime

import config
from uniasist.entity import Mesaj, Sohbet, SoruKaydi
from uniasist.enumlar import GonderenTuru, SonucDurumu
from uniasist.hatalar import IsKuraliIhlaliException

KAPSAM_ANAHTAR_SOZCUKLERI = [
    "ders", "sınav", "sinav", "kayıt", "kayit", "burs", "yurt", "staj",
    "mezuniyet", "mezun", "akademik takvim", "bırakma", "birakma",
    "çift anadal", "cift anadal", "yatay geçiş", "yatay gecis", "üniversite",
    "universite", "fakülte", "fakulte", "bölüm", "bolum", "öğrenci", "ogrenci",
    "diploma", "tez", "kredi", "danışman", "danisman", "harf notu",
    "yaz okulu", "müfredat", "mufredat", "lisansüstü", "lisansustu",
    "dilekçe", "dilekce", "öğrenim", "ogrenim", "akts", "devamsızlık",
    "devamsizlik", "kayıt yenileme", "kayit yenileme", "transkript",
    "öğrenci işleri", "ogrenci isleri", "seminer", "asistan", "mülakat",
    "mulakat", "bahar", "güz", "guz", "dünya", "sözlük", "yeniden",
]

KARA_LISTE = [
    "hava", "spor", "futbol", "basketbol", "yemek tarifi", "şarkı", "sarki",
    "fıkra", "fikra", "film", "dizi", "döviz", "doviz", "piyango", "borsa",
    "astroloji", "burç", "burc", "güzel söz", "siir", "şiir",
]


class SohbetServisi:
    def __init__(self, sohbet_deposu, soru_kaydi_deposu, yanit_uretme_servisi,
                 yanitlanamayan_soru_servisi, bilgi_kaynagi_deposu=None):
        self.sohbet_deposu = sohbet_deposu
        self.soru_kaydi_deposu = soru_kaydi_deposu
        self.yanit_uretme_servisi = yanit_uretme_servisi
        self.yanitlanamayan_soru_servisi = yanitlanamayan_soru_servisi
        self.bilgi_kaynagi_deposu = bilgi_kaynagi_deposu
        self.ziyaretci_sohbetleri = {}

    def _soruGecerliMi(self, soru_metni):
        if not soru_metni or not soru_metni.strip():
            return False
        return len(soru_metni.strip()) <= config.AZAMI_SORU_UZUNLUGU

    def _kapsamIcindeMi(self, soru_metni, baglam_var_mi):
        metin = soru_metni.lower()
        if any(a in metin for a in KAPSAM_ANAHTAR_SOZCUKLERI):
            return True
        if baglam_var_mi:
            return True
        if any(k in metin for k in KARA_LISTE):
            return False
        return True

    def yeniSohbetBaslat(self, kullanici=None, ziyaretci_oturum_id=None):
        if kullanici is not None:
            return Sohbet(
                baslik="Yeni sohbet",
                olusturma_zamani=datetime.now(),
                kullanici_id=kullanici.kullanici_id,
            )
        if ziyaretci_oturum_id in self.ziyaretci_sohbetleri:
            return self.ziyaretci_sohbetleri[ziyaretci_oturum_id]
        sohbet = Sohbet(
            baslik="Ziyaretçi sohbeti",
            olusturma_zamani=datetime.now(),
            ziyaretci_oturum_id=ziyaretci_oturum_id,
        )
        self.ziyaretci_sohbetleri[ziyaretci_oturum_id] = sohbet
        return sohbet

    def soruSorAkis(self, sohbet, soru_metni):
        if not self._soruGecerliMi(soru_metni):
            yield {
                "tur": "hata",
                "kural": "IK-11",
                "mesaj": f"Soru 1 ile {config.AZAMI_SORU_UZUNLUGU} karakter arasında olmalıdır.",
            }
            return
        soru_metni = soru_metni.strip()
        baglam = sohbet.sonMesajlariGetir(config.BAGLAM_MESAJ_SAYISI)
        if not self._kapsamIcindeMi(soru_metni, bool(baglam)):
            yield {"tur": "hata", "kural": "IK-15", "mesaj": config.KAPSAM_METNI}
            return

        sonuc = None
        for olay in self.yanit_uretme_servisi.yanitUretAkis(soru_metni, baglam):
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

        if sohbet.bosMu() and sohbet.baslik in (None, "", "Yeni sohbet", "Ziyaretçi sohbeti"):
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
        if sohbet.kaliciMi():
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

    def kaynagiGoruntule(self, referans):
        if referans is None or referans.kaynak_id is None:
            return None
        if self.bilgi_kaynagi_deposu is None:
            return None
        kaynak = self.bilgi_kaynagi_deposu.idIleBul(referans.kaynak_id)
        if kaynak is None or not kaynak.aktifMi():
            return None
        return kaynak
