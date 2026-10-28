# UniAsist SaaS Dönüşümü Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** UniAsist'i çok üniversiteli, öğrenci belge sahipliği/paylaşımı ve bölüm kapsamlı RAG içeren ücretsiz v1 SaaS'a dönüştürmek.

**Architecture:** Mevcut katmanlar korunur (entity → depo → servis → ekran, Flask + SQLite). Yeni kavramlar: üniversite/bölüm tabloları, e-posta doğrulama (token), belgeye sahiplik + görünürlük (OZEL/PAYLASILAN), arama/kaynak erişiminde kapsam izolasyonu, bildir/moderasyon. Personel rolü, SSS ve ziyaretçi sohbeti erken görevde kaldırılır ki sonraki imza değişiklikleri eskimiş kodu kırmasın.

**Tech Stack:** Python 3.13, Flask, sqlite3 (stdlib), pypdf, requests, pytest, smtplib (stdlib). Yeni bağımlılık YOK.

**Spec:** `docs/superpowers/specs/2026-10-28-uniasist-saas-design.md`

## Global Constraints

- Yeni bağımlılık eklenmez (requirements.txt değişmez).
- Şema değişiklikleri `uniasist/depo/veritabani.py` içindeki `_SEMA`'ya eklenir; eski yerel DB dosyaları silinip taze kurulur (`data/` git-ignore'lu).
- Metot/değişken adları mevcut stili izler (Türkçe-İngilizce karışık, camelCase metotlar).
- Kullanıcıya görünen metinler Türkçe; hata mesajları `IsKuraliIhlaliException(kural_no, mesaj)` ile.
- Yeni iş kuralı numaraları: **IK-29** (doğrulanmamış hesap paylaşamaz), **IK-30** (belge işlemleri yalnız sahibi), **IK-31** (bildirim: yalnız paylaşılan belge + öğrenci başına tek bildirim + kendi belgesi bildirilemez), **IK-32** (moderasyon yönetici yetkisi).
- Commit her görev sonunda `feat:`/`refactor:`/`fix:` önekli kısa Türkçe mesajla.
- Tam süit her görevin sonunda yeşil olmalı (`.venv\Scripts\python -m pytest -q`).

## Review Focus

1. **Başka bölümün öğrencisi paylaşılan belgeden RAG yanıtı alamaz** — ICERIK_BULUNAMADI dönmeli (Task 5 testi: `test_kapsam_baska_bolum_paylasilani_gormez`).
2. **`/kaynak/<id>` izolasyonu** — başka öğrencinin özel belgesi VE kendi üniversite/bölümü dışındaki paylaşılan belge URL ile görüntülenemez (Task 5 testi: `test_kaynak_rotasi_kapsam_disina_kapatilir`).
3. **Doğrulanmamış hesap paylaşamaz** — belge yükleyebilir ama PAYLASILAN seçemez/değiştiremez (Task 4 testi: `test_ik29_dogrulanmamis_paylasamaz`).
4. **Alan adı son ek eşleşmesi** — `@ogrenci.istanbul.edu.tr` kayıtlı `istanbul.edu.tr`'ye bağlanmalı; bilinmeyen alan adı kayıtta reddedilmeli (Task 1 testi: `test_alan_adi_son_ek_eslesmesi`).
5. **Token güvenliği** — süresi dolmuş veya kullanılmış token ile doğrulama reddedilmeli (Task 2 testleri: `test_dogrulama_sure_dolmus_token_red`, `test_dogrulama_token_tek_kullanim`).

---

### Task 1: Üniversite ve bölüm altyapısı

**Files:**
- Create: `uniasist/depo/universite_deposu.py`, `uniasist/veri/universiteler.py`, `uniasist/veri/bolumler.py`
- Modify: `uniasist/entity.py` (Universite sınıfı), `uniasist/depo/veritabani.py` (_SEMA)
- Test: `tests/test_universite.py`

**Interfaces:**
- Produces: `Universite(ad, eposta_alan_adi, universite_id=None)` entity; `UniversiteDeposu(db)` with `kaydet(universite)`, `hepsiniListele() -> list[Universite]`, `idIleBul(universite_id)`, `alanAdindanBul(eposta) -> Universite | None` (son ek eşleşmesi: e-posta alan adı `kayitli` ya da `.kayitli` ile biter), `bolumleriListele() -> list[str]`, `bolumEkle(ad)`; sabit listeler `uniasist.veri.universiteler.UNIVERSITELER: list[tuple[str, str]]` (≥25 Türkiye üniversitesi: (ad, alan adı) çiftleri; demo `("Üniversite", "universite.edu.tr")` dahil) ve `uniasist.veri.bolumler.BOLUMLER: list[str]` (≥30 standart bölüm adı).

