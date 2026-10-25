from datetime import datetime

from uniasist.entity import YanitlanamayanSoru
from uniasist.enumlar import KayitDurumu


class YanitlanamayanSoruDeposu:
    def __init__(self, db):
        self.db = db

    def kaydet(self, kayit):
        if kayit.kayit_id is None:
            imleç = self.db.execute(
                "INSERT INTO yanitlanamayan_soru (soru_metni, ilk_tarih, tekrar_sayisi, durum) VALUES (?,?,?,?)",
                (
                    kayit.soru_metni,
                    kayit.ilk_tarih.isoformat(),
                    kayit.tekrar_sayisi,
                    kayit.durum.value,
                ),
            )
            kayit.kayit_id = imleç.lastrowid
        else:
            self.db.execute(
                "UPDATE yanitlanamayan_soru SET soru_metni=?, ilk_tarih=?, tekrar_sayisi=?, durum=? WHERE kayit_id=?",
                (
                    kayit.soru_metni,
                    kayit.ilk_tarih.isoformat(),
                    kayit.tekrar_sayisi,
                    kayit.durum.value,
                    kayit.kayit_id,
                ),
            )

    def _satirdan(self, satir):
        return YanitlanamayanSoru(
            kayit_id=satir["kayit_id"],
            soru_metni=satir["soru_metni"],
            ilk_tarih=datetime.fromisoformat(satir["ilk_tarih"]),
            tekrar_sayisi=satir["tekrar_sayisi"],
            durum=KayitDurumu(satir["durum"]),
        )

    def idIleBul(self, kayit_id):
        satir = self.db.execute("SELECT * FROM yanitlanamayan_soru WHERE kayit_id = ?", (kayit_id,)).fetchone()
        return self._satirdan(satir) if satir else None

    def metneGoreBul(self, soru_metni):
        satir = self.db.execute(
            "SELECT * FROM yanitlanamayan_soru WHERE soru_metni = ? ORDER BY kayit_id DESC",
            (soru_metni,),
        ).fetchone()
        return self._satirdan(satir) if satir else None

    def durumaGoreListele(self, durum):
        satirlar = self.db.execute(
            "SELECT * FROM yanitlanamayan_soru WHERE durum = ? ORDER BY tekrar_sayisi DESC, ilk_tarih DESC",
            (durum.value,),
        ).fetchall()
        return [self._satirdan(s) for s in satirlar]
