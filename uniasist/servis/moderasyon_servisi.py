from datetime import datetime

from uniasist.entity import Bildirim
from uniasist.enumlar import Gorunurluk
from uniasist.hatalar import IsKuraliIhlaliException


class ModerasyonServisi:
    def __init__(self, bildirim_deposu, bilgi_tabani_servisi):
        self.bildirim_deposu = bildirim_deposu
        self.bilgi_tabani_servisi = bilgi_tabani_servisi

    def bildir(self, belge_id, bildiren, neden):
        belge = self.bilgi_tabani_servisi.kaynagiGetir(belge_id)
        if belge is None:
            raise IsKuraliIhlaliException("IK-31", "Belge bulunamadı.")
        if belge.gorunurluk != Gorunurluk.PAYLASILAN:
            raise IsKuraliIhlaliException(
                "IK-31", "Yalnızca paylaşıma açılmış belgeler bildirilebilir."
            )
        if belge.sahip_id == bildiren.kullanici_id:
            raise IsKuraliIhlaliException(
                "IK-31", "Kendi belgenizi bildiremezsiniz."
            )
        if self.bildirim_deposu.belgeVeKisiyeGoreBul(belge_id, bildiren.kullanici_id) is not None:
            raise IsKuraliIhlaliException(
                "IK-31", "Bu belgeyi zaten bildirdiniz; inceleme bekliyor."
            )
        bildirim = Bildirim(
            belge_id=belge_id,
            bildiren_id=bildiren.kullanici_id,
            neden=(neden or "").strip(),
            tarih=datetime.now(),
        )
        self.bildirim_deposu.kaydet(bildirim)
        return bildirim

    def acikBildirimler(self):
        sonuc = []
        for bildirim in self.bildirim_deposu.aciklariListele():
            belge = self.bilgi_tabani_servisi.kaynagiGetir(bildirim.belge_id)
            if belge is None:
                continue
            sonuc.append((bildirim, belge))
        return sonuc

    def bildirimiDegerlendir(self, bildirim_id, silinsin):
        bildirim = self.bildirim_deposu.idIleBul(bildirim_id)
        if bildirim is None:
            raise IsKuraliIhlaliException("IK-32", "Bildirim bulunamadı.")
        if silinsin:
            self.bilgi_tabani_servisi.belgeSilZorla(bildirim.belge_id)
        self.bildirim_deposu.degerlendirildiIsaretle(bildirim.bildirim_id)
