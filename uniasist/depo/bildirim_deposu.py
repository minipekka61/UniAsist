from datetime import datetime

from uniasist.entity import Bildirim
from uniasist.enumlar import KayitDurumu


class BildirimDeposu:
    def __init__(self, db):
        self.db = db

    def kaydet(self, bildirim):
        if bildirim.bildirim_id is None:
            imleç = self.db.execute(
                "INSERT INTO bildirim (belge_id, bildiren_id, neden, durum, tarih) VALUES (?,?,?,?,?)",
                (
                    bildirim.belge_id,
                    bildirim.bildiren_id,
                    bildirim.neden,
                    bildirim.durum.value,
                    bildirim.tarih.isoformat(),
                ),
            )
            bildirim.bildirim_id = imleç.lastrowid
        else:
            self.db.execute(
                "UPDATE bildirim SET belge_id=?, bildiren_id=?, neden=?, durum=?, tarih=? WHERE bildirim_id=?",
                (
                    bildirim.belge_id,
                    bildirim.bildiren_id,
                    bildirim.neden,
                    bildirim.durum.value,
                    bildirim.tarih.isoformat(),
                    bildirim.bildirim_id,
                ),
            )

    def _satirdan(self, satir):
        return Bildirim(
            bildirim_id=satir["bildirim_id"],
            belge_id=satir["belge_id"],
            bildiren_id=satir["bildiren_id"],
            neden=satir["neden"] or "",
            durum=KayitDurumu(satir["durum"]),
            tarih=datetime.fromisoformat(satir["tarih"]),
        )

    def idIleBul(self, bildirim_id):
        satir = self.db.execute(
            "SELECT * FROM bildirim WHERE bildirim_id = ?", (bildirim_id,)
        ).fetchone()
        return self._satirdan(satir) if satir else None

    def aciklariListele(self):
        satirlar = self.db.execute(
            "SELECT * FROM bildirim WHERE durum = ? ORDER BY tarih",
            (KayitDurumu.ACIK.value,),
        ).fetchall()
        return [self._satirdan(s) for s in satirlar]

    def degerlendirildiIsaretle(self, bildirim_id):
        self.db.execute(
            "UPDATE bildirim SET durum = ? WHERE bildirim_id = ?",
            (KayitDurumu.DEGERLENDIRILDI.value, bildirim_id),
        )

    def belgeVeKisiyeGoreBul(self, belge_id, bildiren_id):
        satir = self.db.execute(
            "SELECT * FROM bildirim WHERE belge_id = ? AND bildiren_id = ?",
            (belge_id, bildiren_id),
        ).fetchone()
        return self._satirdan(satir) if satir else None