- [ ] **Adım 1: Başarısız testleri yaz** (`tests/test_universite.py`)

```python
def test_alan_adi_son_ek_eslesmesi():      # @ogrenci.istanbul.edu.tr → İstanbul; @istanbul.edu.tr → aynı
def test_alan_adi_bilinmeyen_none_doner(): ...
def test_bolum_ekle_ve_listele(): ...
def test_seed_listeleri_dolu():            # UNIVERSITELER >= 25, BOLUMLER >= 30, adlar tekrarsız
```

- [ ] **Adım 2: Koş — FAIL** (modül yok). Run: `.venv\Scripts\python -m pytest tests/test_universite.py -v`
- [ ] **Adım 3: Gerçekleştirin** — `universite(id, ad, eposta_alan_adi UNIQUE)` ve `bolum(id, ad UNIQUE)` tablolarını `_SEMA`'ya ekle; `Universite` entity; `UniversiteDeposu`; veri modülleri (İstanbul, ODTÜ, Hacettepe, Boğaziçi, İTÜ, Ege, Gazi, Ankara, Marmara, Dokuz Eylül, YTÜ, Atatürk, Selçuk, Çukurova, Uludağ, Akdeniz, Erciyes, Kocaeli, Mimar Sinan, Gebze Teknik, Sabancı, Koç, Bilkent, Özyeğin, İstanbul Bilgi + "Üniversite"/universite.edu.tr demo kaydı; bölümler: Bilgisayar Mühendisliği, Elektrik-Elektronik Mühendisliği, Endüstri Mühendisliği, Makine Mühendisliği, İnşaat Mühendisliği, Kimya Mühendisliği, Mimarlık, Tıp, Hukuk, İşletme, Ekonomi, Psikoloji, Sosyoloji, Fizik, Kimya, Biyoloji, Matematik, İstatistik, Türk Dili ve Edebiyatı, Tarih, Felsefe, Hemşirelik, Eczacılık, Diş Hekimliği, Şehir ve Bölge Planlama, Uluslararası İlişkiler, Kamu Yönetimi, Muhasebe ve Finans, Turizm İşletmeciliği, Bilgi Sistemleri ve Teknolojileri).
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_universite.py -v`
- [ ] **Adım 5: Tam süit yeşil** (mevcut testlere dokunulmadı). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: universite ve bolum altyapisi`

---

### Task 2: Kayıt, bölüm seçimi ve e-posta doğrulama

**Files:**
- Create: `uniasist/eposta.py`
- Modify: `uniasist/entity.py` (Kullanici), `uniasist/depo/veritabani.py` (kullanici şeması), `uniasist/depo/kullanici_deposu.py`, `uniasist/servis/kimlik_dogrulama_servisi.py`, `uniasist/kurulum.py`, `config.py`
- Test: `tests/test_kimlik.py` (uyarlanır), `tests/test_eposta.py`

**Interfaces:**
- Consumes: Task 1 `UniversiteDeposu`.
- Produces: `Kullanici(..., universite_id=None, bolum="", eposta_dogrulandi=False, dogrulama_token=None, dogrulama_bitis=None)` + `dogrulanmisMi()`, `epostaDogrula()`, `dogrulamaTokenAta(token, bitis)`; `uniasist/eposta.py`: `IEpostaServisi` (ABC, `dogrulamaEpostasiGonder(eposta, ad_soyad, baglanti)`), `KonsolEpostaServisi` (logging), `SmtpEpostaServisi` (smtplib + config); `KimlikDogrulamaServisi(kullanici_deposu, universite_deposu, eposta_servisi)` with `kayitOl(adSoyad, eposta, sifre, sifreTekrar, bolum)`, `dogrulamaGonder(eposta)`, `dogrula(token) -> Kullanici`; `KullaniciDeposu.tokenIleBul(token)`; config: `UNIVERSITE_ALAN_ADI` SİLİNİR, `DOGRULAMA_SURESI_SAAT = 24`, `MAILGONDER` (env `UNIASIST_MAILGONDER`, varsayılan kapalı), `SMTP_SUNUCU`, `SMTP_PORT`, `SMTP_KULLANICI`, `SMTP_SIFRE`, `SMTP_GONDEREN`; `kur()` universite+bolum tabloları boşsa sabit listelerden seed eder; `KurulumPaketi`'ne `universite_deposu`, `eposta_servisi`. NOT: `Rol.PERSONEL` bu görevde durur (kaldırma Task 3'te).

