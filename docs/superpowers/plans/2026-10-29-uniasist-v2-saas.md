# UniAsist v2 — Öğrenci SaaS Dönüşümü Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** UniAsist'i üniversite bazlı ders projesinden, öğrencilere abone satılan üniversiteden bağımsız bir AI çalışma asistanı SaaS'ına dönüştürmek.

**Architecture:** Mevcut katmanlı yapı korunur (entity → depo → servis → ekran, Flask + SQLite, sunucu tarafında render). Üniversite/bölüm izolasyonu kaldırılıp global ders bazlı takip modeli gelir; kullanıcıya plan (ÜCRETSIZ/PRO) eklenir; akademik e-posta kapısı + zorunlu doğrulama gelir; sohbet doğal LLM konuşmasına döner; tüm arayüz yeni tasarım sistemiyle (mavi→yeşil gradient, açık/koyu tema) yeniden yazılır.

**Tech Stack:** Python 3.13, Flask, sqlite3 (stdlib), pypdf, requests, pytest, smtplib. Yeni bağımlılık YOK.

**Spec:** `docs/superpowers/specs/2026-10-29-uniasist-saas-v2-design.md`

## Global Constraints

- Yeni pip/npm bağımlılığı eklenmez (requirements.txt değişmez).
- Şema değişiklikleri `uniasist/depo/veritabani.py` içindeki `_SEMA`'ya; eski `data/uniasist.db` silinip taze kurulur (`data/` git-ignore'lu).
- Katmanlı mimari korunur: entity → depo → servis → ekran. Metot adları mevcut stilde (camelCase, Türkçe-İngilizce karışık).
- Kullanıcıya görünen metinler Türkçe; iş kuralı ihlalleri `IsKuraliIhlaliException(kural_no, mesaj)` ile.
- Yeni iş kuralı numaraları: **IK-33** (günlük soru limiti), **IK-34** (belge limiti), **IK-35** (doğrulama zorunlu), **IK-36** (paylaşım Pro gerektirir). **IK-29** (eski doğrulanmamış paylaşım kuralı) ve kapsam filtresi **IK-15** kaldırılır.
- Commit her görev sonunda `feat:`/`refactor:`/`fix:` önekli kısa Türkçe mesajla.
- Tam süit her görevin sonunda yeşil olmalı (`.venv\Scripts\python -m pytest -q`).

## Review Focus

1. **Akademik e-posta kapısı** — `gmail.com` kayıtta reddedilir (IK-01); `@ogr.istanbul.edu.tr` kabul edilir (son ek eşleşmesi). Test: Task 4 `test_kayit_gmail_reddedilir`, `test_kayit_ogr_alt_alan_adi_kabul`.
2. **Doğrulama kapısı URL atlatma** — doğrulanmamış hesap `/sohbet`, `/belgelerim`, `/sohbet/yanit`, `/kaynak/<id>` URL'leriyle de erişemez; yönetici muaf (IK-35). Test: Task 5 `test_dogrulanmamis_url_ile_erezami_yapar`.
3. **Ders kapsamı izolasyonu** — takip edilmeyen dersin paylaşılan belgesi RAG sonucunda ve `/kaynak/<id>` ile görünmez; takip eden görür; sahibi her zaman görür. Test: Task 3 `test_kapsam_takip_etmedigi_dersi_gormez`, `test_kaynak_rotasi_ders_izolasyonu`.
4. **Kota ve plan geçişleri** — ÜCRETSIZ 11. soruda IK-33, 4. belgede IK-34, PAYLASILAN'da IK-36 alır; PRO sınırsız; Pro→Ücretsiz dönüşte var olan paylaşımlar kalır. Test: Task 6 `test_ik33_gunluk_soru_limiti`, `test_ik34_belge_limiti`, `test_ik36_ucretsiz_paylasamaz`, `test_prodan_donusumde_paylasim_kalir`.
5. **Kaynakça gizliliği** — kaynak kullanan yanıtta yalnız "Kaynakçalar" düğmesi görünür, tıklanınca liste açılır; kaynaksız yanıtta düğme hiç yoktur. Test: Task 12 `test_kaynakca_yalniz_dugmeyle_gorunur`.

---

### Task 1: Ders ve plan çekirdeği

**Files:**
- Create: `uniasist/depo/ders_deposu.py`, `tests/test_ders.py`
- Modify: `uniasist/enumlar.py` (Plan), `uniasist/entity.py` (Ders, Kullanici.plan, SoruKaydi.kullanici_id), `uniasist/depo/veritabani.py` (_SEMA: `ders`, `kullanici_ders`; `kullanici.plan`; `soru_kaydi.kullanici_id`), `uniasist/depo/kullanici_deposu.py` (plan eşleme), `uniasist/depo/soru_kaydi_deposu.py` (kullanici_id eşleme)

