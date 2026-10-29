# UniAsist v2 — Öğrenci Çalışma Asistanı SaaS Tasarımı

**Tarih:** 2026-10-29
**Durum:** Onaylandı (ürün sahibi ile soru-cevap şeklinde netleştirildi)

## Amaç ve Neden

UniAsist bugün tek üniversiteye bağlı bir ders projesi: kayıt yalnız 25 üniversitenin
e-postasıyla, paylaşım "aynı üniversite + aynı bölüm" ile sınırlı, sohbet ise yalnız belge
soru-cevabı yapan katı bir asistan. Ürün sahibi bunu **öğrencilere tek tek abone satılan,
üniversiteden bağımsız, profesyonel ve sade bir SaaS**'a dönüştürmek istiyor; ileride
internete çıkarıp satılacak.

Temel değer önerisi: öğrenci elindeki ders dokümanlarını yükler, AI onlarla **doğal
sohbet ederek** daha hızlı ve düzenli çalışır; isteyen dokümanını global bir derse
etiketleyip o dersi alan diğer öğrencilere yardımcı olur.

## Hedefler

- Öğrenciye satılabilir abonelik modeli: Ücretsiz katman (değer deneyimlenebilsin) + Pro.
- Doğal, ChatGPT benzeri sohbet; ders materyaline dayalı yanıtlarda kaynakça.
- Global ders bazlı paylaşım ("dersi takip et" modeli).
- Akademik e-posta kapısı ile yalnız üniversite öğrencilerinin kullanımı.
- Modern SaaS görünümü: mavi→yeşil gradient, açık/koyu tema, tanıtım sayfası.
- Profil ekranı (üyelik bilgileri + şifre değiştirme).

## Hedef Olmayanlar (v2)

- Gerçek ödeme tahsilatı (iyzico/Stripe) — yalnız plan altyapısı; tahsilat sonraki sürümde
  aynı iskelete bağlanır.
- PostgreSQL / bulut dosya depolama / SPA (React) / mobil uygulama / çok dil.
- Topluluk/sosyal özellikler (ders forumu vb.).

## Karşı-Hedefler (başarısızlık sayılır)

- Kalıp/şablon AI cevapları (bugünkü "Bu konuda kesin bilgiye sahip değilim…" döngüsü).
- Kayıtta üniversite listesi bakımı gerektiren bir kapı (25 üniversite sabit listesi).
- Menü/ekran kalabalığı: öğrenci arayüzünde yönetici işlevleri görünür olması.
- Kaynakçaların her yanda çip olarak dizilmesi (yalnızca açılır "Kaynakçalar" listesi).

## Kısıtlar

- Mevcut yığın korunur: Python 3.13, Flask, sqlite3 (stdlib), pypdf, requests, pytest,
  smtplib. **Yeni pip/npm bağımlılığı eklenmez.**
- Katmanlı mimari korunur: entity → depo → servis → ekran.
- Kullanıcıya görünen metinler Türkçe; iş kuralı ihlalleri
  `IsKuraliIhlaliException(kural_no, mesaj)` ile.
