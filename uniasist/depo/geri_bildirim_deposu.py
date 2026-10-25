from datetime import datetime

from uniasist.entity import GeriBildirim
from uniasist.enumlar import GeriBildirimTuru


class GeriBildirimDeposu:
    def __init__(self, db):
        self.db = db

    def kaydet(self, geri_bildirim):
        self.db.execute(
            "INSERT INTO geri_bildirim (mesaj_id, kullanici_id, tur, aciklama, zaman) VALUES (?,?,?,?,?) "
            "ON CONFLICT(mesaj_id, kullanici_id) DO UPDATE SET tur=excluded.tur, aciklama=excluded.aciklama, zaman=excluded.zaman",
            (
                geri_bildirim.mesaj_id,
                geri_bildirim.kullanici_id,
                geri_bildirim.tur.value,
                geri_bildirim.aciklama,
                geri_bildirim.zaman.isoformat(),
            ),
        )

    def _satirdan(self, satir):
        return GeriBildirim(
            geri_bildirim_id=satir["geri_bildirim_id"],
            mesaj_id=satir["mesaj_id"],
            kullanici_id=satir["kullanici_id"],
            tur=GeriBildirimTuru(satir["tur"]),
            aciklama=satir["aciklama"],
            zaman=datetime.fromisoformat(satir["zaman"]),
        )

    def mesajIcininBul(self, mesaj_id, kullanici_id):
        satir = self.db.execute(
            "SELECT * FROM geri_bildirim WHERE mesaj_id = ? AND kullanici_id = ?",
            (mesaj_id, kullanici_id),
        ).fetchone()
        return self._satirdan(satir) if satir else None

    def yararsizlar(self):
        satirlar = self.db.execute(
            "SELECT * FROM geri_bildirim WHERE tur = ? ORDER BY zaman DESC",
            (GeriBildirimTuru.YARARSIZ.value,),
        ).fetchall()
        return [self._satirdan(s) for s in satirlar]

    def araliktakiOlumluOrani(self, baslangic, bitis):
        satir = self.db.execute(
            "SELECT SUM(CASE WHEN tur = ? THEN 1 ELSE 0 END) AS olumlu, COUNT(*) AS toplam "
            "FROM geri_bildirim WHERE zaman >= ? AND zaman <= ?",
            (GeriBildirimTuru.YARARLI.value, baslangic.isoformat(), bitis.isoformat()),
        ).fetchone()
        toplam = satir["toplam"] or 0
        if toplam == 0:
            return 0.0
        return (satir["olumlu"] or 0) / toplam
