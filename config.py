import os

API_ANAHTARI = os.environ.get("UNIASIST_API_KEY", "")
API_BASE = os.environ.get("UNIASIST_API_BASE", "https://api.openai.com/v1")
MODEL = os.environ.get("UNIASIST_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.environ.get("UNIASIST_EMBEDDING_MODEL", "text-embedding-3-small")
VERITABANI_YOLU = os.environ.get("UNIASIST_DB", "data/uniasist.db")
SECRET_KEY = os.environ.get("UNIASIST_SECRET_KEY", "uniasist-gelistirme-anahtari")

DOGRULAMA_SURESI_SAAT = 24
AKADEMIK_ALAN_ADLARI = [
    s.strip().lower()
    for s in os.environ.get(
        "UNIASIST_AKADEMIK_ALANLAR", ".edu.tr,.edu,.ac.uk,.edu.au"
    ).split(",")
    if s.strip()
]
TEMEL_URL = os.environ.get("UNIASIST_TEMEL_URL", "http://127.0.0.1:5000")
MAILGONDER = os.environ.get("UNIASIST_MAILGONDER", "0") == "1"
SMTP_SUNUCU = os.environ.get("UNIASIST_SMTP_SUNUCU", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("UNIASIST_SMTP_PORT", "587"))
SMTP_KULLANICI = os.environ.get("UNIASIST_SMTP_KULLANICI", "")
SMTP_SIFRE = os.environ.get("UNIASIST_SMTP_SIFRE", "")
SMTP_GONDEREN = os.environ.get("UNIASIST_SMTP_GONDEREN", "uniasist@example.com")
BENZERLIK_ESIGI = 0.60
YEREL_ESIK = 0.20
EN_FAZLA_PARCA = 5
AZAMI_SORU_UZUNLUGU = 500
BAGLAM_MESAJ_SAYISI = 10
AZAMI_HATALI_DENEME = 5
KILIT_SURESI_DK = 15
OTURUM_SURESI_DK = 30
AZAMI_BELGE_BOYUTU = 10 * 1024 * 1024
YENIDEN_DENEME = 3
LLM_ZAMAN_ASIMI_SANIYE = 30
PARCA_BOYUTU = 900
PARCA_ORTUSME = 150
DOSYA_KLASORU = "veri/dosyalar"

HATA_EPOSTA_SIFRE = "E-posta veya şifre hatalı."
HATA_KILIT = "Hesabınız geçici olarak kilitlendi. Lütfen 15 dakika sonra tekrar deneyin."
HATA_DEVRE_DISI = "Hesabınız devre dışı bırakılmıştır."
BILGI_YOK_METNI = (
    "Bu konuda kesin bilgiye sahip değilim. Detaylı bilgi için Öğrenci İşleri "
    "Daire Başkanlığı'na (ogrenciisleri@universite.edu.tr, 0212 555 00 00) "
    "başvurabilirsiniz."
)
RESMI_UYARI = "Bu yanıt bilgilendirme amaçlıdır; kesin bilgi için resmî belgeyi kontrol ediniz."
KISISEL_VERI_UYARISI = (
    "Lütfen sorularınızda öğrenci no, T.C. kimlik no gibi kişisel veri paylaşmayın."
)
SERVIS_HATA_METNI = "Yapay zekâ servisine şu anda ulaşılamıyor. Lütfen soruyu tekrar gönderin."
KAPSAM_METNI = (
    "UniAsist yalnızca üniversitenin akademik ve idari konularındaki soruları yanıtlar "
    "(kayıt, dersler, burs, yurt, staj, mezuniyet vb.). Lütfen sorunuzu bu kapsamda "
    "yeniden yazın."
)
BIRIM_ILETISIM = "Öğrenci İşleri Daire Başkanlığı — ogrenciisleri@universite.edu.tr — 0212 555 00 00"