- Şema değişiklikleri `uniasist/depo/veritabani.py` içindeki `_SEMA`'ya; eski yerel DB
  silinip taze kurulur (`data/` git-ignore'lu).
- Tam test süiti her görev sonunda yeşil olmalı (`.venv\Scripts\python -m pytest -q`).

## Yaklaşımlar

1. **A (seçilen):** Flask iskeleti ve katmanlı yapı korunur; arayüz sıfırdan yazılmış
   modern bir CSS tasarım sistemiyle (sunucu tarafında render) yenilenir. Hızlı, düşük
   riskli, 182 testlik altyapı ve katmanlar korunur; yeni bağımlılık yok. Tam SPA
   akıcılığı yoktur.
2. **B (reddedilen):** Flask API + React/Vue SPA. En modern his ve gelecek mobil kolaylığı;
   ama yeni araç zincili (Node/build), tüm ekranların ve testlerin yeniden yazımı, yüksek
   süre/risk. Ürün traksiyon kazandıktan sonra düşünülür.

Ürün sahibi A'yı seçti. Gerekçe: "profesyonel, sade, satılabilir" görünüm A ile de
elde edilir; B'nin maliyeti şimdiki hedef için gereksiz.

## Ürün Kararları (ürün sahibi onaylı)

1. **Ticari model:** öğrenciler tek tek abone olur; üniversiteye kurumsal satış yok.
2. **Katmanlar:** Ücretsiz = kayıt, ders paylaşılanlarını görme, **3 belge yükleme**,
   **günde 10 soru**. Pro = sınırsız belge + sınırsız sohbet + **paylaşım**
   (`PAYLASILAN` görünürlüğü yalnız Pro — IK-36).
3. **Pro'ya geçiş:** v1'de self-servis; `/plan` ekranındaki düğme anında Pro yapar
   ("beta — ödeme yakında" notuyla). Geri dönüş (Pro→Ücretsiz) de mümkün. Tahsilat
   sonradan aynı iskelete bağlanır.
4. **Kayıt kapısı:** akademik e-posta alan adı (config listesi) + bağlantıyla doğrulama.
   Kişisel adresler (Gmail vb.) kayıtta reddedilir (IK-01).
5. **Doğrulama zorunlu:** doğrulanmamış hesap giriş yapabilir ama yalnız doğrulama
   ekranını görür; sohbet/belge/ders ekranları kapalı (IK-35). Amaç: uygulamayı yalnız
   öğrenciler kullansın, bilgi kirliliği olmasın.
6. **Profil:** üniversite/bölüm opsiyonel serbest metin (öneri listeleriyle); menüdeki
   "Şifre Değiştir" kalkar, Profil ekranına taşınır.
7. **Paylaşım modeli:** global **ders** bazlı; öğrenci belgeyi bir derse etiketler,
   dersi **takip eden** öğrenciler o belgeyi görür. Ders adı serbest metin (öneri +
   benzersizlik); global ad alanı.
8. **Sohbet:** doğal konuşma; kapsam anahtar kelimesi ve kara liste filtreleri kalkar.
   Ders materyaline özgü bilgi uydurulmaz ("materyallerinde bulamadım" denir).
9. **Kaynakça:** yanıt kaynak kullandıysa yalnızca mesajın en altında "Kaynakçalar"
   düğmesi görünür; tıklanınca liste açılır; başka hiçbir yerde kaynak gösterilmez.
10. **Görünüm:** mavi→yeşil gradient vurgu; açık/koyu tema (kullanıcı tercihi kalıcı,
    varsayılan sistem); ilk girişte herkese açık **tanıtım sayfası** (hero, özellikler,
    fiyatlandırma, CTA).
11. **LLM:** ürün sahibinin OpenAI uyumlu API anahtarı var; gerçek model varsayılan,
    yerel mod yalnızca anahtarsız geliştirme yedeği.

## Ayrıntılı Tasarım

### Veri modeli

- `kullanici`: `universite_id INTEGER` → `universite TEXT` (opsiyonel); `bolum TEXT`
  (opsiyonel) kalır; **`plan TEXT NOT NULL DEFAULT 'UCRETSIZ'`** eklenir (`UCRETSIZ`/`PRO`).
- Yeni tablo `ders (ders_id INTEGER PK, ad TEXT NOT NULL UNIQUE)`.
- Yeni tablo `kullanici_ders (kullanici_id, ders_id, UNIQUE(kullanici_id, ders_id))`.
- `bilgi_kaynagi` ve `icerik_parcasi`: `universite_id`, `bolum` sütunları → **`ders_id`**.
- `soru_kaydi`: **`kullanici_id`** eklenir (günlük kota sayımı).
- `universite` tablosu, `UniversiteDeposu`, `alanAdindanBul`, `veri/universiteler.py`
  silinir. `veri/bolumler.py` yalnızca bölüm öneri listesi olarak kalır.
- Eski `data/uniasist.db` uyumsuz → silinip taze kurulur.

### Erişim, kayıt, doğrulama

- Config: `AKADEMIK_ALAN_ADLARI = [".edu.tr", ".edu", ".ac.uk", ".edu.au"]`
  (env `UNIASIST_AKADEMIK_ALANLAR` ile genişletilebilir; virgülle ayrılmış).
- `kayitOl(adSoyad, eposta, sifre, sifreTekrar, universite="", bolum="")`:
  e-posta biçimi + akademik son ek kontrolü (IK-01, "yalnızca öğrenci e-postaları");
  üniversite/bölüm opsiyonel serbest metin; bölüm öneri listesi yalnızca UI'da datalist.
  Kayıt sonrası doğrulama e-postası (bugünkü token mekanizması aynen).
- Doğrulama kapısı: `dogrulanmisMi()` değilse sohbet/belge/ders/plan ekranları 302 ile
  doğrulama ekranına yönlenir (yönetici muaf). IK-35.
- E-posta benzersizliği büyük/küçük harfe duyarsız yapılır (epostaIleBul/epostaVarMi
  LOWER ile) — mevcut bilinen kusur, bu dönüşümde giderilir.

### Dersler ve paylaşım

- `DersDeposu`: `kaydet`, `adIleBul`, `idIleBul`, `hepsiniListele`, `ara(ad)`,
  `takipEt(kullanici_id, ders_id)`, `takibiBirak`, `kullanicininDersleri(kullanici_id)`,
  `dersinOgrencileri` gerekmez.
- Ders oluşturma: belge yüklerken veya Dersler ekranında serbest metin; varsa mevcut
  ders eşleşir (ad trim + case-insensitive benzersizlik), yoksa oluşturulur.
- Ders etiketi: OZEL belgede opsiyonel (kendi organizasyonu için); **PAYLASILAN belge
  ders ister** (derssiz paylaşılan belge kimselere görünmez — anlamsız). Ders,
  `belgeGuncelle` ile değiştirilebilir.
- Paylaşım kuralı: `belgeYukle(..., gorunurluk=PAYLASILAN)` ve
  `gorunurlukDegistir(..., PAYLASILAN)` yalnız PRO planda (IK-36). Ücretsiz plan OZEL
  yükler; paylaşılan bir belgeyi OZEL'e geri çevirmek her planda serbesttir.
- Pro→Ücretsiz dönüşte mevcut PAYLASILAN belgeler paylaşılmaya devam eder (veri yok
  edilmez); yalnız yeni paylaşım engellenir.
- Paylaşım görünürlüğü: `PAYLASILAN` belge, o dersi takip eden herkese görünür
  (liste, RAG kapsamı, `/kaynak/<id>`).
- `Kapsam(kullanici_id, ders_ids: set)`; `parcaErisilebilirMi`: `sahip_id == kullanici_id`
  VEYA (`PAYLASILAN` ve `ders_id in ders_ids`).
- Bildir (moderasyon): yalnız kullanıcının erişebildiği paylaşılan belgeler bildirilebilir
  (mevcut kapsam kuralının ders versiyonu).

### Plan ve kotalar

- `PlanServisi(kullanici_deposu, soru_kaydi_deposu, bilgi_kaynagi_deposu)`:
  - `haklar(kullanici) -> {plan, belge_sayisi, belge_limiti, bugunku_soru, gunluk_limit}`
  - `soruHakkiVarMi(kullanici)` (UCRETSIZ: bugünkü soru < 10)
  - `belgeHakkiVarMi(kullanici)` (UCRETSIZ: sahip belge sayısı < 3)
  - `proYap(kullanici)`, `ucretsizeDon(kullanici)` (self-servis; YONETICI hariç)
- İş kuralları: **IK-33** günlük soru limiti, **IK-34** belge limiti, **IK-35** doğrulama,
  **IK-36** paylaşım Pro gerektirir.
- Kota kontrol noktaları: `SohbetServisi.soruSorAkis` başında (IK-33);
  `BilgiTabaniServisi.belgeYukle` içinde (IK-34).
- Günlük sayım: `soru_kaydi` tablosundan `kullanici_id` + gün bazlı COUNT (yerel tarih).

### Sohbet

- `SohbetServisi`: `KAPSAM_ANAHTAR_SOZCUKLERI`, `KARA_LISTE`, `_kapsamIcindeMi` kaldırılır;
  her geçerli soru işlenir. `_kapsamiKur` → kullanıcının ders_ids kümesiyle `Kapsam`.
- `YanitUretmeServisi.yanitUretAkis`: eşik altı/parça yoksa artık sabit metin dönmez;
  LLM'e **boş bağlamla** gider (doğal sohbet). Sistem talimatı yenilenir: "UniAsist bir
  öğrenci çalışma asistanıdır; VERİLEN BELGE PARÇALARI ilgiliyse onlara dayan ve belirt;
  parçalar yoksa genel bilgiyle doğal biçimde yardımcı ol; **öğrencinin kendi
  materyallerine dair spesifik bir soru sorulduysa ve verilen parçalar bunu
  içermiyorsa yanıt olarak yalnızca `BILGI_YOK` yaz** (uydurma); kişisel veri isteme;
  Türkçe yanıt ver." (BILGI_YOK bekçisi `ICERIK_BULUNAMADI` ve yönetici
  "yanıtlanamayan soru" analitiğini beslemeye devam eder.)