- [ ] **Adım 1: Başarısız testleri yaz**

```python
# tests/test_kimlik.py (fixture'a universite_deposu + KonsolEpostaServisi eklenir)
def test_kayit_bolum_ve_universite_atanir():       # universite_id + bolum dolu, eposta_dogrulandi False, token üretilir
def test_kayit_bilinmeyen_alan_adi_reddedilir():   # IK-01, mesaj "henüz desteklenmiyor" içerir
def test_kayit_gecersiz_bolum_reddedilir():        # IK-01
def test_dogrula_token_ile_hesap_aktifleşir():     # eposta_dogrulandi True, token temizlenir
def test_dogrulama_sure_dolmus_token_red():        # bitiş geçmiş → IK-29
def test_dogrulama_token_tek_kullanim():           # ikinci dogrula(token) → IK-29
def test_dogrulama_gonder_yeniden():               # yeni token üretilir, eskisi geçersizleşir
# tests/test_eposta.py
def test_konsol_eposta_servisi_loglar():           # log kaydında bağlantı görünür (caplog)
def test_smtp_eposta_servisi_yapilir():            # smtplib.SMTP monkeypatch; sendmail çağrılır
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_kimlik.py tests/test_eposta.py -v`
- [ ] **Adım 3: Gerçekleştirin** — Kullanici alanları/metotları; kullanici tablosuna `universite_id, bolum, eposta_dogrulandi, dogrulama_token, dogrulama_bitis` sütunları; KullaniciDeposu eşleme + `tokenIleBul`; eposta modülü; kayitOl: `universite_deposu.alanAdindanBul(eposta)` (None → IK-01 "Üniversiteniz henüz desteklenmiyor."), bolum `bolumleriListele()` içinde değil → IK-01, kayıt sonrası `uuid4().hex` token + 24 saat bitiş + e-posta gönder; `dogrula(token)`: tokenIleBul → bitiş kontrolü → `epostaDogrula()` + kaydet; config + kurulum güncelle.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_kimlik.py tests/test_eposta.py -v`
- [ ] **Adım 5: Tam süit** (kayıt çağıran tüm testlere bolum parametresi eklenir). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: kayitta bolum secimi ve e-posta dogrulama`

---

### Task 3: Kaldırmalar (personel, SSS, ziyaretçi)

**Files:**
- Delete: `uniasist/ekran/belgeyonetim.py`, `sablonlar/belgeler.html`, `sablonlar/sss_ekle.html`, `sablonlar/anasayfa.html`, `tests/test_ekran_personel.py`
- Modify: `uniasist/entity.py` (SSSGirdisi, Sohbet.ziyaretci_oturum_id/kaliciMi), `uniasist/enumlar.py` (Rol.PERSONEL çıkar), `uniasist/depo/veritabani.py` (şemadan ziyaretci_oturum_id + soru/cevap sütunları), `uniasist/depo/bilgi_kaynagi_deposu.py` (SSS kolları), `uniasist/depo/sohbet_deposu.py` (ziyaretci), `uniasist/servis/bilgi_tabani_servisi.py` (sssEkle), `uniasist/servis/sohbet_servisi.py` (ziyaretci_sohbetleri, yeniSohbetBaslat ziyaretci kolu), `uniasist/servis/kullanici_yonetim_servisi.py` (PERSONEL), `uniasist/ekran/sohbet.py` (ziyaretci kolları), `uniasist/ekran/kullaniciyonetimi.py` (PERSONEL), `uniasist/uygulama.py`, `sablonlar/temel.html`, `uniasist/seed.py` (SSS)
- Test: ziyaretçi/SSS/personel test durumlarının silinmesi; kalanların uyumlanması

