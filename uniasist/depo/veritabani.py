import sqlite3
from datetime import datetime
from pathlib import Path

import config
from uniasist.entity import Oturum

_SEMA = """
CREATE TABLE IF NOT EXISTS kullanici (
    kullanici_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_soyad TEXT NOT NULL,
    eposta TEXT NOT NULL UNIQUE,
    sifre_hash TEXT NOT NULL,
    rol TEXT NOT NULL,
    durum TEXT NOT NULL DEFAULT 'AKTIF',
    basarisiz_deneme_sayisi INTEGER NOT NULL DEFAULT 0,
    kilit_bitis_zamani TEXT,
    kayit_tarihi TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS oturum (
    oturum_id TEXT PRIMARY KEY,
    kullanici_id INTEGER NOT NULL,
    olusturma_zamani TEXT NOT NULL,
    son_etkinlik_zamani TEXT NOT NULL,
    aktif INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS sohbet (
    sohbet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_id INTEGER,
    ziyaretci_oturum_id TEXT,
    baslik TEXT NOT NULL,
    olusturma_zamani TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mesaj (
    mesaj_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sohbet_id INTEGER NOT NULL,
    gonderen TEXT NOT NULL,
    metin TEXT NOT NULL,
    zaman TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS kaynak_referansi (
    kaynak_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mesaj_id INTEGER NOT NULL,
    bolum_bilgisi TEXT NOT NULL,
    kaynak_adi TEXT NOT NULL,
    benzerlik_skoru REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS geri_bildirim (
    geri_bildirim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mesaj_id INTEGER NOT NULL,
    kullanici_id INTEGER NOT NULL,
    tur TEXT NOT NULL,
    aciklama TEXT,
    zaman TEXT NOT NULL,
    UNIQUE(mesaj_id, kullanici_id)
);
CREATE TABLE IF NOT EXISTS bilgi_kaynagi (
    kaynak_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tur TEXT NOT NULL,
    baslik TEXT NOT NULL,
    kategori TEXT NOT NULL,
    durum TEXT NOT NULL DEFAULT 'PASIF',
    olusturma_tarihi TEXT NOT NULL,
    guncelleme_tarihi TEXT NOT NULL,
    dosya_adi TEXT,
    dosya_turu TEXT,
    boyut_byte INTEGER,
    dosya_yolu TEXT,
    surum_no INTEGER,
    soru TEXT,
    cevap TEXT
);
CREATE TABLE IF NOT EXISTS icerik_parcasi (
    parca_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kaynak_id INTEGER NOT NULL,
    surum_no INTEGER NOT NULL DEFAULT 1,
    sira INTEGER NOT NULL,
    metin TEXT NOT NULL,
    gomme TEXT NOT NULL,
    gomme_saglayici TEXT NOT NULL,
    kaynak_adi TEXT,
    bolum_bilgisi TEXT,
    kategori TEXT,
    aktif INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS yanitlanamayan_soru (
    kayit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    soru_metni TEXT NOT NULL,
    ilk_tarih TEXT NOT NULL,
    tekrar_sayisi INTEGER NOT NULL DEFAULT 1,
    durum TEXT NOT NULL DEFAULT 'ACIK'
);
CREATE TABLE IF NOT EXISTS soru_kaydi (
    kayit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    zaman TEXT NOT NULL,
    kategori TEXT,
    yanitlandi INTEGER NOT NULL
);
"""


def sema_olustur(conn):
    conn.executescript(_SEMA)


def baglan(yolu=None):
    yolu = yolu or config.VERITABANI_YOLU
    dosya = Path(yolu)
    if dosya.parent and str(dosya.parent) not in ("", "."):
        dosya.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(dosya))
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    sema_olustur(conn)
    return conn


def oturum_kaydet(db, oturum):
    db.execute(
        "INSERT OR REPLACE INTO oturum (oturum_id, kullanici_id, olusturma_zamani, son_etkinlik_zamani, aktif) VALUES (?,?,?,?,?)",
        (
            oturum.oturum_id,
            oturum.kullanici_id,
            oturum.olusturma_zamani.isoformat(),
            oturum.son_etkinlik_zamani.isoformat(),
            1 if oturum.aktif else 0,
        ),
    )


def oturum_bul(db, oturum_id):
    satir = db.execute("SELECT * FROM oturum WHERE oturum_id = ?", (oturum_id,)).fetchone()
    if satir is None:
        return None
    return Oturum(
        oturum_id=satir["oturum_id"],
        kullanici_id=satir["kullanici_id"],
        olusturma_zamani=datetime.fromisoformat(satir["olusturma_zamani"]),
        son_etkinlik_zamani=datetime.fromisoformat(satir["son_etkinlik_zamani"]),
        aktif=bool(satir["aktif"]),
    )


def oturum_sil(db, oturum_id):
    db.execute("DELETE FROM oturum WHERE oturum_id = ?", (oturum_id,))


def oturumlari_sonlandir(db, kullanici_id):
    db.execute("UPDATE oturum SET aktif = 0 WHERE kullanici_id = ?", (kullanici_id,))
