# UniAsist

Üniversite öğrencileri için ders çalışma asistanı SaaS'ı: öğrenciler kendi
belgeleriyle (PDF/TXT) AI üzerinden ders çalışır, istediklerinde belgelerini
aynı üniversite ve aynı bölümden arkadaşlarıyla paylaşır. Bölümün ortak belge
havuzu büyüdükçe yanıtlar zenginleşir (RAG). Sohbet geçmişi, geri bildirim,
bildiri/moderasyon, kullanıcı yönetimi ve kullanım raporlama içerir.

## Kayıt akışı

1. Üniversite e-postanızla kayıt olun (üniversite, e-posta alan adından otomatik
   belirlenir; desteklenen alan adları `uniasist/veri/universiteler.py` içindedir).
2. Bölümünüzü listeden seçin.
3. E-postanıza gönderilen doğrulama bağlantısıyla hesabınızı aktifleştirin
   (geliştirme modunda bağlantı konsol kaydına yazılır — `uniasist.eposta` log'u).
   Doğrulama yapılmadan belge **paylaşılamaz**; kişisel kullanım açıktır.

Belgeler varsayılan olarak özeldir; yalnız siz (ve AI asistanınız) erişir.
"Paylaş" ile belgeniz aynı üniversite + aynı bölümden öğrencilere açılır.

## Kurulum

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Gereksinimler: Python 3.13, Flask, pypdf, requests, pytest.

## Çalıştırma

```
.venv\Scripts\python app.py
```

Uygulama http://127.0.0.1:5000 adresinde açılır. Boş veritabanında ilk açılışta
örnek veri otomatik yüklenir: 26 üniversite, 30 bölüm, 3 hesap ve sahipli
örnek belgeler. Kayıtsız kullanıcılar giriş sayfasına yönlendirilir.

**Önemli:** Veritabanı şeması SaaS sürümüyle değişti. Önceki (tek üniversiteli)
sürümün `data/uniasist.db` dosyası varsa silin — uygulama ilk açılışta yeni
şemayla ve örnek veriyle taze veritabanı kurar.

## Demo hesapları

| Rol | E-posta | Şifre | Bölüm |
| --- | --- | --- | --- |
| Yönetici | admin@universite.edu.tr | Yonetici1234 | — |
| Öğrenci | bilgisayar@universite.edu.tr | Ogrenci1234 | Bilgisayar Mühendisliği |
| Öğrenci | elektrik@universite.edu.tr | Ogrenci1234 | Elektrik-Elektronik Mühendisliği |

Bilgisayar öğrencisi 14 örnek belgenin sahibidir (2'si bölüme paylaşılmış);
elektrik öğrencisinin 2 belgesi vardır (1'i paylaşılmış). Farklı bölümler
birbirinin paylaşılan belgelerini göremez — kapsam izolasyonu testlidir.

## Yapay zekâ sağlayıcısı

API anahtarı tanımlı değilse uygulama yerel arama modunda çalışır (TF-IDF
benzeri gömme vektörleriyle belge arama; yanıtlar belge metninden derlenir).
OpenAI uyumlu bir REST API kullanmak için:

```
set UNIASIST_API_KEY=...                (zorunlu)
set UNIASIST_API_BASE=https://api.openai.com/v1   (isteğe bağlı)
set UNIASIST_MODEL=gpt-4o-mini          (isteğe bağlı)
set UNIASIST_EMBEDDING_MODEL=text-embedding-3-small (isteğe bağlı)
set UNIASIST_DB=data/uniasist.db        (isteğe bağlı)
set UNIASIST_SECRET_KEY=...             (üretime alırken zorunlu önerilir)
```

Sağlayıcı değiştiğinde indeksli parçalar açılışta otomatik olarak yeniden gömülür.

## E-posta gönderimi (SMTP)

Geliştirmede doğrulama e-postaları konsola/log'a yazılır. Gerçek SMTP gönderimi için:

```
set UNIASIST_MAILGONDER=1
set UNIASIST_SMTP_SUNUCU=smtp.example.com
set UNIASIST_SMTP_PORT=587
set UNIASIST_SMTP_KULLANICI=...
set UNIASIST_SMTP_SIFRE=...
set UNIASIST_SMTP_GONDEREN=uniasist@example.com
```

## Test

```
.venv\Scripts\python -m pytest -q
```

## Değerlendirme (NFR-05)

```
.venv\Scripts\python degerlendir.py
```

Betik, 50 örnek soruyu doğrulanmış demo öğrencisinin kapsamıyla (kendi
belgeleri + bölümün paylaşılanları) gerçek servis üzerinden işler ve doğru
yanıt oranını raporlar (hedef %80). API anahtarı tanımlıysa hazır LLM,
tanımlı değilse yerel arama kullanılır.

## Katmanlar

- `uniasist/entity.py` — varlık sınıfları (Kullanici, Sohbet, Belge, Bildirim, ...)
- `uniasist/depo/` — SQLite depoları
- `uniasist/servis/` — iş kuralları (kimlik doğrulama, e-posta, RAG, bilgi
  tabanı, moderasyon, rapor, ...)
- `uniasist/yapayzeka/` — LLM arayüzü, hazır servis ve yerel arama gerçeklemeleri
- `uniasist/ekran/` — Flask blueprint'leri (öğrenci belgeleri, sohbet, inceleme,
  kullanıcı yönetimi, rapor)
- `uniasist/veri/` — üniversite ve bölüm seed listeleri
- `sablonlar/`, `statik/` — arayüz
- `veri/ornek_belgeler/` — seed belgeleri
