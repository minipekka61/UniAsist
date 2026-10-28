# UniAsist

Üniversite öğrenci destek asistanı: belge tabanlı soru yanıtlama (RAG), sohbet geçmişi,
bilgi tabanı yönetimi, kullanıcı yönetimi ve kullanım raporlama içeren Flask uygulaması.

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

Uygulama http://127.0.0.1:5000 adresinde açılır. Boş veritabanında ilk açılışta örnek
veri (3 hesap, 14 belge, 10 SSS girdisi) otomatik yüklenir.

## Demo hesapları

| Rol | E-posta | Şifre |
| --- | --- | --- |
| Yönetici | admin@universite.edu.tr | Yonetici1234 |
| Personel | personel@universite.edu.tr | Personel1234 |
| Öğrenci | ogrenci@universite.edu.tr | Ogrenci1234 |

Giriş yapmadan (ziyaretçi olarak) da sohbet edilebilir; ziyaretçi sohbetleri kalıcı
olarak saklanmaz.

## Yapay zekâ sağlayıcısı

API anahtarı tanımlı değilse uygulama yerel arama modunda çalışır (TF-IDF benzeri
gömme vektörleriyle belge arama; yanıtlar belge metninden derlenir). Sağlayıcı olarak
OpenAI uyumlu bir REST API kullanmak için aşağıdaki ortam değişkenlerini tanımlayın:

```
set UNIASIST_API_KEY=...                (zorunlu)
set UNIASIST_API_BASE=https://api.openai.com/v1   (isteğe bağlı)
set UNIASIST_MODEL=gpt-4o-mini          (isteğe bağlı)
set UNIASIST_EMBEDDING_MODEL=text-embedding-3-small (isteğe bağlı)
set UNIASIST_DB=data/uniasist.db        (isteğe bağlı)
set UNIASIST_SECRET_KEY=...             (üretime alırken zorunlu önerilir)
```

Sağlayıcı değiştiğinde indeksli parçalar açılışta otomatik olarak yeniden gömülür.

## Test

```
.venv\Scripts\python -m pytest -q
```

## Değerlendirme (NFR-05)

```
.venv\Scripts\python degerlendir.py
```

Betik, 50 örnek soruyu gerçek servis üzerinden işler ve doğru yanıt oranını raporlar
(hedef %80). API anahtarı tanımlıysa hazır LLM, tanımlı değilse yerel arama kullanılır
ve hangi sağlayıcının kullanıldığı raporun ilk satırında yazar.

## Katmanlar

- `uniasist/entity.py` — varlık sınıfları (Kullanici, Sohbet, Belge, ...)
- `uniasist/depo/` — SQLite depoları
- `uniasist/servis/` — iş kuralları (kimlik doğrulama, RAG, bilgi tabanı, rapor, ...)
- `uniasist/yapayzeka/` — LLM arayüzü, hazır servis ve yerel arama gerçeklemeleri
- `uniasist/ekran/` — Flask blueprint'leri
- `sablonlar/`, `statik/` — arayüz
- `veri/ornek_belgeler/` — seed belgeleri
