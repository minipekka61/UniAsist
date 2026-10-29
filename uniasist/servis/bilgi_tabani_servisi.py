from uniasist.entity import Belge
from uniasist.enumlar import Gorunurluk
from uniasist.hatalar import IsKuraliIhlaliException


class BilgiTabaniServisi:
    def __init__(self, bilgi_kaynagi_deposu, belge_isleme_servisi, arama_dizini,
                 ders_deposu=None):
        self.bilgi_kaynagi_deposu = bilgi_kaynagi_deposu
        self.belge_isleme_servisi = belge_isleme_servisi
        self.arama_dizini = arama_dizini
        self.ders_deposu = ders_deposu

    def belgeYukle(self, dosya_adi, dosya_yolu, boyut_byte, baslik, kategori, sahip,
                   gorunurluk=Gorunurluk.OZEL, ders_adi=""):
        if gorunurluk == Gorunurluk.PAYLASILAN and not sahip.dogrulanmisMi():
            raise IsKuraliIhlaliException(
                "IK-29",
                "Belge paylaşabilmek için e-posta adresinizi doğrulamanız gerekiyor.",
            )
        ders = None
        if ders_adi and self.ders_deposu is not None:
            ders = self.ders_deposu.bulVeYaOlustur(ders_adi)
        if gorunurluk == Gorunurluk.PAYLASILAN and ders is None:
            raise IsKuraliIhlaliException(
                "IK-24", "Paylaşmak için bir ders seçmelisiniz."
            )
        belge = Belge(
            baslik=baslik,
            kategori=kategori,
            dosya_adi=dosya_adi,
            dosya_turu=dosya_adi.rsplit(".", 1)[1].lower() if "." in dosya_adi else "",
            boyut_byte=boyut_byte,
            dosya_yolu=dosya_yolu,
            sahip_id=sahip.kullanici_id,
            gorunurluk=gorunurluk,
            universite_id=sahip.universite_id,
            bolum=sahip.bolum,
            ders_id=ders.ders_id if ders else None,
        )
        if not belge.dosyaGecerliMi():
            raise IsKuraliIhlaliException(
                "IK-24",
                "Belge yüklenemedi: yalnızca PDF veya TXT, en fazla 10 MB; "
                "başlık ve kategori zorunludur.",
            )
        self.bilgi_kaynagi_deposu.kaydet(belge)
        try:
            self.belge_isleme_servisi.isleVeIndeksle(belge)
        except IsKuraliIhlaliException:
            self.arama_dizini.kaynagaGoreSil(belge.kaynak_id)
            raise
        belge.aktifYap()
        self.bilgi_kaynagi_deposu.kaydet(belge)
        return belge

    def _belgeyiGetir(self, belge_id):
        belge = self.bilgi_kaynagi_deposu.idIleBul(belge_id)
        if belge is None:
            raise IsKuraliIhlaliException("IK-24", "Belge bulunamadı.")
        return belge

    def _sahiplikKontrol(self, belge, kullanici_id):
        if belge.sahip_id != kullanici_id:
            raise IsKuraliIhlaliException(
                "IK-30", "Bu belgeyi düzenleme yetkiniz yok."
            )

    def belgeGuncelle(self, belge_id, kullanici_id, baslik, kategori,
                      yeni_dosya_yolu=None, yeni_dosya_adi=None, yeni_boyut_byte=None,
                      yeni_ders_adi=None):
        belge = self._belgeyiGetir(belge_id)
        self._sahiplikKontrol(belge, kullanici_id)
        if yeni_ders_adi is not None:
            yeni_ders = None
            if yeni_ders_adi.strip() and self.ders_deposu is not None:
                yeni_ders = self.ders_deposu.bulVeYaOlustur(yeni_ders_adi)
            if belge.gorunurluk == Gorunurluk.PAYLASILAN and yeni_ders is None:
                raise IsKuraliIhlaliException(
                    "IK-24", "Paylaşmak için bir ders seçmelisiniz."
                )
            belge.ders_id = yeni_ders.ders_id if yeni_ders else None
            self.arama_dizini.dersGuncelle(belge.kaynak_id, belge.ders_id)
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

    def belgeSilZorla(self, belge_id):
        belge = self._belgeyiGetir(belge_id)
        self.arama_dizini.kaynagaGoreSil(belge.kaynak_id)
        self.bilgi_kaynagi_deposu.sil(belge_id)

    def belgeSil(self, belge_id, kullanici_id):
        belge = self._belgeyiGetir(belge_id)
        self._sahiplikKontrol(belge, kullanici_id)
        self.belgeSilZorla(belge_id)

    def gorunurlukDegistir(self, belge_id, kullanici, gorunurluk, ders_adi=None):
        belge = self._belgeyiGetir(belge_id)
        self._sahiplikKontrol(belge, kullanici.kullanici_id)
        if gorunurluk == Gorunurluk.PAYLASILAN and not kullanici.dogrulanmisMi():
            raise IsKuraliIhlaliException(
                "IK-29",
                "Belge paylaşabilmek için e-posta adresinizi doğrulamanız gerekiyor.",
            )
        if gorunurluk == Gorunurluk.PAYLASILAN:
            if ders_adi and ders_adi.strip() and self.ders_deposu is not None:
                ders = self.ders_deposu.bulVeYaOlustur(ders_adi)
                belge.ders_id = ders.ders_id
            if belge.ders_id is None:
                raise IsKuraliIhlaliException(
                    "IK-24", "Paylaşmak için bir ders seçmelisiniz."
                )
        belge.gorunurluk = gorunurluk
        self.bilgi_kaynagi_deposu.kaydet(belge)
        self.arama_dizini.gorunurlukGuncelle(belge.kaynak_id, gorunurluk)
        self.arama_dizini.dersGuncelle(belge.kaynak_id, belge.ders_id)
        return belge

    def belgeleriListele(self, kullanici_id):
        return self.bilgi_kaynagi_deposu.sahibinBelgeleri(kullanici_id)

    def dersinPaylasilanlari(self, ders_id):
        return self.bilgi_kaynagi_deposu.dersinPaylasilanlari(ders_id)

    def kaynagiGetir(self, kaynak_id):
        if kaynak_id is None:
            return None
        return self.bilgi_kaynagi_deposu.idIleBul(kaynak_id)
