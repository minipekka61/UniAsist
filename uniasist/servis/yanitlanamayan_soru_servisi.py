from uniasist.entity import YanitlanamayanSoru
from uniasist.enumlar import KayitDurumu
from uniasist.hatalar import IsKuraliIhlaliException


class YanitlanamayanSoruServisi:
    def __init__(self, yanitlanamayan_soru_deposu):
        self.yanitlanamayan_soru_deposu = yanitlanamayan_soru_deposu

    def kaydet(self, soru_metni):
        from datetime import datetime

        mevcut = self.yanitlanamayan_soru_deposu.metneGoreBul(soru_metni)
        if mevcut is not None and mevcut.durum == KayitDurumu.ACIK:
            mevcut.tekrarArtir()
            self.yanitlanamayan_soru_deposu.kaydet(mevcut)
            return mevcut
        kayit = YanitlanamayanSoru(
            soru_metni=soru_metni, ilk_tarih=datetime.now()
        )
        self.yanitlanamayan_soru_deposu.kaydet(kayit)
        return kayit

    def listele(self, durum):
        return self.yanitlanamayan_soru_deposu.durumaGoreListele(durum)

    def cozulduIsaretle(self, kayit_id):
        kayit = self.yanitlanamayan_soru_deposu.idIleBul(kayit_id)
        if kayit is None:
            raise IsKuraliIhlaliException("IK-29", "Kayıt bulunamadı.")
        kayit.coz()
        self.yanitlanamayan_soru_deposu.kaydet(kayit)
