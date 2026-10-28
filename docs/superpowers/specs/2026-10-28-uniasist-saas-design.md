# UniAsist SaaS Dönüşümü — Tasarım (v1)

> Onay tarihi: 2026-10-28. Bu doküman, kullanıcıyla soru-cevapla netleştirilip onaylanan tasarımı kaydeder.

## Amaç ve Neden

UniAsist bugün tek üniversiteli bir öğrenci destek chatbot'u: kayıt tek e-posta alan adına kilitli, belgeleri personel yükler, her belge herkese açıktır. Bu proje onu, öğrencilerin **kendi yükledikleri belgelerle ders çalışabildiği** ve belgelerini **aynı üniversite + aynı bölümden arkadaşlarıyla paylaştığı**, çok üniversiteli bir SaaS'a dönüştürür.

Değer önerisi: her öğrenciye kişisel ders asistanı + bölümün ortak belge havuzu büyüdükçe zenginleşen yanıtlar (RAG).

Kullanıcıyla alınan temel kararlar:

- **Üyelik:** üniversite e-posta alan adından otomatik üniversite, kayıtta listeden bölüm seçimi; e-posta sahipliği doğrulama bağlantısıyla kanıtlanır
- **AI gelişimi:** RAG (arama tabanlı); fine-tuning yok
- **Roller:** ÖĞRENCİ + platform YÖNETİCİSİ (personel rolü kalkar)
- **Ücretlendirme:** ücretsiz v1
- **Yayına alma:** şimdilik yerel geliştirme; sunucu/HTTPS sonraki aşama

## Hedefler

1. Öğrenci üniversite e-postasıyla kayıt olur; üniversite alan adından belirlenir, bölümünü listeden seçer; e-postasına gelen bağlantıyla hesabı aktifleşir
2. Öğrenci PDF/TXT belgelerini yükler, listeler, günceller, siler; isterse "paylaşılan" yapar / paylaşmayı bırakır
3. Chatbot (RAG) soruları şu kapsamda yanıtlar: öğrencinin kendi belgeleri + aynı üniversite ve aynı bölümden diğer öğrencilerin paylaştığı belgeler
4. Öğrenci bölümünün paylaşılan belgelerini uygulama içinde görüntüleyebilir
5. Paylaşılan belgeler bildirilebilir; platform yöneticisi moderasyon yapar (sil / yok say)
6. Yönetici: kullanıcılar, rapor, yanıtlanamayan sorular, bildirimler
7. Sohbet geçmişi ve geri bildirim aynen kalır

## Hedef olmayanlar (v1)

- Ücretlendirme, abonelik planları, kullanım limitleri
- Model fine-tuning
- Personel rolü, SSS, ziyaretçi sohbeti (kaldırılıyor)
- Canlıya alma (sunucu, alan adı, HTTPS) — sonraki aşama
- PostgreSQL geçişi (SQLite + kilitli bağlantı yeterli; canlıya çıkarken değerlendirilir)
- DOCX/PPTX desteği (PDF/TXT kalıyor)
- Şifre sıfırlama akışı (e-posta altyapısı hazır olunca ileride eklenebilir)

## Anti-hedefler

- Paylaşılan bir belge başka üniversite veya başka bölümden bir öğrenciye görünürse ürün başarısızdır
- Doğrulanmamış e-postalı hesap paylaşım yapamaz
- Mevcut test güvencesi (146 test) kaybolmaz — kaldırılan özelliklerin testleri düşer, kalanlar uyarlanır, yeniler eklenir

## Kısıtlar

- Aynı repo, aynı mimari (entity → depo → servis → ekran, Flask + SQLite)
- Geliştirmede e-posta gönderimi konsola/log'a yazılır; SMTP gerçeklemesi arayüzle hazır, config ile açılır
- Üniversite-alan adı eşlemesi ve bölüm listesi seed verisidir (Türkiye üniversiteleri)

## Yaklaşımlar

- **A (seçildi): mevcut kod tabanını dönüştür.** RAG çekirdeği (parçalama, gömme, arama, BILGI_YOK, SSE), güvenlik (PBKDF2, hesap kilitleme) ve auth iskeleti zaten çalışıyor ve 146 testle güvence altında; değişikliklerin çoğu ekleme (sahiplik, görünürlük, kapsam) ve çıkarma (personel, SSS, ziyaretçi). Katmanlar aynı kalır. En hızlı yol; riski tek kiracılı kalıntılardır — testler yakalar.
- **B (reddedildi): taze başla, parçaları taşı.** Temiz veri modeli ama depo/ekran/test katmanları sıfırdan yazılır, test güvencesi kaybolur; aynı sonuç için belirgin biçimde daha yavaş.

## Tasarım Kararları

### 1. Üniversite modeli

