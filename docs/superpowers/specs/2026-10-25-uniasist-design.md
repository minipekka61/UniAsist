# UniAsist — Tasarım Dokümanı

Tarih: 2026-10-25 · Durum: İnceleme bekliyor

## 1. Amaç ve Neden

Bu proje, "chat-bot projesi" klasöründeki dört belgede (gereksinim analizi, iş kuralları
ve use case'ler, UML sınıf diyagramı, sequence diyagramları) eksiksiz biçimde
tanımlanmış **UniAsist** sisteminin çalışan bir yazılım olarak kodlanmasıdır.

UniAsist, üniversite öğrencilerinin ve aday öğrencilerin akademik takvim, kayıt
yenileme, ders ekleme-bırakma, burs, yurt, staj, mezuniyet gibi konulardaki
sorularına, üniversitenin yönetmelik/duyuru/SSS belgelerinden oluşan bilgi tabanına
dayanarak (RAG) Türkçe ve kaynak göstererek yanıt veren web tabanlı bir sohbet
asistanıdır. Amaç: öğrencinin cevaba ulaşma süresini dakikalardan saniyelere
indirmek, öğrenci işlerinin tekrarlayan soru yükünü azaltmak ve eksik konuları
"yanıtlanamayan soru" kayıtlarıyla ölçülebilir kılmak.

Neden şimdi: İnsan partneri, dönem projesi kapsamında hazırladığı belgeleri
çalışır yazılıma dönüştürmek istiyor.

## 2. Hedefler

- Belgelerdeki **FR-01…FR-28** gereksinimlerinin, **IK-01…IK-35** iş kurallarının ve
  **UC-01…UC-24** kullanım durumlarının tamamının karşılanması.
- Tek komutla çalışır durumda olması (bkz. §6 Çalıştırma).
- OpenAI uyumlu API anahtarıyla gerçek LLM yanıtları; anahtar yoksa sistemin
  yerel arama moduna düşerek yine çalışması.
- Türkçe, masaüstü ve mobil tarayıcıda kullanılabilir (responsive) arayüz.
- İş kurallarını doğrulayan otomatik testler (pytest).

## 3. Hedef Olmayanlar ve Anti-Hedefler

Belgelerin 7.2 bölümü aynen geçerlidir: OBS entegrasyonu, öğrenci adına işlem
yapma, sesli/görsel girdi, Türkçe dışı dil, mobil uygulama, model eğitimi/ince ayarı,
canlı desteğe devretme, çok üniversiteli/yüksek eşzamanlılık ölçeklemesi **yapılmayacak**.

Ek olarak bu kodlama için:

- Gerçek üniversite verisi kullanılmayacak; bilgi tabanı örnek (kurgusal
  "universite.edu.tr") belgelerle dolacak.
- Canlıya çıkış (deployment), HTTPS, yedekleme gibi işletim konuları kapsam dışı.

Anti-hedef: belgelere aykırı davranan bir sistem (ör. kaynaksız yanıt göstermek,
Pasif belgeden yanıt üretmek, ziyaretçi sohbetini kalıcı saklamak) — teknik olarak
çalışsa bile başarısız sayılır.

## 4. Kısıtlar

- Ortam: Windows, Python 3.13 mevcut. Kod, standart kütüphane + Flask + pypdf +
  requests + pytest bağımlılıklarıyla sınırlı tutulur (hafif kurulum).
- Veritabanı: tek dosya SQLite (`data/uniasist.db`); sunucu kurulumu gerektirmez.
- Belgelerin sabittestiği parametreler değiştirilmez: benzerlik eşiği 0,60 (IK-14'teki
  "başlangıç değeri" API/embedding modu için aynen geçerli; §5.5'teki yerel yedek mod
  kendi kalibre edilmiş eşiğini kullanır); en fazla 5
  parça; bağlam son 10 mesaj; soru 1–500 karakter; 5 hatalı girişte 15 dk kilit;
  oturum 30 dk; belge PDF/TXT ve ≤10 MB; geri bildirim açıklaması ≤300 karakter;
  LLM zaman aşımı 30 sn; CSV UTF-8 + noktalı virgül; rapor varsayılan son 30 gün;
  indekslemede 3 yeniden deneme.
- UML sınıf adları ve sorumlulukları korunur (Türkçe adlarla 1:1 eşleme, §5.1).

## 5. Nasıl Kararları

### 5.0 Yaklaşımlar (değerlendirilen alternatifler)

| Yaklaşım | Durum | Gerekçe |
|---|---|---|
| **A. Python + Flask + SQLite + Jinja2** | **Seçildi** | Kurulumu/run'ı en kolay; PDF işleme ve metin arama ekosistemi güçlü; eş zamanlılık hedefi düşük olduğundan Flask yeterli. |
| B. Java + Spring Boot | Reddedildi | UML sözdizimine en yakın; ancak kurulum ağırlığı ve geliştirme süresi bu senaryo için gereksiz yük. |
| C. Node.js + Express | Reddedildi | PDF metin çıkarma/embedding tarafında Python kadar pratik değil. |

LLM tarafında değerlendirilen alternatifler: yalnızca gerçek API (anahtar yoksa sistem
hiç çalışmaz — reddedildi), yalnızca yerel arama (RAG yanıtları zayıf — reddedildi);
**seçilen**: `IYapayZekaServisi` arayüzü üzerinden iki gerçekleme (API varsa
`HazirLLMServisi`, yoksa `YerelAramaServisi`) — belgelerdeki arayüz tasarımına da uyar.

Kalıcılık tarafında değerlendirilen alternatifler: SQLAlchemy ORM (reddedildi — UML'deki
Depo sınıflarını gölgeler) vs. **stdlib sqlite3 üzerine elle yazılmış Depo sınıfları**
(seçildi — UML ile 1:1 eşleşir, bağımlılık azalır).

### 5.1 Mimari eşleme (UML → Python)

Proje kökü: `chat-bot projesi/UniAsist/` (yeni klasör; PDF'ler klasörde kalır).

```
UniAsist/
├─ app.py                  # Flask uygulaması, blueprint kayıtları, başlatma
├─ config.py               # API anahtarı/model, alan adı, sabitler (env ile ezilebilir)
├─ requirements.txt
├─ uniasist/
│  ├─ __init__.py
│  ├─ enumlar.py           # Rol, HesapDurumu, KaynakDurumu, KayitDurumu,
│  │                       # GeriBildirimTuru, GonderenTuru, SonucDurumu
│  ├─ entity.py            # Kullanici, Oturum, Sohbet, Mesaj, KaynakReferansi,
│  │                       # GeriBildirim, BilgiKaynagi(abstract), Belge, SSSGirdisi,
│  │                       # IcerikParcasi, YanitlanamayanSoru, SoruKaydi
│  ├─ dto.py               # YanitSonucu, AramaSonucu, KullanimRaporu, GeriBildirimOzeti
│  ├─ hatalar.py           # IsKuraliIhlaliException (kuralNo + mesaj)
│  ├─ depo/                # KullaniciDeposu, SohbetDeposu, BilgiKaynagiDeposu,
│  │                       # YanitlanamayanSoruDeposu, SoruKaydiDeposu, GeriBildirimDeposu
│  ├─ servis/              # KimlikDogrulamaServisi, KullaniciYonetimServisi,
│  │                       # SohbetServisi, YanitUretmeServisi, YanitlanamayanSoruServisi,
│  │                       # BilgiTabaniServisi, BelgeIslemeServisi, GeriBildirimServisi,
│  │                       # RaporServisi, AramaDizini
│  ├─ yapayzeka/           # IYapayZekaServisi(abstract), HazirLLMServisi,
│  │                       # YerelAramaServisi (TF-IDF tabanlı)
│  └─ ekran/               # UML «boundary» sınıfları → Flask blueprint'leri:
│                          # giris, sohbet, geribildirim, belgeyonetim,
│                          # yanitlanamayansoru, kullaniciyonetimi, rapor
├─ sablonlar/              # Jinja2 HTML şablonları (ekran başına sayfalar)
├─ statik/                 # CSS + vanilla JS (sohbet arayüzü, form doğrulama)
├─ veri/
│  ├─ ornek_belgeler/      # Seed: 12–15 örnek TXT belgesi + 10 SSS girdisi
│  └─ dosyalar/            # Yüklenen belge dosyaları
└─ tests/                  # pytest testleri
```

EBC kuralı aynen uygulanır: istek akışı `ekran (blueprint) → servis → varlık/depo`;
varlık sınıfları Flask'i ve servisleri bilmez.

### 5.2 Veri modeli (SQLite tabloları)

`kullanici`, `oturum`, `sohbet`, `mesaj`, `kaynak_referansi` (mesaj FK),
`geri_bildirim`, `bilgi_kaynagi` (tek tablo: `tur` sütunuyla Belge/SSSGirdisi ayrımı —
`dosya_adı`, `dosya_turu`, `boyut_byte`, `dosya_yolu`, `surum_no` yalnız Belge'de, `soru`,
`cevap` yalnız SSSGirdisi'nde NULL olabilir), `icerik_parcai` (kaynak FK, `gomme`
JSON olarak), `yanitlanamayan_soru`, `soru_kaydi`.

İlişkiler ve çokluklar UML'deki gibidir (Sohbet 1—0..* Mesaj, Mesaj 1—0..* KaynakReferansi,
Kullanici 1—0..* Sohbet, BilgiKaynagi 1—0..* IcerikParcasi, YanitlanamayanSoru 0..1—0..1 SSSGirdisi vb.).
Şifreler PBKDF2-HMAC-SHA256 ile tuzlanmış hash olarak saklanır (stdlib; dış bağımlılık yok).

### 5.3 Kimlik doğrulama ve oturum

- `KimlikDogrulamaServisi.girisYap`: kullanıcı bul → şifre doğrula → kilitli mi →
  aktif mi (SD-1 sırası) → `Oturum` yarat. 5 hatalı denemede hesap 15 dk kilitlenir
  (IK-04); hata mesajı hangisinin yanlış olduğunu belirtmez.
- Oturum: DB'de `oturum` tablosu + HttpOnly çerezde token. Her istekte
  `oturumDogrula` 30 dakikalık kayan süreyi (IK-08) günceller.
- Kayıt: yalnız `@universite.edu.tr` alan adı (config'den), e-posta benzersizliği,
  şifre kuralı (≥8 karakter, ≥1 harf, ≥1 rakam), rol daima ÖĞRENCI (IK-01…03, 06).

### 5.4 RAG boru hattı (YanitUretmeServisi)

1. **Soru doğrulama** (SohbetServisi): boş/uzunluk (IK-11), kapsam kontrolü (IK-15 —
   yerel anahtar kelime listesiyle üniversite konuları; eşleşmezse ret ve kapsam açıklaması).
2. **Bağlam**: aynı sohbetteki son 10 mesaj (IK-16).
3. **Arama**: `gommeUret(soru)` → `AramaDizini.enYakinParcalar(sorgu, 5)` → kosinüs
   benzerliği; en yüksek skor < 0,60 ise LLM çağrılmaz (IK-14).
4. **Yanıt üretimi**: `HazirLLMServisi.yanitUret(soru, parcalar, baglam)` — "yalnızca
   verilen içeriğe dayanarak yanıtla; dayanamıyorsan yalnızca `BILGI_YOK` yaz" sistem
   talimatıyla chat-completions çağrısı, 30 sn zaman aşımı (IK-19). Yanıt akışı SSE
   (server-sent events) ile parça parça istemciye aktarılır; NFR-01 ("ilk yanıt
   parçası 5 saniye içinde") bu şekilde karşılanır (yerel modda yanıt anlıktır).
   Model `BILGI_YOK` işaretini döndürürse sonuç ICERIK_BULUNAMADI dalına yönlendirilir:
   kullanıcıya "kesin bilgiye sahip değilim" + birim iletişim bilgisi gösterilir ve
   soru yanıtlanamayan olarak kaydedilir — böylece kaynaksız yanıt hiç gösterilmez
   (IK-13) ve gerçek bilgi boşluğu raporlara yansır (IK-29).
5. **Sonuç dalları** (SD-2): YANIT / ICERIK_BULUNAMADI (eşik altı veya `BILGI_YOK`;
   "Bu konuda kesin bilgiye sahip değilim" + birim iletişim bilgisi; soru
   YanıtlanamayanSoru olarak kaydedilir, aynı soru varsa tekrar sayısı artar —
   IK-29) / SERVIS_HATASI (kullanıcıya "tekrar deneyin"; soru yanıtlanamayan olarak
   KAYDEDİLMEZ — IK-19).
6. Her yanıtla "Bu yanıt bilgilendirme amaçlıdır, resmî belgeyi kontrol ediniz"
   uyarısı ve kişisel veri uyarısı (IK-17, IK-18) gösterilir.

**Parçalama** (BelgeIslemeServisi.parcalaraBol): cümle sınırlarında ~900 karakterlik
parçalar, ~150 karakter örtüşme; her parçaya `kaynakId + sira` ile
`bolumBilgisi = "başlık, parça N"` atanır. PDF metni pypdf ile çıkarılır; çıkan
metin yetersizse (taranmış PDF) belge PASIF kalır (IK-25). Embedding ve indeksleme
hatalarında 3 kez yeniden deneme (SD-3).

### 5.5 Yapay zekâ servisi

- `HazirLLMServisi` (birincil): OpenAI uyumlu REST. Ayarlar `config.py` + ortam
  değişkenleri: `UNIASIST_API_KEY`, `UNIASIST_API_BASE`, `UNIASIST_MODEL`,
  `UNIASIST_EMBEDDING_MODEL`. `gommeUret` embeddings endpoint'ini çağırır.
- `YerelAramaServisi` (yedek): API anahtarı yoksa otomatik seçilir; kelime +
  karakter n-gram TF-IDF vektörleri (Türkçe için ek morfolojisine dayanıklı) ve
  en iyi parçalardan çıkarımsal (extractive) yanıt üretimi. Arayüz aynı olduğundan
  sistem geri kalanı bundan habersiz çalışır. Arayüzde "Yerel mod" rozeti gösterilir.
  TF-IDF kosinüs skorları API embedding'lerinden sistematik düşük dağılır; bu nedenle
  yerel mod kendi kalibre edilmiş benzerlik eşiğini kullanır (başlangıç 0,20;
  `config.py`'de `YEREL_ESIK`). NFR-05 değerlendirmesi birincil (API) modda yapılır.
- **Gömme tutarlılığı**: her `icerik_parcasi` satırına gömmeyi üreten sağlayıcının
  etiketi (`gomme_saglayici`: "api:<model>" ya da "yerel:<sürüm>") yazılır. Uygulama
  açılışında etkin sağlayıcı, kayıtlı etiketlerle karşılaştırılır; uyuşmazlık varsa
  tüm aktif parçalar etkin servis ile yeniden gömülür (yeniden indeksleme, 3 deneme
  kuralıyla). Böylece mod değişiminde (anahtar ekleme/çıkarma) ve TF-IDF sözlük
  eskimesinde arama bozulmaz.
- IK-19 kapsamında dış servis hatası/30 sn zaman aşımı kullanıcıya anlaşılır hata
  olarak döner.

### 5.6 Bilgi tabanı yönetimi

Yükleme (UC-13/14, SD-3): tür/boyut/zorunlu alan doğrulama (PDF/TXT, ≤10 MB, başlık
+ kategori — IK-24) → belge PASIF kaydet → metin çıkar → parçala → gömme üret →
dizine ekle → AKTIF yap. Güncelleme (UC-15): yeni dosya yoksa yalnız başlık/kategori;
yeni dosya varsa yeni parçalar indekslenene kadar eski parçalar yanıt vermeye devam
eder (IK-26), tamamlanınca eski parçalar dizinden silinir. Silme (UC-16): onay şart
(IK-27), dizindeki parçaları da siler; geçmiş yanıtlardaki kaynak bağlantısı "bu
kaynak artık mevcut değil" der. SSS girdileri (UC-17) de bilgi kaynağıdır; yanıtlarda
kaynak adı "SSS" olarak gösterilir (IK-28).

### 5.7 Sohbet, geçmiş, geri bildirim

- Ziyaretçi sohbeti yalnız bellekte/oturum çerezinde; kalıcı kaydedilmez (IK-20).
  Öğrenci sohbeti DB'de; yalnız sahibi görür (IK-21). Yeni sohbet başlatınca mesajlı
  sohbet geçmişe kaydedilir (IK-35). Sohbet silinince bağlı geri bildirimler de silinir;
  anonim yanıtlanamayan soru kayıtları kalır (IK-23).
- Geri bildirim (UC-10): yanıt başına tek kayıt, değiştirilebilir; YARARSIZ'da isteğe
  bağlı ≤300 karakter açıklama (IK-22). Personele listeler kimliksiz gösterilir (IK-30).

### 5.8 Yönetici paneli ve raporlama

- Kullanıcı listeleme/arama (UC-20); rol değiştirme yalnız ÖĞRENCI↔PERSONEL ve
  kendisi/hedef yönetici değilse (IK-10, IK-32); devre dışı bırakma: oturumları
  anında sonlanır, veriler kalır, son aktif yönetici engellenir (IK-31).
- Rapor (UC-23/24): tarih aralığı (varsayılan son 30 gün, bitiş ≥ başlangıç —
  IK-33); toplam soru, yanıtlanamayan oranı, olumlu geri bildirim oranı, en çok
  sorulan 5 kategori (yanıtta kaynak gösterilen belgenin kategorisi — IK-34);
  CSV: UTF-8, `;` ayraçlı, dosya adı `UniAsist_Rapor_<başlangıç>_<bitiş>.csv`.

### 5.9 Örnek veri ve demo hesaplar

İlk çalıştırmada (`flask seed` komutu / ilk `app.py` çalıştırmasında boş DB varsa
otomatik): `admin@universite.edu.tr / Yonetici1234` (YÖNETİCI),
`personel@universite.edu.tr / Personel1234` (PERSONEL),
`ogrenci@universite.edu.tr / Ogrenci1234` (ÖĞRENCI) hesapları; 12–15 gerçekçi
Türkçe örnek belge (lisansüstü/lisans yönetmeliği bölümleri, akademik takvim,
burs yönergesi, yurt, staj, mezuniyet, ders ekle-bırakma) ve ~10 SSS girdisi;
her belgeye kategori atanır ve indekslenir.

### 5.10 Arayüz

Sunucu taraflı Jinja2 + tek CSS + vanilla JS. Sohbet sayfası: mesaj balonları,
"yazıyor…" göstergesi (FR-14), yanıtın SSE ile parça parça (stream) çizilmesi
(NFR-01), kaynak çipleri (tıklayınca kaynak içeriği vurgulu açılır — UC-07),
yararlı/yararsız butonları, yeni sohbet, geçmiş listesi. Tüm
metinler Türkçe; layout mobil uyumlu (NFR-06, FR-07).

### 5.11 Test stratejisi

- Birim testleri: entity iş kuralları (kilit, şifre, geçerlilikler), servis testleri
  (geçici SQLite DB ile), mock `IYapayZekaServisi` ile RAG dalları (YANIT /
  ICERIK_BULUNAMADI / SERVIS_HATASI), eşik ve bağlam mantığı.
- Her test, doğruladığı iş kuralını adında taşır (ör. `test_ik04_bes_hatali_denemede_kilit`).
- Flask istemci testleri: rol bazlı erişim (NFR-03), formlar, CSV çıktısı.
- NFR-05'teki 50 soruluk değerlendirme seti, sistem çalışır hâle geldikten sonra
  örnek belgelerden otomatik üretilir ve ayrı bir değerlendirme betiğiyle koşar.

## 6. Çalıştırma

```
cd UniAsist
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python app.py            # http://127.0.0.1:5000
```

API anahtarı: `UNIASIST_API_KEY` ortam değişkeni ya da `config.py` içine yazım.
Anahtar yoksa sistem yerel arama moduyla açılır.

## 7. Yapımcıya Bırakılan Kararlar

- LLM sistem talimatının tam sözcükleri (§5.4'teki ilkeye sadık kalmak koşuluyla).
- CSS görünüm ayrıntıları.
- Parçalama parametrelerinin ince ayarı (900/150 başlangıç değeridir).
- IK-15 kapsam kontrolü anahtar kelime listelerinin somut içeriği.
- Test sabitlerindeki örnek veri ayrıntıları.
