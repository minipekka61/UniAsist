import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path

import config
from uniasist.enumlar import (
    GonderenTuru,
    HesapDurumu,
    KayitDurumu,
    KaynakDurumu,
)
from uniasist.guvenlik import sifre_dogrula


class Kullanici:
    def __init__(self, ad_soyad, eposta, sifre_hash, rol, kullanici_id=None,
                 durum=HesapDurumu.AKTIF, basarisiz_deneme_sayisi=0,
                 kilit_bitis_zamani=None, kayit_tarihi=None,
                 universite_id=None, bolum="", eposta_dogrulandi=False,
                 dogrulama_token=None, dogrulama_bitis=None):
        self.kullanici_id = kullanici_id
        self.ad_soyad = ad_soyad
        self.eposta = eposta
        self.sifre_hash = sifre_hash
        self.rol = rol
        self.durum = durum
        self.basarisiz_deneme_sayisi = basarisiz_deneme_sayisi
        self.kilit_bitis_zamani = kilit_bitis_zamani
        self.kayit_tarihi = kayit_tarihi or datetime.now()
        self.universite_id = universite_id
        self.bolum = bolum
        self.eposta_dogrulandi = bool(eposta_dogrulandi)
        self.dogrulama_token = dogrulama_token
        self.dogrulama_bitis = dogrulama_bitis

    def dogrulanmisMi(self):
        return self.eposta_dogrulandi

    def epostaDogrula(self):
        self.eposta_dogrulandi = True
        self.dogrulama_token = None
        self.dogrulama_bitis = None

    def dogrulamaTokenAta(self, token, bitis):
        self.dogrulama_token = token
        self.dogrulama_bitis = bitis

    def sifreDogrula(self, sifre):
        return sifre_dogrula(sifre, self.sifre_hash)

    def kilitliMi(self):
        return (
            self.kilit_bitis_zamani is not None
            and datetime.now() < self.kilit_bitis_zamani
        )

    def aktifMi(self):
        return self.durum == HesapDurumu.AKTIF

    def basarisizDenemeKaydet(self):
        simdi = datetime.now()
        if self.kilit_bitis_zamani is not None and self.kilit_bitis_zamani <= simdi:
            self.basarisiz_deneme_sayisi = 0
            self.kilit_bitis_zamani = None
        self.basarisiz_deneme_sayisi += 1
        if self.basarisiz_deneme_sayisi >= config.AZAMI_HATALI_DENEME:
            self.kilit_bitis_zamani = simdi + timedelta(
                minutes=config.KILIT_SURESI_DK
            )

    def denemeleriSifirla(self):
        self.basarisiz_deneme_sayisi = 0
        self.kilit_bitis_zamani = None

    def sifreGuncelle(self, yeni_hash):
        self.sifre_hash = yeni_hash

    def rolDegistir(self, yeni_rol):
        self.rol = yeni_rol

    def devreDisiBirak(self):
        self.durum = HesapDurumu.DEVRE_DISI


class Oturum:
    def __init__(self, oturum_id, kullanici_id, olusturma_zamani,
                 son_etkinlik_zamani, aktif=True):
        self.oturum_id = oturum_id
        self.kullanici_id = kullanici_id
        self.olusturma_zamani = olusturma_zamani
        self.son_etkinlik_zamani = son_etkinlik_zamani
        self.aktif = aktif

    def sureDoldu(self):
        return (
            datetime.now() - self.son_etkinlik_zamani
            > timedelta(minutes=config.OTURUM_SURESI_DK)
        )

    def etkinlikGuncelle(self):
        self.son_etkinlik_zamani = datetime.now()

    def sonlandir(self):
        self.aktif = False


