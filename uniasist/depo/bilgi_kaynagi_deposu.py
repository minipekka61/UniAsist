from datetime import datetime

from uniasist.entity import Belge, SSSGirdisi
from uniasist.enumlar import KaynakDurumu


class BilgiKaynagiDeposu:
    def __init__(self, db):
        self.db = db

    def kaydet(self, kaynak):
        if kaynak.kaynak_id is None:
            imleç = self.db.execute(
                "INSERT INTO bilgi_kaynagi (tur, baslik, kategori, durum, olusturma_tarihi, guncelleme_tarihi, dosya_adi, dosya_turu, boyut_byte, dosya_yolu, surum_no, soru, cevap) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                self._degerler(kaynak),
            )
            kaynak.kaynak_id = imleç.lastrowid
        else:
            self.db.execute(
                "UPDATE bilgi_kaynagi SET tur=?, baslik=?, kategori=?, durum=?, olusturma_tarihi=?, guncelleme_tarihi=?, dosya_adi=?, dosya_turu=?, boyut_byte=?, dosya_yolu=?, surum_no=?, soru=?, cevap=? WHERE kaynak_id=?",
                self._degerler(kaynak) + (kaynak.kaynak_id,),
            )

    def _degerler(self, kaynak):
        ortak = (
            kaynak.tur,
            kaynak.baslik,
            kaynak.kategori,
            kaynak.durum.value,
            kaynak.olusturma_tarihi.isoformat(),
            kaynak.guncelleme_tarihi.isoformat(),
        )
        if kaynak.tur == "BELGE":
            return ortak + (
                kaynak.dosya_adi,
                kaynak.dosya_turu,
                kaynak.boyut_byte,
                kaynak.dosya_yolu,
                kaynak.surum_no,
                None,
                None,
            )
        return ortak + (None, None, None, None, None, kaynak.soru, kaynak.cevap)

    def _satirdan(self, satir):
        ortak = dict(
            kaynak_id=satir["kaynak_id"],
            baslik=satir["baslik"],
            kategori=satir["kategori"],
            durum=KaynakDurumu(satir["durum"]),
            olusturma_tarihi=datetime.fromisoformat(satir["olusturma_tarihi"]),
            guncelleme_tarihi=datetime.fromisoformat(satir["guncelleme_tarihi"]),
        )
        if satir["tur"] == "BELGE":
            return Belge(
                dosya_adi=satir["dosya_adi"] or "",
                dosya_turu=satir["dosya_turu"] or "",
                boyut_byte=satir["boyut_byte"] or 0,
                dosya_yolu=satir["dosya_yolu"] or "",
                surum_no=satir["surum_no"] or 1,
                **ortak,
            )
        return SSSGirdisi(
            soru=satir["soru"] or "",
            cevap=satir["cevap"] or "",
            **ortak,
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
