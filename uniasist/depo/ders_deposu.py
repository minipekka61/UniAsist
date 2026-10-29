from uniasist.entity import Ders


class DersDeposu:
    def __init__(self, db):
        self.db = db

    def kaydet(self, ders):
        if ders.ders_id is None:
            imleç = self.db.execute(
                "INSERT INTO ders (ad) VALUES (?)", (ders.ad,)
            )
            ders.ders_id = imleç.lastrowid
        else:
            self.db.execute(
                "UPDATE ders SET ad=? WHERE ders_id=?", (ders.ad, ders.ders_id)
            )
        return ders

    def bulVeYaOlustur(self, ad):
        ad = (ad or "").strip()
        if not ad:
            raise ValueError("Ders adı boş olamaz.")
        mevcut = self.adIleBul(ad)
        if mevcut is not None:
            return mevcut
        return self.kaydet(Ders(ad=ad))

    def adIleBul(self, ad):
        ad = (ad or "").strip()
        if not ad:
            return None
        satir = self.db.execute(
            "SELECT * FROM ders WHERE LOWER(ad) = LOWER(?)", (ad,)
        ).fetchone()
        return self._satirdan(satir) if satir else None

    def idIleBul(self, ders_id):
        satir = self.db.execute(
            "SELECT * FROM ders WHERE ders_id = ?", (ders_id,)
        ).fetchone()
        return self._satirdan(satir) if satir else None

    def hepsiniListele(self):
        satirlar = self.db.execute("SELECT * FROM ders ORDER BY ad").fetchall()
        return [self._satirdan(s) for s in satirlar]

    def ara(self, ad):
        ad = f"%{(ad or '').strip().lower()}%"
        satirlar = self.db.execute(
            "SELECT * FROM ders WHERE LOWER(ad) LIKE ? ORDER BY ad", (ad,)
        ).fetchall()
        return [self._satirdan(s) for s in satirlar]

    def takipEt(self, kullanici_id, ders_id):
        self.db.execute(
            "INSERT OR IGNORE INTO kullanici_ders (kullanici_id, ders_id) VALUES (?,?)",
            (kullanici_id, ders_id),
        )

    def takibiBirak(self, kullanici_id, ders_id):
        self.db.execute(
            "DELETE FROM kullanici_ders WHERE kullanici_id = ? AND ders_id = ?",
            (kullanici_id, ders_id),
        )

    def kullanicininDersleri(self, kullanici_id):
        satirlar = self.db.execute(
            "SELECT d.* FROM ders d JOIN kullanici_ders kd ON kd.ders_id = d.ders_id "
            "WHERE kd.kullanici_id = ? ORDER BY d.ad",
            (kullanici_id,),
        ).fetchall()
        return [self._satirdan(s) for s in satirlar]

    def kullanicininDersIdleri(self, kullanici_id):
        satirlar = self.db.execute(
            "SELECT ders_id FROM kullanici_ders WHERE kullanici_id = ?",
            (kullanici_id,),
        ).fetchall()
        return {s["ders_id"] for s in satirlar}

    def takipteMi(self, kullanici_id, ders_id):
        satir = self.db.execute(
            "SELECT 1 FROM kullanici_ders WHERE kullanici_id = ? AND ders_id = ?",
            (kullanici_id, ders_id),
        ).fetchone()
        return satir is not None

    def _satirdan(self, satir):
        return Ders(ders_id=satir["ders_id"], ad=satir["ad"])
