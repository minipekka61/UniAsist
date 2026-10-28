from pathlib import Path

from uniasist.entity import Kullanici
from uniasist.enumlar import Rol
from uniasist.guvenlik import sifre_hashle

_KOK = Path(__file__).resolve().parent.parent / "veri" / "ornek_belgeler"

_HESAPLAR = [
    ("Sistem Yöneticisi", "admin@universite.edu.tr", "Yonetici1234", Rol.YONETICI),
    ("Örnek Öğrenci", "ogrenci@universite.edu.tr", "Ogrenci1234", Rol.OGRENCI),
]

_BELGELER = [
    ("lisans_egitim_ogretim_yonetmeligi.txt", "Lisans Eğitim-Öğretim Yönetmeliği", "Kayıt"),
    ("akademik_takvim.txt", "2026-2027 Akademik Takvim", "Akademik Takvim"),
    ("ders_ekle_birak.txt", "Ders Ekleme-Bırakma Yönergesi", "Ders İşlemleri"),
    ("burs_yonergesi.txt", "Burs Yönergesi", "Burs"),
    ("kyk_yurt_basvuru.txt", "Yurt Başvuru Kılavuzu", "Yurt"),
    ("staj_yonergesi.txt", "Staj Yönergesi", "Staj"),
    ("mezuniyet_kosullari.txt", "Mezuniyet Koşulları", "Mezuniyet"),
    ("cift_anadal.txt", "Çift Anadal Yönergesi", "Çift Anadal"),
    ("yatay_gecis.txt", "Yatay Geçiş Koşulları", "Yatay Geçiş"),
    ("kayit_yenileme.txt", "Kayıt Yenileme Kılavuzu", "Kayıt"),
    ("yaz_okulu.txt", "Yaz Okulu Kuralları", "Ders İşlemleri"),
    ("diploma_islemleri.txt", "Diploma ve Çıkış İşlemleri", "Mezuniyet"),
    ("danismanlik.txt", "Öğrenci Danışmanlık Hizmetleri", "Öğrenci Hizmetleri"),
    ("engelli_destek.txt", "Engelli Öğrenci Destek Birimi", "Öğrenci Hizmetleri"),
]

def kos(paket):
    for ad_soyad, eposta, sifre, rol in _HESAPLAR:
        if not paket.kimlik.kullanici_deposu.epostaVarMi(eposta):
            kullanici = Kullanici(
                ad_soyad=ad_soyad,
                eposta=eposta,
                sifre_hash=sifre_hashle(sifre),
                rol=rol,
            )
            paket.kimlik.kullanici_deposu.kaydet(kullanici)

    if not paket.bilgi_tabani.belgeleriListele():
        for dosya_adi, baslik, kategori in _BELGELER:
            yol = _KOK / dosya_adi
            paket.bilgi_tabani.belgeYukle(
                dosya_adi, str(yol), yol.stat().st_size, baslik, kategori
            )