class Sohbet:
    def __init__(self, baslik, olusturma_zamani, kullanici_id=None,
                 ziyaretci_oturum_id=None, sohbet_id=None, mesajlar=None):
        self.sohbet_id = sohbet_id
        self.kullanici_id = kullanici_id
        self.ziyaretci_oturum_id = ziyaretci_oturum_id
        self.baslik = baslik
        self.olusturma_zamani = olusturma_zamani
        self.mesajlar = mesajlar if mesajlar is not None else []

    def mesajEkle(self, mesaj):
        self.mesajlar.append(mesaj)

    def sonMesajlariGetir(self, adet):
        if adet <= 0:
            return []
        return self.mesajlar[-adet:]

    def bosMu(self):
        return len(self.mesajlar) == 0

    def kaliciMi(self):
        return self.kullanici_id is not None


class Mesaj:
    def __init__(self, gonderen, metin, zaman, mesaj_id=None, sohbet_id=None,
                 kaynaklar=None):
        self.mesaj_id = mesaj_id
        self.sohbet_id = sohbet_id
        self.gonderen = gonderen
        self.metin = metin
        self.zaman = zaman
        self.kaynaklar = kaynaklar if kaynaklar is not None else []

    def kaynakEkle(self, referans):
        self.kaynaklar.append(referans)

    def kaynaklariGetir(self):
        return list(self.kaynaklar)


class KaynakReferansi:
    def __init__(self, bolum_bilgisi="", kaynak_adi="", benzerlik_skoru=0.0,
                 kaynak_id=None, kategori=""):
        self.kaynak_id = kaynak_id
        self.bolum_bilgisi = bolum_bilgisi
        self.kaynak_adi = kaynak_adi
        self.benzerlik_skoru = benzerlik_skoru
        self.kategori = kategori

    def kaynakMevcutMu(self):
        return self.kaynak_id is not None

    def kaynakAdiGetir(self):
        return self.kaynak_adi


class GeriBildirim:
    def __init__(self, mesaj_id, kullanici_id, tur, aciklama, zaman,
                 geri_bildirim_id=None):
        self.geri_bildirim_id = geri_bildirim_id
        self.mesaj_id = mesaj_id
        self.kullanici_id = kullanici_id
        self.tur = tur
        self.aciklama = aciklama
        self.zaman = zaman

    def guncelle(self, tur, aciklama):
        self.tur = tur
        self.aciklama = aciklama

    def aciklamaGecerliMi(self):
        return self.aciklama is None or len(self.aciklama) <= 300


class BilgiKaynagi(ABC):
    def __init__(self, tur, baslik="", kategori="", kaynak_id=None,
                 durum=KaynakDurumu.PASIF, olusturma_tarihi=None,
                 guncelleme_tarihi=None):
        self.kaynak_id = kaynak_id
        self.tur = tur
        self.baslik = baslik
        self.kategori = kategori
        self.durum = durum
        self.olusturma_tarihi = olusturma_tarihi or datetime.now()
        self.guncelleme_tarihi = guncelleme_tarihi or datetime.now()

    def aktifMi(self):
        return self.durum == KaynakDurumu.AKTIF

    def aktifYap(self):
        self.durum = KaynakDurumu.AKTIF
        self.guncelleme_tarihi = datetime.now()

    def pasifYap(self):
        self.durum = KaynakDurumu.PASIF
        self.guncelleme_tarihi = datetime.now()

    @abstractmethod
    def icerikMetniGetir(self):
        ...

    @abstractmethod
    def kaynakAdiGetir(self):
        ...


