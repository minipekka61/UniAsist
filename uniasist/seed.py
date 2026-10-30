from pathlib import Path

from uniasist.entity import Kullanici
from uniasist.enumlar import Gorunurluk, Plan, Rol
from uniasist.guvenlik import sifre_hashle

_KOK = Path(__file__).resolve().parent.parent / "veri" / "ornek_belgeler"

# (eposta, sifre, ad_soyad, rol, bolum, plan)
_HESAPLAR = [
    ("admin@universite.edu.tr", "Yonetici1234", "Sistem Yöneticisi", Rol.YONETICI, "", None),
    ("bilgisayar@universite.edu.tr", "Ogrenci1234", "Bilgisayar Öğrencisi", Rol.OGRENCI, "Bilgisayar Mühendisliği", Plan.PRO),
    ("elektrik@universite.edu.tr", "Ogrenci1234", "Elektrik Öğrencisi", Rol.OGRENCI, "Elektrik-Elektronik Mühendisliği", Plan.PRO),
]

# (dosya, başlık, kategori, görünürlük, ders)
_BILGISAYAR_BELGELERI = [
    ("lisans_egitim_ogretim_yonetmeligi.txt", "Lisans Eğitim-Öğretim Yönetmeliği", "Kayıt", Gorunurluk.OZEL, ""),
    ("akademik_takvim.txt", "2026-2027 Akademik Takvim", "Akademik Takvim", Gorunurluk.OZEL, ""),
    ("ders_ekle_birak.txt", "Ders Ekleme-Bırakma Yönergesi", "Ders İşlemleri", Gorunurluk.OZEL, ""),
    ("burs_yonergesi.txt", "Burs Yönergesi", "Burs", Gorunurluk.PAYLASILAN, "Burs"),
    ("kyk_yurt_basvuru.txt", "Yurt Başvuru Kılavuzu", "Yurt", Gorunurluk.OZEL, ""),
    ("staj_yonergesi.txt", "Staj Yönergesi", "Staj", Gorunurluk.PAYLASILAN, "Staj"),
    ("mezuniyet_kosullari.txt", "Mezuniyet Koşulları", "Mezuniyet", Gorunurluk.OZEL, ""),
    ("cift_anadal.txt", "Çift Anadal Yönergesi", "Çift Anadal", Gorunurluk.OZEL, ""),
    ("yatay_gecis.txt", "Yatay Geçiş Koşulları", "Yatay Geçiş", Gorunurluk.OZEL, ""),
    ("kayit_yenileme.txt", "Kayıt Yenileme Kılavuzu", "Kayıt", Gorunurluk.OZEL, ""),
    ("yaz_okulu.txt", "Yaz Okulu Kuralları", "Ders İşlemleri", Gorunurluk.OZEL, ""),
    ("diploma_islemleri.txt", "Diploma ve Çıkış İşlemleri", "Mezuniyet", Gorunurluk.OZEL, ""),
    ("danismanlik.txt", "Öğrenci Danışmanlık Hizmetleri", "Öğrenci Hizmetleri", Gorunurluk.OZEL, ""),
    ("engelli_destek.txt", "Engelli Öğrenci Destek Birimi", "Öğrenci Hizmetleri", Gorunurluk.OZEL, ""),
]

_ELEKTRIK_BELGELERI = [
    ("yaz_okulu.txt", "Yaz Okulu Kuralları (Elektrik)", "Ders İşlemleri", Gorunurluk.OZEL, ""),
    ("kyk_yurt_basvuru.txt", "Yurt Başvuru Kılavuzu (Elektrik)", "Yurt", Gorunurluk.PAYLASILAN, "Yurt"),
]


def _belgeleri_yukle(paket, sahip, belgeler):
    for dosya_adi, baslik, kategori, gorunurluk, ders in belgeler:
        yol = _KOK / dosya_adi
        if not any(
            b.dosya_yolu == str(yol) and b.sahip_id == sahip.kullanici_id
            for b in paket.bilgi_tabani.belgeleriListele(sahip.kullanici_id)
        ):
            paket.bilgi_tabani.belgeYukle(
                dosya_adi, str(yol), yol.stat().st_size, baslik, kategori,
                sahip=sahip, gorunurluk=gorunurluk, ders_adi=ders,
            )


def kos(paket):
    kullanicilar = {}
    for eposta, sifre, ad_soyad, rol, bolum, plan in _HESAPLAR:
        if not paket.kimlik.kullanici_deposu.epostaVarMi(eposta):
            kullanici = Kullanici(
                ad_soyad=ad_soyad,
                eposta=eposta,
                sifre_hash=sifre_hashle(sifre),
                rol=rol,
                universite="Üniversite",
                bolum=bolum,
                eposta_dogrulandi=True,
                plan=plan,
            )
            paket.kimlik.kullanici_deposu.kaydet(kullanici)
        kullanicilar[eposta] = paket.kimlik.kullanici_deposu.epostaIleBul(eposta)

    _belgeleri_yukle(
        paket, kullanicilar["bilgisayar@universite.edu.tr"], _BILGISAYAR_BELGELERI
    )
    _belgeleri_yukle(
        paket, kullanicilar["elektrik@universite.edu.tr"], _ELEKTRIK_BELGELERI
    )