**Interfaces:**
- Produces: `enumlar.Plan{UCRETSIZ, PRO}`; `Ders(ders_id=None, ad="")` entity; `DersDeposu(db)` with `bulVeYaOlustur(ad) -> Ders` (ad strip + case-insensitive benzersizlik; varsa mevcudu döner), `adIleBul(ad) -> Ders | None`, `idIleBul(ders_id)`, `hepsiniListele() -> list[Ders]` (ad sıralı), `ara(ad) -> list[Ders]` (LIKE, ad ve ders_id'ye göre), `takipEt(kullanici_id, ders_id)`, `takibiBirak(kullanici_id, ders_id)`, `kullanicininDersleri(kullanici_id) -> list[Ders]`, `kullanicininDersIdleri(kullanici_id) -> set[int]`, `takipteMi(kullanici_id, ders_id) -> bool`; `Kullanici(..., plan=Plan.UCRETSIZ)` + `proMu() -> bool`; `SoruKaydi(zaman, kategori=None, yanitlandi=False, kullanici_id=None, kayit_id=None)`.

- [ ] **Adım 1: Başarısız testleri yaz** (`tests/test_ders.py`)

```python
def test_ders_bul_veya_olustur():          # iki çağrı aynı ders_id; ad trim edilir
def test_ders_ad_eslesmesi_harf_duyarsiz():  # adIleBul("matematik i") → "Matematik I"
def test_ders_takip_et_ve_birak():         # takipteMi, kullanicininDersIdleri, takibiBirak
def test_ders_ara():                       # "mat" → Matematik I listelenir
def test_kullanici_plan_varsayilan_ucrtsiz():  # kaydet → plan UCRETSIZ; proMu False
def test_soru_kaydi_kullanici_id_kalici():     # kaydet → okunur
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_ders.py -v`
- [ ] **Adım 3: Gerçekleştirin** — enum, entity, `_SEMA` (yalnızca eklemeler: `ders`, `kullanici_ders (kullanici_id, ders_id, UNIQUE(kullanici_id, ders_id))`, `kullanici.plan TEXT NOT NULL DEFAULT 'UCRETSIZ'`, `soru_kaydi.kullanici_id INTEGER`), depolar. Var olan tablo/kod dokunulmaz (additive).
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_ders.py -v`
- [ ] **Adım 5: Tam süit yeşil.** `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: ders ve plan cekirdegi`

---

### Task 2: Belgeye ders etiketi

**Files:**
- Modify: `uniasist/entity.py` (Belge.ders_id, IcerikParcasi.ders_id), `uniasist/depo/veritabani.py` (bilgi_kaynagi + icerik_parcasa `ders_id INTEGER`), `uniasist/depo/bilgi_kaynagi_deposu.py` (eşleme + `dersinPaylasilanlari(ders_id)`), `uniasist/servis/arama_dizini.py` (parça eşleme + `dersGuncelle(kaynak_id, ders_id)`), `uniasist/servis/bilgi_tabani_servisi.py`, `uniasist/servis/belge_isleme_servisi.py` (parçalara ders_id kopyalar), `uniasist/kurulum.py` (BilgiTabaniServisi'ne ders_deposu bağlanır)
- Test: `tests/test_bilgitabani.py` (uyarlanır)

**Interfaces:**
- Consumes: Task 1 `DersDeposu.bulVeYaOlustur`.
- Produces: `BilgiTabaniServisi(bilgi_kaynagi_deposu, belge_isleme_servisi, arama_dizini, ders_deposu=None)`; `belgeYukle(dosya_adi, dosya_yolu, boyut_byte, baslik, kategori, sahip, gorunurluk=Gorunurluk.OZEL, ders_adi="")` — ders_adi doluysa `bulVeYaOlustur`, belge ve parçalara `ders_id` yazılır; `gorunurluk == PAYLASILAN and not ders_adi` → IK-24 "Paylaşmak için bir ders seçmelisiniz."; `belgeGuncelle(..., yeni_ders_adi=None)` (belge + `arama_dizini.dersGuncelle`); `dersinPaylasilanlari(ders_id) -> list[Belge]`. `bolumunPaylasilanlari` bu görevde durur (Task 3'te silinir).

- [ ] **Adım 1: Başarısız testleri yaz**

```python
def test_belge_ders_etiketi_atanir():        # belgeYukle ders_adi → belge.ders_id + parçalara kopyalanır
def test_paylasilan_belge_ders_ister():      # PAYLASILAN + ders_adi yok → IK-24
def test_belge_ders_degistirilebilir():      # guncelle yeni_ders_adi → belge + parçalar yeni ders_id
def test_dersin_paylasilanlari_listeler():   # aynı ders PAYLASILAN görünür; başka ders ve OZEL görünmez
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_bilgitabani.py -v`
- [ ] **Adım 3: Gerçekleştirin** — şema/eşleme/depo/servis değişiklikleri; kurulum bağlantısı.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_bilgitabani.py -v`
- [ ] **Adım 5: Tam süit** — mevcut PAYLASILAN belge yükleyen testlere `ders_adi="Test Dersi"` eklenir (test_bilgitabani, test_moderasyon, test_ekran_ogrenci, test_ekran_yonetici, test_seed). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: belgeye ders etiketi`

---

### Task 3: Ders bazlı kapsam izolasyonu

**Files:**
- Modify: `uniasist/dto.py` (Kapsam), `uniasist/servis/sohbet_servisi.py`, `uniasist/servis/moderasyon_servisi.py`, `uniasist/depo/bilgi_kaynagi_deposu.py` (bolumunPaylasilanlari sil), `uniasist/servis/bilgi_tabani_servisi.py` (bolumunPaylasilanlari → dersinPaylasilanlari), `uniasist/kurulum.py` (SohbetServisi ve ModerasyonServisi'ne ders_deposu), `uniasist/ekran/belgelerim.py` + `sablonlar/belgelerim.html` (`?sekme=bolum` → `?sekme=ders&ders_id=<id>`; ders seçim linki Dersler ekranına — Task 8'de tam ekran gelir, burada minimal uyarlama)
- Test: `tests/test_rag.py`, `tests/test_sohbet.py`, `tests/test_moderasyon.py` (uyarlanır)

**Interfaces:**
- Consumes: Task 1 `kullanicininDersIdleri`, Task 2 parça `ders_id`.
- Produces: `Kapsam(kullanici_id, ders_ids)`; `parcaErisilebilirMi(parca)`: `parca.sahip_id == kullanici_id VEYA (PAYLASILAN ve parca.ders_id in ders_ids)`; `SohbetServisi(..., ders_deposu)` — `_kapsamiKur` → `Kapsam(kullanici_id, ders_deposu.kullanicininDersIdleri(...))`; `_kaynakErisilebilirMi(kaynak, kullanici)` aynı kural; `ModerasyonServisi(bildirim_deposu, bilgi_tabani_servisi, ders_deposu)` — `_bildirilebilirMi` aynı kural.

- [ ] **Adım 1: Başarısız testleri yaz** (test_rag/test_sohbet: iki öğrenci; A dersi takip ediyor, B değil; paylaşılan belge A'nın dersinde)

```python
def test_kapsam_takip_ettigi_dersin_paylasilanini_gorur():   # A → YANIT + kaynak
def test_kapsam_takip_etmedigi_dersi_gormez():               # B → ICERIK_BULUNAMADI
def test_kaynak_rotasi_ders_izolasyonu():                    # kaynagiGoruntule: B → None; A → belge; sahibi → belge
# test_moderasyon:
def test_ik31_takip_etmedigi_dersi_bildiremez():             # B → IK-31 "Belge bulunamadı."
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_rag.py tests/test_sohbet.py tests/test_moderasyon.py -v`
- [ ] **Adım 3: Gerçekleştirin** — Kapsam, servisler, kurulum, belgelerim ekranı minimum uyarlama.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_rag.py tests/test_sohbet.py tests/test_moderasyon.py -v`
- [ ] **Adım 5: Tam süit** (universite/bolum bazlı kapsam testleri ders bazlıya çevrilir). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: ders bazli kapsam izolasyonu`

---

### Task 4: Akademik e-posta kapısı ve üniversitenin kaldırılması

**Files:**
- Modify: `config.py` (`AKADEMIK_ALAN_ADLARI = [".edu.tr", ".edu", ".ac.uk", ".edu.au"]` + env `UNIASIST_AKADEMIK_ALANLAR`), `uniasist/entity.py` (Kullanici: `universite_id` → `universite=""`; Belge/IcerikParcasi: `universite_id`/`bolum` sil), `uniasist/depo/veritabani.py` (kullanici.universite TEXT; bilgi_kaynagi/icerik_parcasi'dan universite_id+bolum sil), `uniasist/depo/kullanici_deposu.py` (universite TEXT; `epostaIleBul`/`epostaVarMi`/`ara` LOWER ile), `uniasist/servis/kimlik_dogrulama_servisi.py` (kayitOl yeni imza; `_akademikMi(eposta)`), `uniasist/servis/bilgi_tabani_servisi.py`, `uniasist/servis/arama_dizini.py`, `uniasist/servis/belge_isleme_servisi.py` (kalan universite/bolum kopyaları silinir), `uniasist/ekran/giris.py` + `sablonlar/kayit.html` (universite + bolum serbest metin, bolum datalist `BOLUMLER`), `uniasist/ekran/kullaniciyonetimi.py` + `sablonlar/kullanicilar.html` (üniversite metni), `uniasist/kurulum.py` (temel_verileri_ekle ve universite_deposu kaldırılır; `KimlikDogrulamaServisi(kullanici_deposu, eposta_servisi)`), `uniasist/seed.py` (minimum uyarlama; tam seed Task 15)
- Delete: `uniasist/depo/universite_deposu.py`, `uniasist/veri/universiteler.py`, `tests/test_universite.py`
- Test: `tests/test_kimlik.py`, `tests/test_eposta.py`, `tests/test_ekran_giris.py`, `tests/test_ekran_yonetici.py` (uyarlanır); `veri/bolumler.py` kalır (öneri listesi)

**Interfaces:**
- Produces: `kayitOl(adSoyad, eposta, sifre, sifreTekrar, universite="", bolum="")` — `_akademikMi`: alan adı `config.AKADEMIK_ALAN_ADLARI` son eklerinden biriyle bitmiyorsa IK-01 "Kayıt yalnızca öğrenci e-posta adresleriyle yapılabilir (örn. .edu.tr)."; eposta `strip()` ile saklanır, benzersizlik/giriş LOWER ile; `Kullanici.universite` TEXT. Kod/şablonda `universite_id`, `UniversiteDeposu`, `UNIVERSITELER` referansı kalmaz (grep doğrulaması).

- [ ] **Adım 1: Başarısız testleri yaz** (test_kimlik.py)

```python
def test_kayit_gmail_reddedilir():            # ali@gmail.com → IK-01
def test_kayit_akademik_alan_kabul():         # ali@ogr.istanbul.edu.tr → OK (son ek .edu.tr)
def test_kayit_universite_bolum_opsiyonel():  # boş geçilebilir; doluysa kaydedilir
def test_kayit_eposta_harf_duyarsiz_benzersiz():  # Ali@x.edu.tr sonrası ali@x.edu.tr → IK-02
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_kimlik.py -v`
- [ ] **Adım 3: Gerçekleştirin** — config, servis, şema, depo, ekran, kurulum; grep doğrulaması: `universite_id|UniversiteDeposu|UNIVERSITELER|bolumleriListele|alanAdindanBul` sıfır referans (kod + şablon; testler hariç).
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_kimlik.py -v`
- [ ] **Adım 5: Tam süit** — kayitOl çağıran tüm testler yeni imzaya, universite_id kullanan tüm testler/fixture'lar `universite` metnine uyumlanır; test_universite.py silinir. `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `refactor: akademik e-posta kapisi ve universite kaldirma`

---

### Task 5: Zorunlu e-posta doğrulaması (IK-35)

**Files:**
- Modify: `uniasist/ekran/yardimcilar.py` (`dogrulama_required(roller=None)` dekoratörü), `uniasist/ekran/giris.py` (`GET /dogrulama-bekliyor`), `uniasist/ekran/sohbet.py` (tüm sohbet/kaynak rotaları), `uniasist/ekran/belgelerim.py` (tüm rotalar)
- Create: `sablonlar/dogrulama_bekliyor.html` (bilgi + tekrar gönder düğmesi; Task 10'da tasarım yenilenir)
- Test: `tests/test_ekran_ogrenci.py` (uyarlanır)

**Interfaces:**
- Produces: `dogrulama_required()` — `giris_required` + `g.aktif_kullanici.dogrulanmisMi()` değilse ve rol YONETICI değilse 302 `/dogrulama-bekliyor` (IK-35). Kapı: `/`, `/sohbet/yanit`, `/gecmis*`, `/kaynak/<id>`, `/belgelerim*`. Muaf: giriş/kayıt/doğrulama/profil rotaları ve YONETICI.

- [ ] **Adım 1: Başarısız testleri yaz**

```python
def test_dogrulanmamis_anasayfaya_erisemez():      # GET / → 302 /dogrulama-bekliyor
def test_dogrulanmamis_url_ile_erezami_yapar():    # /belgelerim, /sohbet/yanit, /kaynak/1 → 302
def test_dogrulanmis_erisir():                     # epostaDogrula sonrası / → 200
def test_yonetici_muaf():                          # doğrulanmamış YONETICI /belgelerim → 403 değil 200 (rol kuralı)
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_ogrenci.py -v`
- [ ] **Adım 3: Gerçekleştirin** — dekoratör + kapı rotası + rotalara uygulama.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_ogrenci.py -v`
- [ ] **Adım 5: Tam süit** (mevcut ekran testleri doğrulanmış kullanıcıyla çalışıyorsa uyarlama gerekmez). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: zorunlu e-posta dogrulamasi kapisi`

---

### Task 6: Plan servisi, kotalar ve plan ekranı

**Files:**
- Create: `uniasist/servis/plan_servisi.py`, `uniasist/ekran/plan.py`, `sablonlar/plan.html`, `tests/test_plan.py`
- Modify: `config.py` (`UCRETSIZ_GUNLUK_SORU = 10`, `UCRETSIZ_AZAMI_BELGE = 3`), `uniasist/depo/soru_kaydi_deposu.py` (`gunlukSoruSayisi(kullanici_id, gun=None) -> int`; gun = `date.today().isoformat()`, `zaman LIKE 'gun%'`), `uniasist/servis/sohbet_servisi.py` (+plan_servisi; soruSorAkis başında kota; SoruKaydi'ye kullanici_id), `uniasist/servis/bilgi_tabani_servisi.py` (belgeYukle IK-34; PAYLASILAN → IK-36; gorunurlukDegistir PAYLASILAN → IK-36; IK-29 kaldırılır), `uniasist/kurulum.py`, `uniasist/uygulama.py` (plan_bp)

**Interfaces:**
- Produces: `PlanServisi(kullanici_deposu, soru_kaydi_deposu, bilgi_kaynagi_deposu)`: `haklar(kullanici) -> dict` (anahtarlar: `plan`, `belge_sayisi`, `belge_limiti` (PRO'da None), `bugunku_soru`, `gunluk_limit` (PRO'da None)), `soruHakkiVarMi(kullanici) -> bool`, `belgeHakkiVarMi(kullanici) -> bool`, `proYap(kullanici)`, `ucretsizeDon(kullanici)` (YONETICI hariç). Rotalar: `GET /plan` (dogrulama_required), `POST /plan/pro`, `POST /plan/ucretsiz` → /plan yönlendirir. Kota mesajları: IK-33 "Günlük soru limitine ulaştınız (10). Sınırsız sohbet için Pro'ya geçin.", IK-34 "Ücretsiz planda en fazla 3 belge yükleyebilirsiniz. Daha fazlası için Pro'ya geçin.", IK-36 "Belge paylaşmak Pro özelliğidir."

- [ ] **Adım 1: Başarısız testleri yaz** (tests/test_plan.py)

```python
def test_haklar_ucrtsiz():                     # 10/3 limitler görünür
def test_ik33_gunluk_soru_limiti():            # 10 soru sonrası 11. → IK-33; PRO'da sınır yok
def test_ik34_belge_limiti():                  # 3 belge sonrası 4. → IK-34; PRO'da sınır yok
def test_ik36_ucretsiz_paylasamaz():           # UCRETSIZ + PAYLASILAN → IK-36 (yükleme ve görünürlük)
def test_proya_gecis_ve_donus():               # proYap → proMu; ucretsizeDon → UCRETSIZ
def test_prodan_donusumde_paylasim_kalir():    # PRO'da PAYLASILAN → ucretsizeDon → belge PAYLASILAN kalır
def test_plan_ekrani_ve_gecis():               # GET /plan görünür; POST /plan/pro → PRO
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_plan.py -v`
- [ ] **Adım 3: Gerçekleştirin** — servis, depo metodu, entegrasyonlar, ekran.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_plan.py -v`
- [ ] **Adım 5: Tam süit** (IK-29 testleri IK-36'ya çevrilir; PAYLASILAN kullanan fixture'lara PRO plan eklenir). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: plan servisi kotalar ve plan ekrani`

---

### Task 7: Doğal sohbet

**Files:**
- Modify: `uniasist/servis/sohbet_servisi.py` (KAPSAM_ANAHTAR_SOZCUKLERI, KARA_LISTE, `_kapsamIcindeMi` silinir; IK-15 yolu kalkar), `uniasist/servis/yanit_uretme_servisi.py` (eşik filtresi: `secilen = [s for s in sonuclar if s.skor >= benzerlik_esigi]`; boş olsa bile LLM çağrılır; BILGI_YOK bekçisi kalır), `uniasist/yapayzeka/hazir_llm_servisi.py` (SISTEM_TALIMATI yenilenir; `_istemler` parça yoksa "BELGE İÇERİĞİ" bölümü yazmaz), `config.py` (BILGI_YOK_METNI yeni: "Bu konuda materyallerinde bilgi bulamadım. İlgili belgeyi yüklersen bu konuda da yardımcı olabilirim."; KAPSAM_METNI ve BIRIM_ILETISIM silinir), `tests/yardimci.py` (SahteYZ: parçasız çağrıda doğal yanıt üretir)
- Test: `tests/test_rag.py`, `tests/test_sohbet.py` (uyarlanır)

**Interfaces:**
- Produces: `yanitUretAkis(soru_metni, baglam, kapsam=None)` — her geçerli soruda LLM çağrılır; parça eşik altıysa bağlam boş gider; yanıt kaynaksız da olabilir (`SonucDurumu.YANIT` + `kaynaklar=[]`); `ICERIK_BULUNAMADI` yalnızca model `BILGI_YOK` dönerse. Sistem talimatı: "UniAsist bir öğrenci çalışma asistanıdır; VERİLEN BELGE PARÇALARI ilgiliyse onlara dayan; parçalar yoksa genel bilgiyle doğal biçimde yardımcı ol; öğrencinin kendi materyallerine dair spesifik soruda parçalar yetersizse yalnızca 'BILGI_YOK' yaz; kişisel veri isteme; Türkçe yanıt ver."

- [ ] **Adım 1: Başarısız testleri yaz**

```python
def test_dogrulama_belge_disi_soru_doal_yanit():  # parça yok → YANIT (ICERIK_BULUNAMADI değil), kaynaklar boş
def test_bilgi_yok_bekcisi_kalir():               # model BILGI_YOK dönerse → ICERIK_BULUNAMADI + yeni metin
def test_kapsam_filtresi_kalkti():                # kara liste kelimesi ("futbol") bile yanıtlanır
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_rag.py tests/test_sohbet.py -v`
- [ ] **Adım 3: Gerçekleştirin** — servis + prompt + config + SahteYZ.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_rag.py tests/test_sohbet.py -v`
- [ ] **Adım 5: Tam süit** (IK-15 kapsam testleri silinir/uyarlanır). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: dogal sohbet akisi`

---

### Task 8: Dersler ekranı

**Files:**
- Create: `uniasist/ekran/dersler.py`, `sablonlar/dersler.html`, `sablonlar/ders.html`, `tests/test_ekran_dersler.py`
- Modify: `uniasist/uygulama.py` (dersler_bp), `sablonlar/temel.html` (menüye "Dersler")

**Interfaces:**
- Produces: `GET /dersler` (arama `?q=`; ders listesi + takip durumu + "Ders ekle" formu), `POST /dersler` (`ad` → `bulVeYaOlustur` + takip), `GET /dersler/<id>` (dersin paylaşılan belgeleri + bildir formu; sadece takip edenler görür, değilse uyarı), `POST /dersler/<id>/takip`, `POST /dersler/<id>/birak` (hepsi `dogrulama_required()`).

- [ ] **Adım 1: Başarısız testleri yaz**

```python
def test_dersler_listesi_ve_arama():         # GET /dersler → 200, ders adları; ?q= filtresi
def test_ders_takip_et_ve_birak():           # POST takip → dersin paylaşılanları görünür; birak → gizli
def test_yeni_ders_olusturma():              # POST /dersler "Fizik II" → listede + takipte
def test_ders_detayinda_paylasilanlar():     # PAYLASILAN belge görünür; OZEL görünmez; bildir formu var
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_dersler.py -v`
- [ ] **Adım 3: Gerçekleştirin** — blueprint + şablonlar.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_dersler.py -v`
- [ ] **Adım 5: Tam süit.** `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: dersler ekrani`

---

### Task 9: Profil ekranı

**Files:**
- Create: `uniasist/ekran/profil.py`, `sablonlar/profil.html`, `tests/test_ekran_profil.py`
- Modify: `uniasist/servis/kimlik_dogrulama_servisi.py` (`profilGuncelle(kullanici_id, ad_soyad, universite, bolum)` — ad_soyad boş → IK-01), `uniasist/ekran/giris.py` (`/sifre-degistir` rotası silinir; şifre değiştirme `/profil/sifre` olur), `sablonlar/temel.html` ("Şifre Değiştir" → "Profil"), `uniasist/uygulama.py` (profil_bp)

**Interfaces:**
- Produces: `GET /profil` (girişli; ad soyad, e-posta, doğrulama durumu, üniversite/bölüm, plan ve kullanım — PlanServisi.haklar), `POST /profil` (profilGuncelle), `POST /profil/sifre` (mevcut_sifre/yeni_sifre/yeni_sifre_tekrar → `kimlik.sifreDegistir`). `sifre.html` ve `/sifre-degistir` kalkar.

- [ ] **Adım 1: Başarısız testleri yaz**

```python
def test_profil_bilgileri_gorunur():         # ad, eposta, üniversite, plan, kalan haklar
def test_profil_guncelleme():                # POST → alanlar güncellenir; ad_soyad boş → hata
def test_profil_sifre_degistirme():          # POST /profil/sifre → yeni şifreyle giriş; yanlış mevcut → hata
def test_eski_sifre_rotasi_yok():            # GET /sifre-degistir → 404
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_profil.py -v`
- [ ] **Adım 3: Gerçekleştirin** — servis metodu + blueprint + şablon.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_profil.py -v`
- [ ] **Adım 5: Tam süit** (test_ekran_giris'deki /sifre-degistir testleri /profil/sifre'e taşınır). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: profil ekrani`

---

### Task 10: Tasarım sistemi, tema ve auth ekranları

**Files:**
- Rewrite: `statik/stil.css` (tasarım token'ları: `:root` açık + `html[data-tema="koyu"]` koyu palet; mavi→yeşil gradient `#2563eb → #10b981`; kart/buton/giriş/rozet/tablo/balon/panel bileşenleri; responsive), `sablonlar/temel.html` (yeni üst çubuk: gradient marka, menü, tema düğmesi; `data-tema="{{ tema }}"`), `sablonlar/giris.html`, `sablonlar/kayit.html`, `sablonlar/dogrulama.html`, `sablonlar/dogrulama_bekliyor.html`
- Create: `statik/tema.js` (düğme: `uniasist_tema` çerezi + `data-tema` değiştirme; çerez yoksa `prefers-color-scheme`)
- Modify: `uniasist/uygulama.py` (context processor: `tema` = çerezden, varsayılan "acik")
- Test: `tests/test_tema.py`

**Interfaces:**
- Produces: `tema` context değişkeni ("acik"/"koyu"); `<html data-tema>`; tema düğmesi id `tema-dugme`. CSS sınıf adları: `kart`, `buton`, `buton-birincil` (gradient), `giris`, `rozet`, `panel`, `balon`.

- [ ] **Adım 1: Başarısız testleri yaz** (tests/test_tema.py)

```python
def test_tema_varsayilan_acik():             # çerez yok → data-tema="acik"
def test_tema_cerezden_koyu():               # çerez koyu → data-tema="koyu"
def test_tema_dugme_var():                   # tüm sayfalarda id="tema-dugme"
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_tema.py -v`
- [ ] **Adım 3: Gerçekleştirin** — CSS, JS, şablonlar, context processor.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_tema.py -v`
- [ ] **Adım 5: Tam süit** (auth ekran testlerinde sınıf/metin uyumlaması). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: tasarim sistemi tema ve auth ekrani`

---

### Task 11: Tanıtım sayfası ve sohbet ana rotası

**Files:**
- Create: `sablonlar/tanitim.html` (hero gradient, özellik kartları, fiyatlandırma: Ücretsiz/Pro kartları — Pro'da fiyat yok, "Beta — ödeme yakında, şimdilik ücretsiz geçiş" notu; CTA: Ücretsiz Başla → /kayit, Giriş → /giris), `tests/test_ekran_tanitim.py`
- Modify: `uniasist/ekran/sohbet.py` (`/` → girişliyse 302 `/sohbet`, değilse tanıtım; sohbet_sayfasi rotası `/` → `/sohbet`), `uniasist/ekran/giris.py` (giriş sonrası her rol `/sohbet`e), `sablonlar/temel.html` (marka `href="/sohbet"`), `uniasist/ekran/sohbet.py` içindeki `/sohbet/yeni` hedefleri

**Interfaces:**
- Produces: `GET /` herkese açık tanıtım; `GET /sohbet` sohbet ekranı (dogrulama_required). Yönlendirme değişiklikleri: giriş → `/sohbet`; kayıtsız `/` → tanıtım (302 değil, 200).

- [ ] **Adım 1: Başarısız testleri yaz**

```python
def test_kayitsiz_anasayfa_tanitim():        # GET / → 200; "UniAsist", fiyat kartları, /kayit linki
def test_girisli_anasayfa_sohbete_yonlenir():  # GET / → 302 /sohbet
def test_giris_sonrasi_sohbete():            # POST /giris → Location /sohbet
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_tanitim.py -v`
- [ ] **Adım 3: Gerçekleştirin** — şablon + rota değişiklikleri (tüm `/` referansları güncellenir: sohbet.js, kaynak.html "Sohbete dön", temel.html).
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_tanitim.py -v`
- [ ] **Adım 5: Tam süit** (`/` bekleyen testler `/sohbet`e alınır). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: tanitim sayfasi ve sohbet ana rotasi`

---

### Task 12: Sohbet ekranı yeniden yazımı

**Files:**
- Rewrite: `sablonlar/sohbet.html` (sol panel: sohbet listesi + "Yeni Sohbet" + satır içi adlandırma + sil; ana alan: ders filtresi select, mesaj balonları, yazıyor, form), `statik/sohbet.js` (SSE + kaynakça render + panel + filtre)
- Modify: `uniasist/ekran/sohbet.py` (`/sohbet/yanit` forma `ders_id` alır; `POST /sohbet/<id>/ad` (`baslik`); `/gecmis*` rotaları ve `sablonlar/gecmis.html` silinir), `uniasist/servis/sohbet_servisi.py` (`soruSorAkis(sohbet, soru_metni, ders_id=None)` — ders_id verilmişse kapsam `Kapsam(kullanici_id, {ders_id})`; `sohbetAdlandir(sohbet_id, kullanici_id, baslik)`), `uniasist/kurulum.py`
- Test: `tests/test_ekran_sohbet.py` (uyarlanır)

**Interfaces:**
- Produces: kaynakça biçimi — yanıt balonunun altında `<button class="kaynakca-dugme">Kaynakçalar</button>` + gizli `<div class="kaynakca-liste">`; kaynak yoksa hiç render edilmez; canlı SSE ve geçmiş yüklemesi aynı yapıyı üretir. Rotalar: `/sohbet`, `POST /sohbet/yanit` (form: `soru`, `sohbet_id`, `ders_id`), `/sohbet/yeni`, `POST /sohbet/<id>/sil`, `POST /sohbet/<id>/ad`.

- [ ] **Adım 1: Başarısız testleri yaz** (test_ekran_sohbet.py)

```python
def test_kaynakca_yalniz_dugmeyle_gorunur():   # kaynaklı yanıt → "Kaynakçalar" düğmesi var, kaynak adı düğme dışında yok; kaynaksız → düğme de yok
def test_gecmis_paneli_sohbetlerde():          # /sohbet → sohbet başlıkları panelde
def test_sohbet_adlandirma():                  # POST /sohbet/<id>/ad → yeni başlık listede
def test_ders_filtresi():                      # soruSorAkis ders_id → yalnız o dersin paylaşılanı kapsamda
```

- [ ] **Adım 2: Koş — FAIL.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_sohbet.py -v`
- [ ] **Adım 3: Gerçekleştirin** — şablon + JS + rota + servis.
- [ ] **Adım 4: Koş — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_sohbet.py -v`
- [ ] **Adım 5: Tam süit** (/gecmis testleri silinir; panel testleri eklenir). `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Commit** — `feat: sohbet ekrani yeniden yazimi`

---

### Task 13: Öğrenci ekranlarının yeni tasarımı

**Files:**
- Rewrite: `sablonlar/belgelerim.html` (yükleme formu: başlık, kategori, ders — datalist; paylaş checkbox yalnız PRO'da etkin, ÜCRETSIZ'da disabled + "Pro" rozeti; belge tablosu: ders adı, görünürlük, kota göstergesi), `sablonlar/dersler.html`, `sablonlar/ders.html`, `sablonlar/profil.html`, `sablonlar/plan.html` (plan kartları + "Pro'ya Geç" düğmesi "beta — ödeme yakında" notuyla), `sablonlar/kaynak.html`
- Modify: `uniasist/ekran/belgelerim.py` (rota belgeleri `(belge, ders_adi)` olarak zenginleştirir; PRO bilgisi), ilgili ekran rotaları (haklar/ders verisi)
- Test: `tests/test_ekran_ogrenci.py`, `tests/test_ekran_dersler.py`, `tests/test_ekran_profil.py`, `tests/test_plan.py` (uyarlanır)

**Interfaces:**
- Produces: şablonlerde yeni sınıf adları (`kart`, `buton-birincil`, `rozet`, `panel`...); belgelerim rotası şablona `belgeler` yerine `satirlar` (belge + ders_adi demetleri), `plan_haklari` (PlanServisi.haklar), `plan_pro_mu` geçirir. Paylaş checkbox adı `paylas` kalır.

- [ ] **Adım 1: Testleri uyarla** — belgelerim kota göstergesi (`3 belgeden 2`), ÜCRETSIZ'da paylaş disabled, ders adı sütunu, plan ekranı notu; mevcut davranış testleri korunur.
- [ ] **Adım 2: Koş — FAIL → gerçekleştir — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_ogrenci.py tests/test_ekran_dersler.py tests/test_ekran_profil.py tests/test_plan.py -v`
- [ ] **Adım 3: Tam süit.** `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 4: Commit** — `feat: ogrenci ekrani yeni tasarim`

---

### Task 14: Admin ekranlarının yeni tasarımı ve menü düzeni

**Files:**
- Rewrite: `sablonlar/kullanicilar.html` (üniversite metin + plan sütunu), `sablonlar/bildirimler.html`, `sablonlar/rapor.html`, `sablonlar/yanitlanamayan.html`, `sablonlar/geribildirimler.html`
- Modify: `sablonlar/temel.html` (öğrenci menüsü: Sohbet · Belgelerim · Dersler · Plan · Profil; yönetici menüsü ayrı ve yalnız YONETICI'da görünür), `uniasist/ekran/kullaniciyonetimi.py` (satırlarda plan)
- Test: `tests/test_ekran_yonetici.py` (uyarlanır)

**Interfaces:**
- Produces: `/yonetici/kullanicilar` satırları `(kullanici, universite_metni, plan)`; menüde "Şifre Değiştir"/"Geçmiş" yok; yönetici menü öğeleri yalnız YONETICI'da render.

- [ ] **Adım 1: Testleri uyarla** — plan sütunu görünür; öğrenci görünümünde yönetici menüsü yok; yöneticide var.
- [ ] **Adım 2: Koş — FAIL → gerçekleştir — PASS.** Run: `.venv\Scripts\python -m pytest tests/test_ekran_yonetici.py -v`
- [ ] **Adım 3: Tam süit.** `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 4: Commit** — `feat: admin ekrani yeni tasarim`

---

### Task 15: Seed, değerlendirme, README ve uçtan uca doğrulama

**Files:**
- Modify: `uniasist/seed.py`, `degerlendir.py`, `README.md`, `tests/test_seed.py`

**Interfaces:**
- Produces: seed — `admin@universite.edu.tr / Yonetici1234` (YONETICI), `ali@universite.edu.tr / Ogrenci1234` (**PRO**; OZEL + PAYLASILAN belgeler), `ayse@universite.edu.tr / Ogrenci1234` (**UCRETSIZ**; yalnız OZEL; dersleri takip eder); dersler "Matematik I", "Fizik I"; idempotent. `degerlendir.py` kapsam=None ile 50 soru, oran ≥ %80 (yerel mod). README: ürün tanımı, akademik e-posta, kayıt/doğrulama akışı, dersler, planlar, demo hesaplar, tema, env değişkenleri (API anahtarı, `UNIASIST_AKADEMIK_ALANLAR`, `UNIASIST_TEMEL_URL`, SMTP/MAILGONDER).

- [ ] **Adım 1: test_seed.py uyarla** — hesap planları, ders etiketleri, Ayşe'nin takipleri, paylaşılanların `dersinPaylasilanlari`'da görünmesi; idempotent korunur.
- [ ] **Adım 2: Koş — FAIL → seed.py realize → PASS.** Run: `.venv\Scripts\python -m pytest tests/test_seed.py -v`
- [ ] **Adım 3: degerlendir.py uyarla + koş.** Run: `.venv\Scripts\python degerlendir.py` — Expected: 50 soru, oran ≥ %80 (yerel mod).
- [ ] **Adım 4: README güncelle.**
- [ ] **Adım 5: Tam süit.** `.venv\Scripts\python -m pytest -q`
- [ ] **Adım 6: Elle uçtan uca doğrulama** — `data/uniasist.db` silinip `.venv\Scripts\python app.py`: tanıtım → kayıt (gmail reddi, .edu.tr kabul, doğrulama bağlantısı logdan) → doğrulama kapısı → belge yükle (ders etiketi, ücretsiz kota) → soru sorma (kota, kaynakça düğmesi) → Pro'ya geç → paylaş → ikinci hesap ders takibi → paylaşılanı sohbet + kaynaktan görme → bildir → yönetici moderasyon → tema açık/koyu.
- [ ] **Adım 7: Commit** — `feat: v2 seed degerlendirme ve readme`
