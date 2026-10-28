from datetime import datetime

from uniasist.entity import Belge
from uniasist.enumlar import KaynakDurumu


class BilgiKaynagiDeposu:
    def __init__(self, db):
        self.db = db

    def kaydet(self, kaynak):
        if kaynak.kaynak_id is None:
            imleç = self.db.execute(
                "INSERT INTO bilgi_kaynagi (tur, baslik, kategori, durum, olusturma_tarihi, guncelleme_tarihi, dosya_adi, dosya_turu, boyut_byte, dosya_yolu, surum_no) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                self._degerler(kaynak),
            )
            kaynak.kaynak_id = imleç.lastrowid
        else:
            self.db.execute(
                "UPDATE bilgi_kaynagi SET tur=?, baslik=?, kategori=?, durum=?, olusturma_tarihi=?, guncelleme_tarihi=?, dosya_adi=?, dosya_turu=?, boyut_byte=?, dosya_yolu=?, surum_no=? WHERE kaynak_id=?",
                self._degerler(kaynak) + (kaynak.kaynak_id,),
            )

    def _degerler(self, kaynak):
        return (
            kaynak.tur,
            kaynak.baslik,
            kaynak.kategori,
            kaynak.durum.value,
            kaynak.olusturma_tarihi.isoformat(),
            kaynak.guncelleme_tarihi.isoformat(),
            kaynak.dosya_adi,
            kaynak.dosya_turu,
            kaynak.boyut_byte,
            kaynak.dosya_yolu,
            kaynak.surum_no,
        )

    def _satirdan(self, satir):
        return Belge(
            kaynak_id=satir["kaynak_id"],
            baslik=satir["baslik"],
            kategori=satir["kategori"],
            durum=KaynakDurumu(satir["durum"]),
            olusturma_tarihi=datetime.fromisoformat(satir["olusturma_tarihi"]),
            guncelleme_tarihi=datetime.fromisoformat(satir["guncelleme_tarihi"]),
            dosya_adi=satir["dosya_adi"] or "",
            dosya_turu=satir["dosya_turu"] or "",
            boyut_byte=satir["boyut_byte"] or 0,
            dosya_yolu=satir["dosya_yolu"] or "",
            surum_no=satir["surum_no"] or 1,
        )

    def idIleBul(self, kaynak_id):
        satir = self.db.execute("SELECT * FROM bilgi_kaynagi WHERE kaynak_id = ?", (kaynak_id,)).fetchone()
        return self._satirdan(satir) if satir else None

    def sil(self, kaynak_id):
        self.db.execute("DELETE FROM bilgi_kaynagi WHERE kaynak_id = ?", (kaynak_id,))

    def aktifKaynaklar(self):
        satirlar = self.db.execute(
            "SELECT * FROM bilgi_kaynagi WHERE durum = ? ORDER BY baslik",
            (KaynakDurumu.AKTIF.value,),
        ).fetchall()
        return [self._satirdan(s) for s in satirlar]

    def belgeler(self):
        satirlar = self.db.execute(
            "SELECT * FROM bilgi_kaynagi WHERE tur = 'BELGE' ORDER BY baslik"
        ).fetchall()
        return [self._satirdan(s) for s in satirlar]
