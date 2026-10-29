import json

from uniasist.dto import AramaSonucu
from uniasist.entity import IcerikParcasi
from uniasist.enumlar import Gorunurluk


class AramaDizini:
    def __init__(self, db):
        self.db = db
        self.parcalar = []
        self._yukle()

    def _yukle(self):
        self.parcalar = []
        satirlar = self.db.execute("SELECT * FROM icerik_parcasi ORDER BY parca_id").fetchall()
        for satir in satirlar:
            self.parcalar.append(
                IcerikParcasi(
                    parca_id=satir["parca_id"],
                    kaynak_id=satir["kaynak_id"],
                    surum_no=satir["surum_no"],
                    sira=satir["sira"],
                    metin=satir["metin"],
                    gomme=json.loads(satir["gomme"]),
                    gomme_saglayici=satir["gomme_saglayici"],
                    kaynak_adi=satir["kaynak_adi"] or "",
                    bolum_bilgisi=satir["bolum_bilgisi"],
                    kategori=satir["kategori"] or "",
                    aktif=bool(satir["aktif"]),
                    sahip_id=satir["sahip_id"],
                    gorunurluk=Gorunurluk(satir["gorunurluk"] or "OZEL"),
                    universite_id=satir["universite_id"],
                    bolum=satir["bolum"] or "",
                    ders_id=satir["ders_id"],
                )
            )

    def parcaEkle(self, parca):
        imleç = self.db.execute(
            "INSERT INTO icerik_parcasi (kaynak_id, surum_no, sira, metin, gomme, gomme_saglayici, kaynak_adi, bolum_bilgisi, kategori, aktif, sahip_id, gorunurluk, universite_id, bolum, ders_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                parca.kaynak_id,
                parca.surum_no,
                parca.sira,
                parca.metin,
                json.dumps(parca.gomme or []),
                parca.gomme_saglayici,
                parca.kaynak_adi,
                parca._bolum_bilgisi,
                parca.kategori,
                1 if parca.aktif else 0,
                parca.sahip_id,
                parca.gorunurluk.value,
                parca.universite_id,
                parca.bolum,
                parca.ders_id,
            ),
        )
        parca.parca_id = imleç.lastrowid
        self.parcalar.append(parca)

    def dersGuncelle(self, kaynak_id, ders_id):
        self.db.execute(
            "UPDATE icerik_parcasi SET ders_id = ? WHERE kaynak_id = ?",
            (ders_id, kaynak_id),
        )
        for parca in self.parcalar:
            if parca.kaynak_id == kaynak_id:
                parca.ders_id = ders_id

    def gorunurlukGuncelle(self, kaynak_id, gorunurluk):
        self.db.execute(
            "UPDATE icerik_parcasi SET gorunurluk = ? WHERE kaynak_id = ?",
            (gorunurluk.value, kaynak_id),
        )
        for parca in self.parcalar:
            if parca.kaynak_id == kaynak_id:
                parca.gorunurluk = gorunurluk

    def kaynagaGoreSil(self, kaynak_id):
        self.db.execute("DELETE FROM icerik_parcasi WHERE kaynak_id = ?", (kaynak_id,))
        self.parcalar = [p for p in self.parcalar if p.kaynak_id != kaynak_id]

    def surumeGoreSil(self, kaynak_id, surum_no):
        self.db.execute(
            "DELETE FROM icerik_parcasi WHERE kaynak_id = ? AND surum_no = ?",
            (kaynak_id, surum_no),
        )
        self.parcalar = [
            p for p in self.parcalar
            if not (p.kaynak_id == kaynak_id and p.surum_no == surum_no)
        ]

    def enYakinParcalar(self, sorgu_gommesi, adet, kapsam=None):
        sonuclar = []
        for parca in self.parcalar:
            if not parca.aktif:
                continue
            if kapsam is not None and not kapsam.parcaErisilebilirMi(parca):
                continue
            sonuclar.append(AramaSonucu(parca=parca, skor=parca.benzerlikHesapla(sorgu_gommesi)))
        sonuclar.sort(key=lambda s: s.skor, reverse=True)
        return sonuclar[:adet]

    def saglayiciUyumlu(self, etiket):
        return all(p.gomme_saglayici == etiket for p in self.parcalar)

    def yenidenGomme(self, yapay_zeka_servisi):
        for parca in self.parcalar:
            parca.gomme = yapay_zeka_servisi.gommeUret(parca.metin)
            parca.gomme_saglayici = yapay_zeka_servisi.saglayici_etiketi
            self.db.execute(
                "UPDATE icerik_parcasi SET gomme = ?, gomme_saglayici = ? WHERE parca_id = ?",
                (json.dumps(parca.gomme), parca.gomme_saglayici, parca.parca_id),
            )