**Interfaces:**
- Produces: `Sohbet(kullanici_id zorunlu)`; `yeniSohbetBaslat(kullanici)` tek imza; şemada `sohbet.ziyaretci_oturum_id` ve `bilgi_kaynagi.soru/cevap` yok; kod/şablon/seed'de `PERSONEL`, `SSS`, `ziyaretci` referansı kalmaz (grep ile doğrulanır). Rol değiştirme artık yalnız OGRENCI↔YONETICI arasıdır (`test_uc21_rol_degistirme` uyumlanır).

- [ ] **Adım 1: Kırılacak testleri belirle** — ziyaretçi durumları (`test_ekran_sohbet.py` `test_fr06_*`, `test_sohbet.py` ziyaretçi kolları), SSS durumları (`test_bilgitabani.py`, `test_entity.py`, `test_seed.py` SSS bölümleri), `tests/test_ekran_personel.py` komple, `test_uc21_rol_degistirme` (PERSONEL → OGRENCI hedefine çevrilir).
- [ ] **Adım 2: Kodu kaldır** — Delete/Modify listesi; `uygulama.py` blueprint kayıtları ve `temel.html` menü referansları temizlenir; grep doğrulaması: `PERSONEL`, `SSS`, `ziyaretci` (kod + şablon) sıfır referans.
- [ ] **Adım 3: Tam süit yeşil.** Run: `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 4: Commit** — `refactor: personel, sss ve ziyaretci akislarini kaldir`

---

### Task 4: Belge sahipliği ve görünürlük

**Files:**
- Modify: `uniasist/enumlar.py` (Gorunurluk), `uniasist/entity.py` (Belge, IcerikParcasi), `uniasist/depo/veritabani.py` (şema), `uniasist/depo/bilgi_kaynagi_deposu.py`, `uniasist/servis/bilgi_tabani_servisi.py`, `uniasist/servis/belge_isleme_servisi.py`, `uniasist/servis/arama_dizini.py`
- Test: `tests/test_bilgitabani.py` (uyarlanır)

**Interfaces:**
- Produces: `enumlar.Gorunurluk{OZEL, PAYLASILAN}`; `Belge(..., sahip_id=None, gorunurluk=Gorunurluk.OZEL, universite_id=None, bolum="")`; `IcerikParcasi(..., sahip_id=None, gorunurluk=Gorunurluk.OZEL, universite_id=None, bolum="")`; `BilgiTabaniServisi.belgeYukle(dosya_adi, dosya_yolu, boyut_byte, baslik, kategori, sahip, gorunurluk=Gorunurluk.OZEL)` (sahibin universite_id/bolum'u belgeye kopyalanır; PAYLASILAN + doğrulanmamış sahip → IK-29), `belgeGuncelle(belge_id, kullanici_id, baslik, kategori, yeni_dosya_yolu=None, yeni_dosya_adi=None, yeni_boyut_byte=None)` (başkasının belgesi → IK-30), `belgeSil(belge_id, kullanici_id)` (IK-30), `belgeSilZorla(belge_id)` (moderasyon), `gorunurlukDegistir(belge_id, kullanici_id, gorunurluk)` (IK-30; PAYLASILAN + doğrulanmamış → IK-29; parçaların görünürlüğü güncellenir), `belgeleriListele(kullanici_id)`, `bolumunPaylasilanlari(universite_id, bolum)`; `BilgiKaynagiDeposu.sahibinBelgeleri(kullanici_id)`, `bolumunPaylasilanlari(universite_id, bolum)`; `AramaDizini.gorunurlukGuncelle(kaynak_id, gorunurluk)`.

- [ ] **Adım 1: Başarısız testleri yaz** (fixture'a doğrulanmış öğrenci kullanıcı eklenir; mevcut `belgeYukle` çağrılarına `sahip` eklenir)

```python
def test_belge_sahiplik_alanlari_atanir():           # sahip_id/universite_id/bolum dolu, gorunurluk OZEL
def test_ik29_dogrulanmamis_paylasamaz():            # PAYLASILAN + doğrulanmamış → IK-29; OZEL yükler
def test_ik30_baskasi_belgeyi_guncelleyemez():       # → IK-30
def test_ik30_baskasi_belgeyi_silemez():             # → IK-30
def test_gorunurluk_degisimi_parcalara_yansir():     # OZEL→PAYLASILAN → parçalar PAYLASILAN
def test_ik29_dogrulanmamis_gorunurluk_degistiremez(): ...
def test_bolumun_paylasilanlari_listeler():          # aynı üniv+bölüm PAYLASILAN görünür; OZEL ve başka bölüm görünmez
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_bilgitabani.py -v`
- [ ] **Adım 3: Gerçekleştirin** — `bilgi_kaynagi` ve `icerik_parcasi` tablolarına `sahip_id INTEGER, gorunurluk TEXT DEFAULT 'OZEL', universite_id INTEGER, bolum TEXT`; entity/depo eşlemeleri; `isleVeIndeksle` parçalara sahiplik/görünürlük kopyalar; servis imzaları yukarıdaki gibi.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_bilgitabani.py -v`
- [ ] **Adım 5: Tam süit** (test_seed/test_rag/test_ekran_* belgeYukle çağrıları uyumlanır — `sahip` parametresi). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: belge sahipligi ve gorunurluk`

---

### Task 5: Arama kapsamı ve kaynak görüntüleme izolasyonu

**Files:**
- Modify: `uniasist/dto.py` (Kapsam), `uniasist/servis/arama_dizini.py`, `uniasist/servis/yanit_uretme_servisi.py`, `uniasist/servis/sohbet_servisi.py`, `uniasist/ekran/sohbet.py`, `uniasist/kurulum.py`
- Test: `tests/test_rag.py` (uyarlanır), `tests/test_sohbet.py` (uyarlanır)

**Interfaces:**
- Consumes: Task 4 parça sahiplik alanları.
- Produces: `dto.Kapsam(kullanici_id, universite_id, bolum)`; `AramaDizini.enYakinParcalar(sorgu_gommesi, adet, kapsam=None)` (kapsam None → tüm parçalar — degerlendir.py ve test araçları; doluysa: `p.sahip_id == kapsam.kullanici_id or (p.gorunurluk == Gorunurluk.PAYLASILAN and p.universite_id == kapsam.universite_id and p.bolum == kapsam.bolum)`); `YanitUretmeServisi.yanitUretAkis(soru_metni, baglam, kapsam=None)`; `SohbetServisi` ctor'a `kullanici_deposu` eklenir (kurulum bağlar), `soruSorAkis` sohbetin kullanıcısından Kapsam kurar, `kaynagiGoruntule(referans, kullanici)` kapsam kontrolü yapar (sahibin belgesi YA DA PAYLASILAN + aynı üniversite + aynı bölüm; değilse None).

- [ ] **Adım 1: Başarısız testleri yaz** (aynı üniversite, farklı bölüm iki öğrenci; biri belgeyi PAYLASILAN yükler)

```python
def test_kapsam_kendi_belgesinden_yanit_alir():      # sahip → YANIT
def test_kapsam_ayni_bolum_paylasilani_gorur():      # aynı bölüm diğer öğrenci → YANIT + kaynak
def test_kapsam_baska_bolum_paylasilani_gormez():    # başka bölüm → ICERIK_BULUNAMADI
def test_kaynak_rotasi_kapsam_disina_kapatilir():    # kaynagiGoruntule: başka bölüm → None; sahibi → belge; aynı bölüm paylaşılan → belge
def test_kapsam_none_tum_parcalar():                 # kapsam=None → eski davranış
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_rag.py tests/test_sohbet.py -v`
- [ ] **Adım 3: Gerçekleştirin** — Kapsam DTO; dizin filtresi; yanitUretAkis kapsam parametresi; soruSorAkis Kapsam kurar; kaynagiGoruntule kontrol; `ekran/sohbet.py kaynak_ac` `g.aktif_kullanici` geçirir.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_rag.py tests/test_sohbet.py -v`
- [ ] **Adım 5: Tam süit.** `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: arama ve kaynak erisiminde kapsam izolasyonu`

