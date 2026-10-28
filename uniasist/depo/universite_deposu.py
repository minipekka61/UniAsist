from uniasist.entity import Universite


class UniversiteDeposu:
    def __init__(self, db):
        self.db = db

    def kaydet(self, universite):
        if universite.universite_id is None:
            imleç = self.db.execute(
                "INSERT INTO universite (ad, eposta_alan_adi) VALUES (?,?)",
                (universite.ad, universite.eposta_alan_adi),
            )
            universite.universite_id = imleç.lastrowid
        else:
            self.db.execute(
                "UPDATE universite SET ad=?, eposta_alan_adi=? WHERE universite_id=?",
                (universite.ad, universite.eposta_alan_adi, universite.universite_id),
            )

    def _satirdan(self, satir):
        return Universite(
            ad=satir["ad"],
            eposta_alan_adi=satir["eposta_alan_adi"],
            universite_id=satir["universite_id"],
        )

    def hepsiniListele(self):
        satirlar = self.db.execute(
            "SELECT * FROM universite ORDER BY ad"
        ).fetchall()
        return [self._satirdan(s) for s in satirlar]

    def idIleBul(self, universite_id):
        if universite_id is None:
            return None
        satir = self.db.execute(
            "SELECT * FROM universite WHERE universite_id = ?", (universite_id,)
        ).fetchone()
        return self._satirdan(satir) if satir else None

    def alanAdindanBul(self, eposta):
        if not isinstance(eposta, str) or "@" not in eposta:
            return None
        alan_adi = eposta.strip().lower().rsplit("@", 1)[1]
        if not alan_adi or "." not in alan_adi:
            return None
        for universite in self.hepsiniListele():
            kayitli = universite.eposta_alan_adi.lower()
            if alan_adi == kayitli or alan_adi.endswith("." + kayitli):
                return universite
        return None

    def bolumleriListele(self):
        satirlar = self.db.execute("SELECT ad FROM bolum ORDER BY ad").fetchall()
        return [s["ad"] for s in satirlar]

    def bolumEkle(self, ad):
        mevcut = self.db.execute("SELECT ad FROM bolum WHERE ad = ?", (ad,)).fetchone()
        if mevcut is None:
            self.db.execute("INSERT INTO bolum (ad) VALUES (?)", (ad,))