- `ICERIK_BULUNAMADI` yalnızca model açıkça BILGI_YOK işaretlerse; `BILGI_YOK_METNI`
  ürüne uygun yeni metinle değiştirilir (Öğrenci İşleri yönlendirmesi kaldırılır).
- Yerel mod (`YerelAramaServisi`) geliştirme yedeği olarak kalır; kalıp yanıt üretmesi
  kabul edilir, UI'da "Yerel mod" rozeti bunu belirtir. Uçtan uca doğrulama API
  anahtarıyla yapılır.
- Kaynakça UI: SSE `sonuc` olayındaki `kaynaklar` yalnızca yanıt balonunun altındaki
  "Kaynakçalar" düğmesine bağlanır; tıklamada liste açılır/kapanır. Geçmiş yüklerken de
  aynı bileşen. Kaynak yoksa düğme hiç görünmez.

### Ekranlar ve rotalar

| Ekran | Rota | Kim |
|---|---|---|
| Tanıtım | `GET /` | herkese açık; girişliysa `/sohbet`e yönlenir |
| Sohbet | `/sohbet`, `POST /sohbet/yanit` (SSE), `/sohbet/yeni`, `/sohbet/<id>/sil`, `/sohbet/<id>/ad` | doğrulanmış |
| Belgelerim | `/belgelerim`, `/belgelerim/yukle`, `/<id>/gorunurluk`, `/<id>/sil`, `/<id>/guncelle`, `/<id>/bildir` | doğrulanmış |
| Dersler | `/dersler`, `/dersler/takip/<id>`, `/dersler/birak/<id>`, `GET /dersler/<id>` (dersin paylaşılan belgeleri + bildir) | doğrulanmış |
| Profil | `/profil` (GET/POST), `/profil/sifre` (POST) | girişli |
| Plan | `/plan`, `/plan/pro`, `/plan/ucretsiz` | doğrulanmış |
| Doğrulama | `/dogrula/<token>`, `POST /dogrulama/yeniden`, doğrulama kapı ekranı | girişli |
| Kaynak | `/kaynak/<id>` | doğrulanmış |
| Admin | mevcut `/yonetici/*` rotaları + kullanıcı listesinde plan sütunu | YONETICI |