class Belge(BilgiKaynagi):
    def __init__(self, baslik="", kategori="", dosya_adi="", dosya_turu="",
                 boyut_byte=0, dosya_yolu="", surum_no=1, **kwargs):
        kwargs.setdefault("tur", "BELGE")
        super().__init__(baslik=baslik, kategori=kategori, **kwargs)
        self.dosya_adi = dosya_adi
        self.dosya_turu = dosya_turu.lower()
        self.boyut_byte = boyut_byte
        self.dosya_yolu = dosya_yolu
        self.surum_no = surum_no

    def dosyaGecerliMi(self):
        if self.dosya_turu not in ("pdf", "txt"):
            return False
        if self.boyut_byte is None or self.boyut_byte > config.AZAMI_BELGE_BOYUTU:
            return False
        return bool(self.baslik.strip() and self.kategori.strip())

    def yeniSurumAta(self, dosya_adi, dosya_yolu, boyut_byte):
        self.surum_no += 1
        self.dosya_adi = dosya_adi
        self.dosya_yolu = dosya_yolu
        self.boyut_byte = boyut_byte
        if "." in dosya_adi:
            self.dosya_turu = dosya_adi.rsplit(".", 1)[1].lower()

    def icerikMetniGetir(self):
        if self.dosya_turu == "txt":
            return Path(self.dosya_yolu).read_text(encoding="utf-8")
        from pypdf import PdfReader
        okuyucu = PdfReader(self.dosya_yolu)
        return "\n".join(sayfa.extract_text() or "" for sayfa in okuyucu.pages)

    def kaynakAdiGetir(self):
        return self.dosya_adi


class SSSGirdisi(BilgiKaynagi):
    def __init__(self, baslik="", kategori="", soru="", cevap="", **kwargs):
        kwargs.setdefault("tur", "SSS")
        super().__init__(baslik=baslik or soru, kategori=kategori, **kwargs)
        self.soru = soru
        self.cevap = cevap

    def alanlarGecerliMi(self):
        return bool(
            self.soru.strip() and self.cevap.strip() and self.kategori.strip()
        )

    def icerikMetniGetir(self):
        return f"S: {self.soru}\nC: {self.cevap}"

    def kaynakAdiGetir(self):
        return "SSS"


class IcerikParcasi:
    def __init__(self, kaynak_id, sira, metin, gomme=None, surum_no=1,
                 gomme_saglayici="", kaynak_adi="", bolum_bilgisi=None,
                 kategori="", aktif=True, parca_id=None):
        self.parca_id = parca_id
        self.kaynak_id = kaynak_id
        self.surum_no = surum_no
        self.sira = sira
        self.metin = metin
        self.gomme = gomme
        self.gomme_saglayici = gomme_saglayici
        self.kaynak_adi = kaynak_adi
        self.kategori = kategori
        self._bolum_bilgisi = bolum_bilgisi
        self.aktif = aktif

    def benzerlikHesapla(self, sorgu_gommesi):
        if not self.gomme or not sorgu_gommesi:
            return 0.0
        if len(self.gomme) != len(sorgu_gommesi):
            return 0.0
        pay = sum(a * b for a, b in zip(self.gomme, sorgu_gommesi))
        norm_a = math.sqrt(sum(a * a for a in self.gomme))
        norm_b = math.sqrt(sum(b * b for b in sorgu_gommesi))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return pay / (norm_a * norm_b)

    def bolumBilgisiGetir(self):
        if self._bolum_bilgisi:
            return self._bolum_bilgisi
        return f"{self.kaynak_adi} — parça {self.sira}"


class YanitlanamayanSoru:
    def __init__(self, soru_metni, ilk_tarih, kayit_id=None, tekrar_sayisi=1,
                 durum=KayitDurumu.ACIK):
        self.kayit_id = kayit_id
        self.soru_metni = soru_metni
        self.ilk_tarih = ilk_tarih
        self.tekrar_sayisi = tekrar_sayisi
        self.durum = durum

    def tekrarArtir(self):
        self.tekrar_sayisi += 1

    def coz(self):
        self.durum = KayitDurumu.COZULDU


class SoruKaydi:
    def __init__(self, zaman, kategori=None, yanitlandi=False, kayit_id=None):
        self.kayit_id = kayit_id
        self.zaman = zaman
        self.kategori = kategori
        self.yanitlandi = yanitlandi


class Universite:
    def __init__(self, ad, eposta_alan_adi, universite_id=None):
        self.universite_id = universite_id
        self.ad = ad
        self.eposta_alan_adi = eposta_alan_adi