- `universite` tablosu: `id`, `ad`, `eposta_alan_adi` (v1'de üniversite başına tek kayıtlı alan adı)
- Kayıtta e-posta alan adı **son ek eşleşmesi** ile bulunur (`@ogrenci.x.edu.tr` → `x.edu.tr`); alt alan adları kapsanır
- Eşleşme yoksa: "Üniversiteniz henüz desteklenmiyor" hatası
- Seed: Türkiye'deki devlet + vakıf üniversiteleri ve öğrenci e-posta alan adları
- `config.UNIVERSITE_ALAN_ADI` sabiti kalkar (yerini tablo alır)

### 2. Bölüm modeli

- `bolum` standart liste (seed, YÖK akademik birim adlarından türetilmiş); kayıtta açılır listeden seçim
- Serbest metin YOK — paylaşım kapsamı eşleşmesi için standart ad şart
- Bölüm kayıtta seçilir, sonradan değiştirilemez (v1)

### 3. Kullanıcı modeli

- Yeni alanlar: `universite_id`, `bolum`, `eposta_dogrulandi`, `dogrulama_token`, `dogrulama_bitis`
- `HesapDurumu.DOGRULAMA_BEKLIYOR` eklenir
- Kayıt akışı: form → hesap DOGRULAMA_BEKLIYOR + doğrulama token'ı (uuid4, 24 saat, tek kullanımlık) → e-postaya bağlantı → AKTİF; token yeniden gönderilebilir
- Girişte DOGRULAMA_BEKLIYOR: uyarı gösterilir, paylaşım yapılamaz
- Roller: OGRENCI, YONETICI (PERSONEL kaldırılır)
- IK-01 kuralı: sabit alan adı yerine universite tablosundan eşleşme
- Yönetici hesabı seed ile oluşur (env ile ezilebilir); kayıttan yönetici olunmaz

### 4. Belge modeli

- Yeni alanlar: `sahip_id`, `gorunurluk` (OZEL / PAYLASILAN), `universite_id`, `bolum` (sahibinden kopyalanır — kapsam sorguları için denormalize)
- Belge işlemleri (yükle/güncelle/sil) yalnız sahibi yapar
- Görünürlük değiştirme (paylaş / paylaşmayı bırak) sahibinin tek tıkla işi; parçaların görünürlüğü de güncellenir
- Silme: arama dizini + kayıtlar kaskatlı temizlenir (mevcut davranış)

### 5. Arama kapsamı

- `IcerikParcasi`'ye sahiplik/görünürlük/üniversite/bölüm alanları taşınır
- `enYakinParcalar` kapsam filtresi: `parça.sahip_id = öğrenci OR (gorunurluk = PAYLASILAN AND aynı üniversite AND aynı bölüm)`
- RAG çekirdeği (parçalama, gömme, eşik, BILGI_YOK, SSE) değişmez

### 6. Kaynak görüntüleme kapsam kontrolü

- `/kaynak/<id>` rotası da aynı kapsam filtresinden geçer: başka öğrencinin özel belgesine URL ile erişilemez, kendi üniversite/bölümü dışındaki paylaşılan belge görüntülenemez

### 7. Ekranlar

- **Öğrenci belge ekranı (yeni):** "Belgelerim" ve "Bölümün paylaşılanları" sekmeleri; yükle, güncelle, sil, paylaş/paylaşmayı bırak, bildir
- **Kayıt:** bölüm seçimi + üniversite eşleşme hatası; doğrulama bilgi sayfası; `/dogrula/<token>` rotası; doğrulama e-postasını yeniden gönder
- **Sohbet:** aynı; kapsam otomatik. `/` kayıtsız kullanıcıyı giriş sayfasına yönlendirir (ziyaretçi sohbeti kalkar)
- **Yönetici:** mevcut kullanıcılar (üniversite/bölüm sütunlarıyla), rapor, yanıtlanamayan sorular + bildirim moderasyonu ekranı
- **Kaldırılan:** personel blueprint'leri, SSS ekranları, ziyaretçi sohbeti

### 8. Bildir / moderasyon

- `bildirim` tablosu: `belge_id`, `bildiren_id`, `neden`, `durum` (ACIK / DEGERLENDIRILDI), `tarih`
- Yalnız paylaşılan belgeler bildirilebilir; bir öğrenci bir belgeyi bir kez bildirir
- Yönetici bildirimi değerlendirir: belgeyi siler ya da bildirimi yok sayar

### 9. E-posta servisi

- `IEpostaServisi` arayüzü: `dogrulamaEpostasiGonder(eposta, ad_soyad, baglanti)`
- Geliştirme gerçeklemesi: konsol/log yazar (`MAILGONDER=0` varsayılan)
- SMTP gerçeklemesi: `smtplib` + config anahtarları; canlıya çıkarken açılır

### 10. Test stratejisi

- Kaldırılan özelliklerin testleri silinir (ziyaretçi sohbeti, SSS, personel ekranları)
- Kalanlar uyarlanır; yeniler: alan adı son ek eşleşmesi, doğrulama akışı (token, süre, tek kullanım), görünürlük/kapsam izolasyonu (başka bölüm ve başka üniversite göremez — en kritik test), belge sahipliği, bildir/moderasyon, `/kaynak` rotası izolasyonu
- Süit her görevde yeşil kalır

## Yapıcının Kararları (kullanıcı onaylı calls)

- Paylaşılan belge uygulama içinde görüntülenir; ham dosya indirme v1'de yok
- Bölüm kayıtta seçilir, sonradan değiştirilemez
- Yönetici hesabı seed ile oluşur
- Belge limitleri: dosya başına 10 MB kalır, adet limiti yok

## Yapıcıya kalan

- Test dosyası/durum ayrıntıları, şablon metinleri, seed listelerinin tam içeriği, SMTP config anahtar adları, görev sıralaması
