from datetime import datetime

from uniasist.entity import SoruKaydi


class SoruKaydiDeposu:
    def __init__(self, db):
        self.db = db

    def kaydet(self, kayit):
        if kayit.kayit_id is None:
            imleç = self.db.execute(
                "INSERT INTO soru_kaydi (zaman, kategori, yanitlandi, kullanici_id) VALUES (?,?,?,?)",
                (kayit.zaman.isoformat(), kayit.kategori, 1 if kayit.yanitlandi else 0, kayit.kullanici_id),
            )
            kayit.kayit_id = imleç.lastrowid
        else:
            self.db.execute(
                "UPDATE soru_kaydi SET zaman=?, kategori=?, yanitlandi=?, kullanici_id=? WHERE kayit_id=?",
                (kayit.zaman.isoformat(), kayit.kategori, 1 if kayit.yanitlandi else 0, kayit.kullanici_id, kayit.kayit_id),
            )

    def _satirdan(self, satir):
        return SoruKaydi(
            kayit_id=satir["kayit_id"],
            zaman=datetime.fromisoformat(satir["zaman"]),
            kategori=satir["kategori"],
            yanitlandi=bool(satir["yanitlandi"]),
            kullanici_id=satir["kullanici_id"],
        )

    def araliktakiKayitlar(self, baslangic, bitis):
        satirlar = self.db.execute(
            "SELECT * FROM soru_kaydi WHERE zaman >= ? AND zaman <= ? ORDER BY zaman",
            (baslangic.isoformat(), bitis.isoformat()),
        ).fetchall()
        return [self._satirdan(s) for s in satirlar]
