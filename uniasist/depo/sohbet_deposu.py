from datetime import datetime

from uniasist.entity import KaynakReferansi, Mesaj, Sohbet
from uniasist.enumlar import GonderenTuru


class SohbetDeposu:
    def __init__(self, db):
        self.db = db

    def kaydet(self, sohbet):
        if sohbet.sohbet_id is None:
            imleç = self.db.execute(
                "INSERT INTO sohbet (kullanici_id, ziyaretci_oturum_id, baslik, olusturma_zamani) VALUES (?,?,?,?)",
                (
                    sohbet.kullanici_id,
                    sohbet.ziyaretci_oturum_id,
                    sohbet.baslik,
                    sohbet.olusturma_zamani.isoformat(),
                ),
            )
            sohbet.sohbet_id = imleç.lastrowid
        else:
            self.db.execute(
                "UPDATE sohbet SET kullanici_id=?, ziyaretci_oturum_id=?, baslik=?, olusturma_zamani=? WHERE sohbet_id=?",
                (
                    sohbet.kullanici_id,
                    sohbet.ziyaretci_oturum_id,
                    sohbet.baslik,
                    sohbet.olusturma_zamani.isoformat(),
                    sohbet.sohbet_id,
                ),
            )
        for mesaj in sohbet.mesajlar:
            if mesaj.mesaj_id is None:
                imleç = self.db.execute(
                    "INSERT INTO mesaj (sohbet_id, gonderen, metin, zaman) VALUES (?,?,?,?)",
                    (
                        sohbet.sohbet_id,
                        mesaj.gonderen.value,
                        mesaj.metin,
                        mesaj.zaman.isoformat(),
                    ),
                )
                mesaj.mesaj_id = imleç.lastrowid
                mesaj.sohbet_id = sohbet.sohbet_id
                for referans in mesaj.kaynaklar:
                    self.db.execute(
                        "INSERT INTO kaynak_referansi (mesaj_id, bolum_bilgisi, kaynak_adi, benzerlik_skoru, belge_kaynak_id) VALUES (?,?,?,?,?)",
                        (
                            mesaj.mesaj_id,
                            referans.bolum_bilgisi,
                            referans.kaynak_adi,
                            referans.benzerlik_skoru,
                            referans.kaynak_id,
                        ),
                    )

    def _mesaj_satirdan(self, satir):
        mesaj = Mesaj(
            mesaj_id=satir["mesaj_id"],
            sohbet_id=satir["sohbet_id"],
            gonderen=GonderenTuru(satir["gonderen"]),
            metin=satir["metin"],
            zaman=datetime.fromisoformat(satir["zaman"]),
        )
        ref_satirlar = self.db.execute(
            "SELECT * FROM kaynak_referansi WHERE mesaj_id = ? ORDER BY kaynak_id",
            (mesaj.mesaj_id,),
        ).fetchall()
        for r in ref_satirlar:
            mesaj.kaynakEkle(
                KaynakReferansi(
                    kaynak_id=r["belge_kaynak_id"],
                    bolum_bilgisi=r["bolum_bilgisi"],
                    kaynak_adi=r["kaynak_adi"],
                    benzerlik_skoru=r["benzerlik_skoru"],
                )
            )
        return mesaj

    def _sohbet_satirdan(self, satir, mesajlarla):
        sohbet = Sohbet(
            sohbet_id=satir["sohbet_id"],
            kullanici_id=satir["kullanici_id"],
            ziyaretci_oturum_id=satir["ziyaretci_oturum_id"],
            baslik=satir["baslik"],
            olusturma_zamani=datetime.fromisoformat(satir["olusturma_zamani"]),
        )
        if mesajlarla:
            mesaj_satirlar = self.db.execute(
                "SELECT * FROM mesaj WHERE sohbet_id = ? ORDER BY mesaj_id",
                (sohbet.sohbet_id,),
            ).fetchall()
            for m in mesaj_satirlar:
                sohbet.mesajEkle(self._mesaj_satirdan(m))
        return sohbet

    def idIleBul(self, sohbet_id, mesajlarla=True):
        satir = self.db.execute("SELECT * FROM sohbet WHERE sohbet_id = ?", (sohbet_id,)).fetchone()
        return self._sohbet_satirdan(satir, mesajlarla) if satir else None

    def kullaniciSohbetleri(self, kullanici_id):
        satirlar = self.db.execute(
            "SELECT * FROM sohbet WHERE kullanici_id = ? ORDER BY olusturma_zamani DESC, sohbet_id DESC",
            (kullanici_id,),
        ).fetchall()
        return [self._sohbet_satirdan(s, True) for s in satirlar]

    def mesajBul(self, mesaj_id):
        satir = self.db.execute("SELECT * FROM mesaj WHERE mesaj_id = ?", (mesaj_id,)).fetchone()
        return self._mesaj_satirdan(satir) if satir else None

    def sil(self, sohbet_id):
        self.db.execute(
            "DELETE FROM kaynak_referansi WHERE mesaj_id IN (SELECT mesaj_id FROM mesaj WHERE sohbet_id = ?)",
            (sohbet_id,),
        )
        self.db.execute(
            "DELETE FROM geri_bildirim WHERE mesaj_id IN (SELECT mesaj_id FROM mesaj WHERE sohbet_id = ?)",
            (sohbet_id,),
        )
        self.db.execute("DELETE FROM mesaj WHERE sohbet_id = ?", (sohbet_id,))
        self.db.execute("DELETE FROM sohbet WHERE sohbet_id = ?", (sohbet_id,))

    def kullaniciSohbetleriniSil(self, kullanici_id):
        satirlar = self.db.execute(
            "SELECT sohbet_id FROM sohbet WHERE kullanici_id = ?", (kullanici_id,)
        ).fetchall()
        for satir in satirlar:
            self.sil(satir["sohbet_id"])
