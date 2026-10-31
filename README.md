# UniAsist

Üniversite öğrencileri için AI çalışma asistanı SaaS'ı. UniAsist herhangi bir
üniversiteye bağlı değildir: öğrenci akademik e-postasıyla (örn. `.edu.tr`)
kayıt olur, kendi derslerini takip eder, kendi belgeleriyle (PDF/TXT) AI
üzerinden çalışır. İstediğinde belgelerini takip ettiği derse paylaşır; dersin
diğer takipçileri bu belgeleri sohbette kaynak olarak görür (RAG). Doğal sohbet
akışı, sohbet geçmişi, geri bildirim, bildiri/moderasyon, kullanıcı yönetimi,
plan (Ücretsiz/Pro) yönetimi ve kullanım raporlama içerir.

## Kayıt ve doğrulama akışı

1. Kayıt yalnızca akademik e-posta adresleriyle yapılır — alan adı
   `AKADEMIK_ALAN_ADLARI` son eklerinden biriyle bitmelidir (`.edu.tr`, `.edu`,
   `.ac.uk`, `.edu.au`; `UNIASIST_AKADEMIK_ALANLAR` ortam değişkeniyle
   genişletilebilir). Gmail gibi adresler reddedilir.
2. Üniversite ve bölüm bilgisi serbest metindir (zorunlu değildir).
3. E-postanıza gönderilen doğrulama bağlantısıyla hesabınızı
   doğrulayın (geliştirme modunda bağlantı konsol kaydına yazılır —
   `uniasist.eposta` log'u). Doğrulama yapılmadan sohbet, belge ve kaynak
   ekranlarına erişilemez; yönetici muafdir.

## Dersler ve paylaşım

- Dersler globaldir: arar, bulur ya da yeni oluşturur ve takip edersiniz.
- Belgeler varsayılan olarak özeldir; yalnız siz (ve AI asistanınız) erişir.
- Belge paylaşımı Pro özelliğidir: paylaşılan belge, o dersi takip eden tüm
  öğrencilerin sohbet kapsamına girer ve `/kaynak/<id>` ile görünür olur.
- Uygunsuz içerik ders sayfasından bildirilebilir; yönetici moderasyonla
  değerlendirir.

## Planlar

| Plan | Soru | Belge | Paylaşım |
| --- | --- | --- | --- |
| Ücretsiz | Günde 10 | En fazla 3 | Yok |
| Pro | Sınırsız | Sınırsız | Var |

Pro şu an beta aşamasında — ödeme yakında; geçiş şimdilik ücretsizdir
(`/plan` sayfasından "Pro'ya Geç").

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

Uygulama http://127.0.0.1:5000 adresinde açılır. Kayıtsız kullanıcılar tanıtım
sayfasını görür. Boş veritabanında ilk açılışta örnek veri otomatik yüklenir.

**Önemli:** Veritabanı şeması v2 SaaS sürümüyle değişti. Önceki sürümün
`data/uniasist.db` dosyası varsa silin — uygulama ilk açılışta yeni şemayla ve
örnek veriyle taze veritabanı kurar (`data/` klasörü git-ignore'ludur).

## Demo hesapları

| Rol | E-posta | Şifre | Plan |
| --- | --- | --- | --- |
| Yönetici | admin@universite.edu.tr | Yonetici1234 | — |
| Öğrenci | ali@universite.edu.tr | Ogrenci1234 | Pro |
| Öğrenci | ayse@universite.edu.tr | Ogrenci1234 | Ücretsiz |

Ali 14 örnek belgenin sahibidir (Burs Yönergesi "Matematik I"e, Staj Yönergesi
"Fizik I"e paylaşılmıştır). Ayşe'nin 2 özel belgesi vardır ve her iki dersi de
takip eder — Ali'nin paylaşılan belgelerini sohbet kapsamında görür.

## Tema

Arayüz açık/koyu temalıdır. Üst çubuktaki tema düğmesi tercihi
`uniasist_tema` çerezine yazar; çerez yoksa tarayıcının
`prefers-color-scheme` ayarına uyulur.

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
set UNIASIST_AKADEMIK_ALANLAR=.edu.tr,.edu,.ac.uk (isteğe bağlı; virgülle ayrılmış son ekler)
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
set UNIASIST_TEMEL_URL=https://uniasist.example.com
```

`UNIASIST_TEMEL_URL` doğrulama bağlantısının başına yazılan temel adrestir
(varsayılan `http://127.0.0.1:5000`); SMTP açıkken uygulamanın erişilebildiği
adresi verecek şekilde ayarlayın.

## Test

```
.venv\Scripts\python -m pytest -q
```

## Değerlendirme (NFR-05)

```
.venv\Scripts\python degerlendir.py
```

Betik, 50 örnek soruyu doğrulanmış demo öğrencisi Ali'nin kapsamıyla
(kapsam=None: kendi belgeleri) gerçek servis üzerinden işler ve doğru yanıt
oranını raporlar (hedef %80). API anahtarı tanımlıysa hazır LLM, tanımlı
değilse yerel arama kullanılır.

## Katmanlar

- `uniasist/entity.py` — varlık sınıfları (Kullanici, Sohbet, Belge, Ders, ...)
- `uniasist/depo/` — SQLite depoları
- `uniasist/servis/` — iş kuralları (kimlik doğrulama, e-posta, RAG, bilgi
  tabanı, moderasyon, plan, rapor, ...)
- `uniasist/yapayzeka/` — LLM arayüzü, hazır servis ve yerel arama gerçeklemeleri
- `uniasist/ekran/` — Flask blueprint'leri (sohbet, belgelerim, dersler, plan,
  profil, kullanıcı yönetimi, rapor)
- `uniasist/veri/` — bölüm öneri listesi
- `sablonlar/`, `statik/` — arayüz (açık/koyu tema)
- `veri/ornek_belgeler/` — seed belgeleri
