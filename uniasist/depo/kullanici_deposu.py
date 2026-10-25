from datetime import datetime

from uniasist.entity import Kullanici
from uniasist.enumlar import HesapDurumu, Rol


class KullaniciDeposu:
    def __init__(self, db):
        self.db = db

    def kaydet(self, kullanici):
        if kullanici.kullanici_id is None:
            imleç = self.db.execute(
                "INSERT INTO kullanici (ad_soyad, eposta, sifre_hash, rol, durum, basarisiz_deneme_sayisi, kilit_bitis_zamani, kayit_tarihi) VALUES (?,?,?,?,?,?,?,?)",
                (
                    kullanici.ad_soyad,
                    kullanici.eposta,
                    kullanici.sifre_hash,
                    kullanici.rol.value,
                    kullanici.durum.value,
                    kullanici.basarisiz_deneme_sayisi,
                    kullanici.kilit_bitis_zamani.isoformat() if kullanici.kilit_bitis_zamani else None,
                    kullanici.kayit_tarihi.isoformat(),
                ),
            )
            kullanici.kullanici_id = imleç.lastrowid
        else:
            self.db.execute(
                "UPDATE kullanici SET ad_soyad=?, eposta=?, sifre_hash=?, rol=?, durum=?, basarisiz_deneme_sayisi=?, kilit_bitis_zamani=?, kayit_tarihi=? WHERE kullanici_id=?",
                (
                    kullanici.ad_soyad,
                    kullanici.eposta,
                    kullanici.sifre_hash,
                    kullanici.rol.value,
                    kullanici.durum.value,
                    kullanici.basarisiz_deneme_sayisi,
                    kullanici.kilit_bitis_zamani.isoformat() if kullanici.kilit_bitis_zamani else None,
                    kullanici.kayit_tarihi.isoformat(),
                    kullanici.kullanici_id,
                ),
            )

    def _satirdan(self, satir):
        return Kullanici(
            kullanici_id=satir["kullanici_id"],
            ad_soyad=satir["ad_soyad"],
            eposta=satir["eposta"],
            sifre_hash=satir["sifre_hash"],
            rol=Rol(satir["rol"]),
            durum=HesapDurumu(satir["durum"]),
            basarisiz_deneme_sayisi=satir["basarisiz_deneme_sayisi"],
            kilit_bitis_zamani=datetime.fromisoformat(satir["kilit_bitis_zamani"]) if satir["kilit_bitis_zamani"] else None,
            kayit_tarihi=datetime.fromisoformat(satir["kayit_tarihi"]),
        )

    def idIleBul(self, kullanici_id):
        satir = self.db.execute("SELECT * FROM kullanici WHERE kullanici_id = ?", (kullanici_id,)).fetchone()
        return self._satirdan(satir) if satir else None

    def epostaIleBul(self, eposta):
        satir = self.db.execute("SELECT * FROM kullanici WHERE eposta = ?", (eposta,)).fetchone()
        return self._satirdan(satir) if satir else None

    def epostaVarMi(self, eposta):
        satir = self.db.execute("SELECT 1 FROM kullanici WHERE eposta = ?", (eposta,)).fetchone()
        return satir is not None

    def ara(self, arama):
        arama = f"%{arama.strip().lower()}%"
        satirlar = self.db.execute(
            "SELECT * FROM kullanici WHERE LOWER(ad_soyad) LIKE ? OR LOWER(eposta) LIKE ? ORDER BY ad_soyad",
            (arama, arama),
        ).fetchall()
        return [self._satirdan(s) for s in satirlar]

    def aktifYoneticiSayisi(self):
        satir = self.db.execute(
            "SELECT COUNT(*) AS n FROM kullanici WHERE rol = ? AND durum = ?",
            (Rol.YONETICI.value, HesapDurumu.AKTIF.value),
        ).fetchone()
        return satir["n"]