- `/gecmis` sayfası kalkar; sohbet geçmişi sohbet ekranının sol paneline taşınır.
- `/sifre-degistir` rotası kalkar; Profil ekranında bölüm olur.
- Admin menüsü yalnız YONETICI rolünde görünür; öğrenci menüsü: Sohbet · Belgelerim ·
  Dersler · Plan · Profil.
- Giriş sonrası yönlendirme: her rol `/sohbet`e.

### Görsel sistem

- `statik/stil.css` sıfırdan: CSS custom properties (renk, boşluk, yarıçap, gölge,
  tipografi); `:root` açık, `html[data-tema="koyu"]` koyu palet.
- Vurgu: mavi→yeşil gradient (`#2563eb → #10b981` civarı) — birincil butonlar, hero,
  vurgu metinleri; düz renk alternatifleri token'da.
- Font: system stack (`-apple-system, "Segoe UI", Roboto, ...`) — harici bağımlılık yok.
- Tema: üst çubukta düğme; `localStorage` + `uniasist_tema` çerezi (ilk render'da flash
  olmaması için sunucu `data-tema`'yı çerezden okur); varsayılan sistem tercihi
  (`prefers-color-scheme`).
- Bileşen sınıfları yeniden adlandırılır (kart, buton, giriş, rozet, tablo, sohbet
  balonu, panel, mesaj); tüm şablonlar buna göre yeniden yazılır.
- Responsive: mobil öncelikli; sohbet paneli dar ekranda gizlenebilir.

### Seed ve değerlendirme

- Seed: 1 yönetici (`admin@universite.edu.tr / Yonetici1234`), 2 doğrulanmış öğrenci —
  `ali@universite.edu.tr / Ogrenci1234` **PRO** (OZEL + PAYLASILAN belgeler),
  `ayse@universite.edu.tr / Ogrenci1234` **ÜCRETSIZ** (yalnız OZEL belgeler; dersleri
  takip ederek Ali'nin paylaşımlarını görür); ortak dersler ("Matematik I",
  "Fizik I"); idempotent.
- Tanıtım sayfası fiyatlandırma bölümü: iki plan kartı (Ücretsiz/Pro karşılaştırması);
  Pro kartında fiyat yok, "Beta — ödeme yakında, şimdilik ücretsiz geçiş" notu.
- `degerlendir.py`: yeni Kapsam API'sine uyarlanır; yerel mod ≥%80 hedefi korunur.

## Kabul Kriterleri

1. Akademik olmayan e-posta ile kayıt reddedilir (IK-01); `@ogr.istanbul.edu.tr` kabul
   edilir (son ek eşleşmesi korunur).
2. Doğrulanmamış hesap sohbet/belge/ders/plan ekranlarına erişemez (IK-35).
3. Dersi takip etmeyen öğrenci o dersin paylaşılan belgesini listede, RAG sonucunda ve
   `/kaynak/<id>` ile göremez; takip eden görür; sahibi her zaman görür.
4. ÜCRETSIZ plan 4. belge yüklemede IK-34, 11. soruda IK-33 verir; PRO sınırsızdır.
   ÜCRETSIZ planda PAYLASILAN seçilemez (IK-36); PRO→ÜCRETSIZ dönüşte var olan
   paylaşımlar kalır.
5. `/plan/pro` self-servis Pro yapar; `/plan/ucretsiz` geri döndürür.
6. Kaynaklar yalnız "Kaynakçalar" açılır listesinde görünür; kaynak yoksa düğme yok.
7. İlk girişte tanıtım sayfası; girişli kullanıcı `/sohbet`e gider.
8. Tema tercihi kalıcı; açık ve koyu palet düzgün; gradient vurgu her iki temada okunur.
9. Menüde "Şifre Değiştir" yok; Profil ekranında üyelik bilgileri + şifre değiştirme var.
10. Tam süit yeşil; tüm kullanıcıya görünen metinler Türkçe.

## Yapımcıya Bırakılan Kararlar

- Gradient'in tam renk değerleri ve boşluk/yarıçap ölçüleri (token dosyasında tutulur).
- Ders öneri listesinin başlangıç içeriği (seed dersleri yeterli).
- Sohbet panelinde sohbet adlandırma etkileşiminin tam UX'i (satır içi düzenleme).
- `soru_kaydi` günlük sayımında saat dilimi: sunucu yerel tarihi.
- Admin kullanıcı listesinde plan değiştirme düğmesi eklenip eklenmeyeceği — eklenmez,
  self-servis yeterli (yapımcı kararı; gerekirse sonradan eklenir).