---

### Task 6: Bildir ve moderasyon servisi

**Files:**
- Create: `uniasist/depo/bildirim_deposu.py`, `uniasist/servis/moderasyon_servisi.py`
- Modify: `uniasist/entity.py` (Bildirim), `uniasist/depo/veritabani.py` (bildirim tablosu), `uniasist/kurulum.py`
- Test: `tests/test_moderasyon.py`

**Interfaces:**
- Consumes: Task 4 `BilgiTabaniServisi` (belgeSilZorla, bolumunPaylasilanlari).
- Produces: `Bildirim(bildirim_id=None, belge_id, bildiren_id, neden, durum=KayitDurumu.ACIK, tarih)` entity; `BildirimDeposu(db)` with `kaydet`, `idIleBul`, `aciklariListele()`, `degerlendirildiIsaretle(bildirim_id)`, `belgeVeKisiyeGoreBul(belge_id, bildiren_id)`; `ModerasyonServisi(bildirim_deposu, bilgi_tabani_servisi)` with `bildir(belge_id, bildiren: Kullanici, neden)` (paylaşılan değil / zaten bildirilmiş / kendi belgesi → IK-31), `acikBildirimler() -> list[(bildirim, belge)]` (belgesi silinmişse atlar), `bildirimiDegerlendir(bildirim_id, silinsin: bool)` (silinsin → `belgeSilZorla`; her durumda bildirim DEGERLENDIRILDI); `KurulumPaketi.moderasyon`.

