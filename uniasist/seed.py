from pathlib import Path

from uniasist.entity import Kullanici
from uniasist.enumlar import Rol
from uniasist.guvenlik import sifre_hashle

_KOK = Path(__file__).resolve().parent.parent / "veri" / "ornek_belgeler"

_HESAPLAR = [
    ("Sistem Yöneticisi", "admin@universite.edu.tr", "Yonetici1234", Rol.YONETICI),
    ("Öğrenci İşleri Personeli", "personel@universite.edu.tr", "Personel1234", Rol.PERSONEL),
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

_SSS = [
    (
        "Kayıt yenileme ne zaman ve nasıl yapılır?",
        "Kayıt yenileme her yarıyıl başında, akademik takvimde ilan edilen iki haftalık süre içinde, "
        "öğrenci bilgi sistemi üzerinden ders seçimi ve katkı payı ödemesi yapılarak yapılır.",
        "Kayıt",
    ),
    (
        "Burs başvurusu ne zaman yapılır?",
        "Burs başvuruları her yıl eylül ayının ilk haftasında Öğrenci İşleri Daire Başkanlığına yapılır.",
        "Burs",
    ),
    (
        "Başarı bursu için kaç ortalama gerekir?",
        "Başarı bursu için genel not ortalamasının en az 3,00 olması gerekir; burs eğitim ücretinden "
        "%50 indirim ve aylık 1.000 TL kitap desteği sağlar.",
        "Burs",
    ),
    (
        "Yurt başvurusu nereden ve ne zaman yapılır?",
        "Yurt başvuruları her yıl temmuz ayında Kredi ve Yurtlar Kurumu (KYK) sistemi üzerinden çevrim "
        "içi yapılır.",
        "Yurt",
    ),
    (
        "Staj süresi en az kaç gündür?",
        "Staj başvurusu için en az 60 gün süreyle kesintisiz çalışma gerekir.",
        "Staj",
    ),
    (
        "Mezuniyet için kaç AKTS tamamlanmalı?",
        "Mezuniyet için toplam 240 AKTS kredisi tamamlanmalı ve genel not ortalaması en az 2,00 olmalıdır.",
        "Mezuniyet",
    ),
    (
        "Mezuniyet töreni ne zaman yapılır?",
        "Mezuniyet töreni her yıl haziran ayının son haftasında kampüs konferans salonunda düzenlenir.",
        "Mezuniyet",
    ),
    (
        "Ders ekleme-bırakma süresi ne kadar?",
        "Ders ekleme ve bırakma işlemleri yarıyılın ilk iki haftası içinde yapılır.",
        "Ders İşlemleri",
    ),
    (
        "Yaz okulunda en fazla kaç ders alınabilir?",
        "Yaz okulunda en fazla iki ders alınabilir; genel not ortalaması 3,00 ve üzerinde olan öğrenciler "
        "için bu sınır danışman onayı ile üçe çıkar.",
        "Ders İşlemleri",
    ),
    (
        "Tek ders sınavı nedir?",
        "Mezun olması için yalnızca bir dersten başarısız olan öğrenciye ilgili fakülte yönetim kurulu "
        "kararı ile tek ders sınavı hakkı verilir ve bu sınavda en yüksek CC notu verilir.",
        "Ders İşlemleri",
    ),
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

    mevcut_sss = paket.db.execute(
        "SELECT COUNT(*) AS n FROM bilgi_kaynagi WHERE tur='SSS'"
    ).fetchone()["n"]
    if mevcut_sss == 0:
        for soru, cevap, kategori in _SSS:
            paket.bilgi_tabani.sssEkle(soru, cevap, kategori)
