from datetime import datetime

from uniasist.dto import GeriBildirimOzeti
from uniasist.entity import GeriBildirim
from uniasist.enumlar import GonderenTuru
from uniasist.hatalar import IsKuraliIhlaliException


class GeriBildirimServisi:
    def __init__(self, sohbet_deposu, geri_bildirim_deposu):
        self.sohbet_deposu = sohbet_deposu
        self.geri_bildirim_deposu = geri_bildirim_deposu

    def geriBildirimVer(self, kullanici_id, mesaj_id, tur, aciklama):
        mesaj = self.sohbet_deposu.mesajBul(mesaj_id)
        if mesaj is None:
            raise IsKuraliIhlaliException("IK-22", "Yanıt bulunamadı.")
        sohbet = self.sohbet_deposu.idIleBul(mesaj.sohbet_id, mesajlarla=False)
        if sohbet is None or sohbet.kullanici_id != kullanici_id:
            raise IsKuraliIhlaliException(
                "NFR-04", "Yalnızca kendi yanıtlarınıza geri bildirim verebilirsiniz."
            )
        if aciklama and len(aciklama) > 300:
            raise IsKuraliIhlaliException(
                "IK-22", "Açıklama en fazla 300 karakter olabilir."
            )
        mevcut = self.geri_bildirim_deposu.mesajIcininBul(mesaj_id, kullanici_id)
        if mevcut is not None:
            mevcut.guncelle(tur, aciklama)
            mevcut.zaman = datetime.now()
            self.geri_bildirim_deposu.kaydet(mevcut)
            return mevcut
        geri_bildirim = GeriBildirim(
            mesaj_id=mesaj_id,
            kullanici_id=kullanici_id,
            tur=tur,
            aciklama=aciklama,
            zaman=datetime.now(),
        )
        self.geri_bildirim_deposu.kaydet(geri_bildirim)
        return geri_bildirim

    def yararsizlariListele(self):
        ozetler = []
        for gb in self.geri_bildirim_deposu.yararsizlar():
            mesaj = self.sohbet_deposu.mesajBul(gb.mesaj_id)
            if mesaj is None:
                continue
            sohbet = self.sohbet_deposu.idIleBul(mesaj.sohbet_id, mesajlarla=True)
            soru = ""
            if sohbet is not None:
                sorular = [m for m in sohbet.mesajlar if m.gonderen == GonderenTuru.KULLANICI]
                if sorular:
                    soru = sorular[0].metin
            ozetler.append(
                GeriBildirimOzeti(
                    soru=soru,
                    yanit=mesaj.metin,
                    kaynaklar=[r.kaynak_adi for r in mesaj.kaynaklariGetir()],
                    aciklama=gb.aciklama or "",
                    tarih=gb.zaman,
                )
            )
        return ozetler