- [ ] **Adım 1: Başarısız testleri yaz**

```python
def test_bildir_paylasilan_belge():              # açık bildirim oluşur
def test_ik31_paylasilmayan_belge_bildirilemez(): ...
def test_ik31_ayni_kisi_tek_bildirim(): ...
def test_ik31_kendi_belgesi_bildirilemez(): ...
def test_degerlendir_sil():                     # belge + parçalar gider, bildirim DEGERLENDIRILDI
def test_degerlendir_yoksay():                  # belge kalır, bildirim DEGERLENDIRILDI
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_moderasyon.py -v`
- [ ] **Adım 3: Gerçekleştirin** — `bildirim` tablosu `UNIQUE(belge_id, bildiren_id)`; entity + depo + servis + kurulum.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_moderasyon.py -v`
- [ ] **Adım 5: Tam süit.** `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: bildirim ve moderasyon servisi`

---

### Task 7: Öğrenci ekranları (belgelerim, kayıt, doğrulama)

**Files:**
- Create: `uniasist/ekran/belgelerim.py`, `sablonlar/belgelerim.html`, `sablonlar/dogrulama.html`
- Modify: `uniasist/ekran/giris.py`, `uniasist/ekran/sohbet.py` (`/` kayıtsıza yönlendirme), `uniasist/uygulama.py`, `sablonlar/giris.html`, `sablonlar/kayit.html`, `sablonlar/temel.html`
- Test: `tests/test_ekran_ogrenci.py`

**Interfaces:**
- Consumes: Task 2 (kayitOl/dogrula/dogrulamaGonder), Task 4 (belge işlemleri), Task 6 (bildir).
- Produces: `belgelerim_bp`: `GET /belgelerim` (`?sekme=bolum` → bölümün paylaşılanları; varsayılan kendi belgeleri), `POST /belgelerim/yukle` (form: baslik, kategori, dosya, `paylas` checkbox), `POST /belgelerim/<id>/gorunurluk`, `POST /belgelerim/<id>/sil`, `POST /belgelerim/<id>/guncelle`, `POST /belgelerim/<id>/bildir` (yalnız paylaşılan); `giris_bp`'ye `GET /dogrula/<token>` ve `POST /dogrulama/yeniden`; `sohbet_sayfasi` kayıtsıza `/giris` yönlendirir; `temel.html` doğrulanmamış kullanıcıya banner.

- [ ] **Adım 1: Başarısız testleri yaz** (doğrulanmış öğrenci fixture'ı: kayıt + `epostaDogrula()`)

```python
def test_ogrenci_belge_yukler_ve_gorur():        # POST yükle → listede; sekme=bolum'de yok (OZEL)
def test_ogrenci_paylasir_bolum_gorur():         # gorunurluk POST → sekme=bolum'de görünür
def test_dogrulanmamis_paylas_hata():            # banner görünür; paylas POST → hata (IK-29)
def test_dogrulama_rotasi_token_ile():           # /dogrula/<token> → hesap doğrulanır, banner kalkar
def test_kayit_ekrani_bolum_listesi():           # GET /kayit → bölüm adları dropdown'da
def test_bolum_belgesi_bildir():                 # POST bildir → moderasyon acikBildirimler'de
def test_kayitsiz_anasayfa_girise_yonlendirir(): # GET / → 302 /giris
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_ogrenci.py -v`
- [ ] **Adım 3: Gerçekleştirin** — blueprint + şablonlar; dosya kaydetme `config.DOSYA_KLASORU` altına (eski `belgeyonetim.py`'nin `_dosya_kaydet` yaklaşımı geri getirilir); kayıt formunda `paket.universite_deposu.bolumleriListele()`; doğrulama akışı; `uygulama.py`'ye `belgelerim_bp` kaydı.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_ogrenci.py -v`
- [ ] **Adım 5: Tam süit** (test_ekran_giris.py kayıt akışı bolum alanıyla uyumlanır). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: ogrenci belge ekranlari ve dogrulama akisi`

---

### Task 8: Yönetici ekranları (üniversite/bölüm sütunları + moderasyon)

**Files:**
- Create: `sablonlar/bildirimler.html`
- Modify: `uniasist/ekran/kullaniciyonetimi.py`, `sablonlar/kullanicilar.html`, `sablonlar/temel.html`
- Test: `tests/test_ekran_yonetici.py` (uyarlanır)

**Interfaces:**
- Consumes: Task 6 `ModerasyonServisi`, Task 1 `UniversiteDeposu.idIleBul`.
- Produces: `GET /yonetici/bildirimler` (açık bildirimler: belge başlığı/sahibi/bildiren/neden/tarih), `POST /yonetici/bildirimler/<id>/karar` (`sil=1` → belge silinir; boş → yok sayılır; ikisi de listeye yönlendirir); `/yonetici/kullanicilar` satırlarında üniversite adı + bölüm.

- [ ] **Adım 1: Başarısız testleri yaz**

```python
def test_kullanicilar_universite_bolum_sutunu():   # listede üniversite adı ve bölüm görünür
def test_bildirimler_ekrani_ve_karar():            # GET listeler; POST karar sil=1 → belge gitti, liste boşalır
def test_bildirim_yoksay():                        # POST kararsız → belge durur, bildirim kapandı
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_yonetici.py -v`
- [ ] **Adım 3: Gerçekleştirin** — rotalar kullaniciyonetimi_bp'ye + şablon; kullanıcı listesi rotada `(kullanici, universite_adi)` demetlerine zenginleştirilir.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_yonetici.py -v`
- [ ] **Adım 5: Tam süit.** `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: yonetici ekranlarina universite, bolum ve moderasyon`

