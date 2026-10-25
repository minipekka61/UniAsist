from uniasist.entity import Belge, IcerikParcasi, SSSGirdisi
from uniasist.enumlar import KaynakDurumu
from uniasist.hatalar import IsKuraliIhlaliException


class BilgiTabaniServisi:
    def __init__(self, bilgi_kaynagi_deposu, belge_isleme_servisi, arama_dizini):
        self.bilgi_kaynagi_deposu = bilgi_kaynagi_deposu
        self.belge_isleme_servisi = belge_isleme_servisi
        self.arama_dizini = arama_dizini

    def belgeYukle(self, dosya_adi, dosya_yolu, boyut_byte, baslik, kategori):
        belge = Belge(
            baslik=baslik,
            kategori=kategori,
            dosya_adi=dosya_adi,
            dosya_turu=dosya_adi.rsplit(".", 1)[1].lower() if "." in dosya_adi else "",
            boyut_byte=boyut_byte,
            dosya_yolu=dosya_yolu,
        )
        if not belge.dosyaGecerliMi():
            raise IsKuraliIhlaliException(
                "IK-24",
                "Belge yüklenemedi: yalnızca PDF veya TXT, en fazla 10 MB; "
                "başlık ve kategori zorunludur.",
            )
        self.bilgi_kaynagi_deposu.kaydet(belge)
        self.belge_isleme_servisi.isleVeIndeksle(belge)
        belge.aktifYap()
        self.bilgi_kaynagi_deposu.kaydet(belge)
        return belge

    def belgeGuncelle(self, belge_id, baslik, kategori, yeni_dosya_yolu=None,
                      yeni_dosya_adi=None, yeni_boyut_byte=None):
        belge = self.bilgi_kaynagi_deposu.idIleBul(belge_id)
        if belge is None:
            raise IsKuraliIhlaliException("IK-24", "Güncellenecek belge bulunamadı.")
        if yeni_dosya_yolu:
            deneme = Belge(
                baslik=baslik,
                kategori=kategori,
                dosya_adi=yeni_dosya_adi,
                dosya_turu=yeni_dosya_adi.rsplit(".", 1)[1].lower() if "." in yeni_dosya_adi else "",
                boyut_byte=yeni_boyut_byte,
                dosya_yolu=yeni_dosya_yolu,
            )
            if not deneme.dosyaGecerliMi():
                raise IsKuraliIhlaliException(
                    "IK-24",
                    "Yeni dosya geçersiz: yalnızca PDF veya TXT, en fazla 10 MB; "
                    "başlık ve kategori zorunludur.",
                )
            eski = dict(
                dosya_adi=belge.dosya_adi,
                dosya_turu=belge.dosya_turu,
                dosya_yolu=belge.dosya_yolu,
                boyut_byte=belge.boyut_byte,
                surum_no=belge.surum_no,
                baslik=belge.baslik,
                kategori=belge.kategori,
            )
            belge.baslik = baslik
            belge.kategori = kategori
            belge.yeniSurumAta(yeni_dosya_adi, yeni_dosya_yolu, yeni_boyut_byte)
            self.bilgi_kaynagi_deposu.kaydet(belge)
            try:
                self.belge_isleme_servisi.isleVeIndeksle(belge)
            except IsKuraliIhlaliException:
                self.arama_dizini.surumeGoreSil(belge.kaynak_id, belge.surum_no)
                for alan, deger in eski.items():
                    setattr(belge, alan, deger)
                self.bilgi_kaynagi_deposu.kaydet(belge)
                raise
            self.arama_dizini.surumeGoreSil(belge.kaynak_id, eski["surum_no"])
            belge.aktifYap()
            self.bilgi_kaynagi_deposu.kaydet(belge)
            return belge
        belge.baslik = baslik
        belge.kategori = kategori
        self.bilgi_kaynagi_deposu.kaydet(belge)
        return belge

    def belgeSil(self, belge_id):
        belge = self.bilgi_kaynagi_deposu.idIleBul(belge_id)
        if belge is None:
            raise IsKuraliIhlaliException("IK-24", "Silinecek belge bulunamadı.")
        self.arama_dizini.kaynagaGoreSil(belge.kaynak_id)
        self.bilgi_kaynagi_deposu.sil(belge_id)

    def belgeleriListele(self):
        return self.bilgi_kaynagi_deposu.belgeler()

    def sssEkle(self, soru, cevap, kategori):
        girdi = SSSGirdisi(baslik=soru, kategori=kategori, soru=soru, cevap=cevap)
        if not girdi.alanlarGecerliMi():
            raise IsKuraliIhlaliException(
                "IK-28", "SSS girdisinde soru, cevap ve kategori alanları zorunludur."
            )
        for kaynak in self.bilgi_kaynagi_deposu.aktifKaynaklar():
            if isinstance(kaynak, SSSGirdisi) and kaynak.soru.strip() == soru.strip():
                raise IsKuraliIhlaliException(
                    "IK-28",
                    "Bu soru SSS'de zaten var; mevcut girdiyi güncellemeniz önerilir.",
                )
        girdi.aktifYap()
        self.bilgi_kaynagi_deposu.kaydet(girdi)
        parca = IcerikParcasi(
            kaynak_id=girdi.kaynak_id,
            sira=1,
            metin=girdi.icerikMetniGetir(),
            kaynak_adi="SSS",
            kategori=girdi.kategori,
        )
        parca.gomme = self.belge_isleme_servisi._gommeUret(parca.metin)
        parca.gomme_saglayici = self.belge_isleme_servisi.yapay_zeka_servisi.saglayici_etiketi
        parca._bolum_bilgisi = f"{girdi.baslik} — SSS"
        self.arama_dizini.parcaEkle(parca)
        return girdi

    def kaynagiGetir(self, kaynak_id):
        if kaynak_id is None:
            return None
        return self.bilgi_kaynagi_deposu.idIleBul(kaynak_id)