---

### Task 9: Seed, değerlendirme betiği, README ve uçtan uca doğrulama

**Files:**
- Modify: `uniasist/seed.py`, `degerlendir.py`, `README.md`
- Test: `tests/test_seed.py` (uyarlanır)

**Interfaces:**
- Produces: seed: 1 yönetici + aynı üniversiteden 2 farklı bölüm öğrencisi (doğrulanmış), öğrenci başına 1 OZEL + 1 PAYLASILAN belge; demo hesaplar `admin@universite.edu.tr / Yonetici1234`, `bilgisayar@universite.edu.tr / Ogrenci1234` (Bilgisayar Müh.), `elektrik@universite.edu.tr / Ogrenci1234` (Elektrik-Elektronik Müh.); `degerlendir.py` doğrulanmış öğrenciyle Kapsam kurup soruları işler (rapor kapsamı yazar); README: kayıt akışı, bölüm seçimi, doğrulama, demo hesaplar, SMTP/MAILGONDER değişkenleri.

- [ ] **Adım 1: test_seed.py uyarla** (yeni hesap/belge yapısı; idempotent korunur; paylaşılanlar bolumunPaylasilanlari'da).
- [ ] **Adım 2: Koş — FAIL → seed.py realize → PASS.** Run: `.venv\Scripts\python -m pytest tests/test_seed.py -v`
- [ ] **Adım 3: degerlendir.py uyarla + koş.** Run: `.venv\Scripts\python degerlendir.py` — Expected: 50 soru, oran ≥ %80 (yerel mod).
- [ ] **Adım 4: README güncelle.**
- [ ] **Adım 5: Tam süit.** `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Elle uçtan uca doğrulama** — `.venv\Scripts\python app.py`: kayıtsız `/` → /giris; kayıt (bölüm seçimi; doğrulama bağlantısı konsol logundan alınır ve tıklanır); belge yükle/paylaş; aynı bölüm paylaşılanı görürken başka bölüm göremez; sohbet + kaynak; bildir; yönetici moderasyon/kullanıcılar/rapor.
- [ ] **Adım 7: Commit** — `feat: saas seed, degerlendirme ve readme`

---
