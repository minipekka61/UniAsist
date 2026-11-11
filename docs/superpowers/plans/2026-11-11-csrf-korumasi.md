# CSRF Koruması Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** UniAsist'in tüm durum değiştiren POST isteklerini CSRF token'ı ile korumak, `/cikis`'i POST'a çevirmek ve çerezlere `SameSite=Lax` eklemek.

**Architecture:** Flask-WTF `CSRFProtect` uygulama fabrikasında (`uygulama_olustur`) başlatılır; tüm POST'lar varsayılan olarak korunur, hiçbir rota muaf tutulmaz. Token Flask'ın imzalı `session` çerezinde taşınır; şablonlarda `csrf_token()` (form gizli alanı) ve `csrf_meta_tag()` (meta etiketi) ile render edilir; JS `X-CSRFToken` başlığı ile gönderir. Mevcut davranış testleri CSRF'i kapalı fixture'larla çalışmaya devam eder; CSRF'in kendisi odaklı testlerle doğrulanır.

**Tech Stack:** Flask 3.1.3, Werkzeug 3.1.9, flask-wtf (yeni bağımlılık), pytest 9.1.1

**Spec:** `docs/superpowers/specs/2026-11-11-csrf-korumasi-design.md`

## Global Constraints

- Yeni bağımlılık `flask-wtf`, `requirements.txt`'ye sürüm sabitlenmeden eklenir (mevcut stil: flask, pypdf, requests, pytest).
- Commit mesajları mevcut stil: küçük harf Türkçe, `feat:`/`test:`/`docs:` öneki, nokta yok.
- Şablonlardaki sabit `action` yolları ve görünür UX değişmez (yalnız gizli alan eklenir).
- Mevcut 234 test yeşil kalmalı; her task sonunda tam suite: `.venv\Scripts\python -m pytest -q`.
- `SECRET_KEY` `config.py`'de zaten ayarlı; CSRF için ek config gerekmez.

## Review Focus

1. Geçersiz/imzası bozuk token değerli POST → 400 dönmeli, uygulama çökmemeli — Task 1 `test_gecersiz_token_400_doner`.
2. JSON gövdeli POST (`/geri-bildirim`) header'sız → 400 ve view ÇALIŞMAMALI (aynı 400'ü view hatası olarak da dönebildiği için JSON gövde ayrımı şart) — Task 2 `test_geri_bildirim_json_rotasi_korumali`.
3. Multipart dosya yükleme (belgelerim) token ile çalışmalı — form alanı mekanizması Task 1 `test_form_tokenu_kabul_edilir` ile pinlenir; Task 2'de manuel smoke ile uçtan uca doğrulanır.
4. Token süresi (varsayılan `WTF_CSRF_TIME_LIMIT` = 3600 sn) dolduğunda POST → 400 — bilinçli varsayılan, Task 5'te belgelenir.
5. Eski yer iminden GET `/cikis` → 405 — Task 3 `test_cikis_get_405`.

---

### Task 1: CSRFProtect çekirdeği

**Files:**
- Modify: `requirements.txt`
- Modify: `uniasist/uygulama.py` (`uygulama_olustur`, ~satır 35-37)
- Modify: `sablonlar/temel.html` (head, satır 5 sonrası)
- Create: `tests/test_csrf.py`
- Modify (her birine tek satır): `tests/test_ekran_dersler.py:22`, `tests/test_ekran_giris.py:27`, `tests/test_ekran_ogrenci.py:36`, `tests/test_ekran_profil.py:16`, `tests/test_ekran_sohbet.py:50`, `tests/test_ekran_tanitim.py:12`, `tests/test_ekran_yonetici.py:19`, `tests/test_plan.py:21`, `tests/test_tema.py:12`

**Interfaces:**
- Consumes: yok (ilk task).
- Produces: `uygulama_olustur` her çağrıda CSRFProtect başlatır; Jinja global'leri `csrf_token()` ve `csrf_meta_tag()` otomatik kayıtlı olur. `tests/test_csrf.py` fixture'ı `istemci` — DİKKAT: diğer test fixture'larının aksine `WTF_CSRF_ENABLED` AYARLANMAZ (CSRF açık kalır). Yardımcı `_token_al(istemci, yol="/giris")` — verilen sayfanın meta etiketinden imzalı token'ı döndürür.

- [ ] **Step 1: Başarısız testleri yaz** — `tests/test_csrf.py` oluştur:

```python
import re

import pytest

from tests.yardimci import SahteYZ, gecici_db
from uniasist.kurulum import kur
from uniasist.uygulama import uygulama_olustur


@pytest.fixture
def paket():
    return kur(db=gecici_db(), yapay_zeka=SahteYZ())


@pytest.fixture
def istemci(paket):
    uygulama = uygulama_olustur(paket)
    uygulama.config["TESTING"] = True
    # WTF_CSRF_ENABLED ayarlanmaz — bu uygulamada CSRF AÇIK kalır
    with uygulama.test_client() as istemci:
        yield istemci


def _token_al(istemci, yol="/giris"):
    metin = istemci.get(yol).get_data(as_text=True)
    eslesme = re.search(r'<meta name="csrf-token" content="([^"]+)"', metin)
    assert eslesme, "csrf meta etiketi bulunamadı"
    return eslesme.group(1)


def test_tokensiz_post_400_doner(istemci):
    yanit = istemci.post(
        "/giris", data={"eposta": "a@universite.edu.tr", "sifre": "Yanlis1234"}
    )
    assert yanit.status_code == 400


def test_gecersiz_token_400_doner(istemci):
    yanit = istemci.post(
        "/giris",
        data={
            "eposta": "a@universite.edu.tr",
            "sifre": "Yanlis1234",
            "csrf_token": "sahte-deger",
        },
    )
    assert yanit.status_code == 400


def test_form_tokenu_kabul_edilir(istemci):
    token = _token_al(istemci)
    yanit = istemci.post(
        "/giris",
        data={
            "eposta": "a@universite.edu.tr",
            "sifre": "Yanlis1234",
            "csrf_token": token,
        },
    )
    assert yanit.status_code == 200
    assert "E-posta veya şifre hatalı" in yanit.get_data(as_text=True)


def test_baslik_tokenu_kabul_edilir(istemci):
    token = _token_al(istemci)
    yanit = istemci.post(
        "/giris",
        data={"eposta": "a@universite.edu.tr", "sifre": "Yanlis1234"},
        headers={"X-CSRFToken": token},
    )
    assert yanit.status_code == 200
    assert "E-posta veya şifre hatalı" in yanit.get_data(as_text=True)


def test_get_istekleri_etkilenmez(istemci):
    assert istemci.get("/giris").status_code == 200


def test_meta_etiketi_token_tasir(istemci):
    metin = istemci.get("/giris").get_data(as_text=True)
    assert '<meta name="csrf-token"' in metin
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

Run: `.venv\Scripts\python -m pytest tests/test_csrf.py -q`
Expected: FAIL — 4 test assertion hatası (400 bekleyenler 200 alır; meta testi etiketi bulamaz), 2 test geçebilir.

- [ ] **Step 3: flask-wtf kur ve requirements'a ekle**

Run: `.venv\Scripts\pip install flask-wtf`
`requirements.txt`'ye `flask-wtf` satırı ekle (alfabetik değil, mevcut sıraya uyan yere).

- [ ] **Step 4: `uygulama_olustur`'da CSRFProtect başlat** — `uniasist/uygulama.py`

`from flask_wtf import CSRFProtect` import'u ekle; `uygulama.secret_key = config.SECRET_KEY` atamasından sonra `CSRFProtect(uygulama)` çağır. (Her `uygulama_olustur` çağrısı kendi örneğini oluşturur; Jinja global'leri `init_app` içinde otomatik kaydedilir.)

- [ ] **Step 5: Meta etiketini temel düzene ekle** — `sablonlar/temel.html`

`<meta name="viewport" ...>` satırından (satır 5) sonra `{{ csrf_meta_tag() }}` ekle.

- [ ] **Step 6: 9 test fixture'ına CSRF kapatma satırı ekle**

Files bölümündeki 9 dosyada `uygulama.config["TESTING"] = True` satırının hemen altına `uygulama.config["WTF_CSRF_ENABLED"] = False` ekle.

- [ ] **Step 7: Testleri doğrula**

Run: `.venv\Scripts\python -m pytest tests/test_csrf.py -q`
Expected: 6 PASS.
Run: `.venv\Scripts\python -m pytest -q`
Expected: 240 pass (234 + 6).

- [ ] **Step 8: Commit**

```bash
git add requirements.txt uniasist/uygulama.py sablonlar/temel.html tests/test_csrf.py tests/test_ekran_dersler.py tests/test_ekran_giris.py tests/test_ekran_ogrenci.py tests/test_ekran_profil.py tests/test_ekran_sohbet.py tests/test_ekran_tanitim.py tests/test_ekran_yonetici.py tests/test_plan.py tests/test_tema.py
git commit -m "feat: csrf korumasi flask wtf ile etkinlestirildi"
```

---

### Task 2: Form gizli tokenleri + JS fetch başlıkları

**Files:**
- Modify: `sablonlar/ders.html` (formlar satır 15, 29, 46), `sablonlar/bildirimler.html` (20, 25), `sablonlar/belgelerim.html` (28, 64, 80, 87, 114), `sablonlar/dersler.html` (11, 29, 33 — satır 7'deki GET formu ALMAZ), `sablonlar/dogrulama_bekliyor.html` (14), `sablonlar/giris.html` (6), `sablonlar/kayit.html` (6), `sablonlar/kullanicilar.html` (29, 36 — satır 6 GET ALMAZ), `sablonlar/plan.html` (23, 42), `sablonlar/profil.html` (33, 49), `sablonlar/sohbet.html` (13 — satır 65'teki `soru-formu` JS'e özel, ALMAZ), `sablonlar/temel.html` (41), `sablonlar/yanitlanamayan.html` (24)
- Modify: `statik/sohbet.js` (fetch çağrıları satır 92, 200, 232-235)
- Test: `tests/test_csrf.py` (genişlet)

**Interfaces:**
- Consumes: Task 1'in `istemci` fixture'ı (CSRF açık) ve `_token_al(istemci, yol)`.
- Produces: tüm POST formları `csrf_token` gizli girişi taşır; `sohbet.js` meta etiketten okuduğu token'ı `X-CSRFToken` başlığıyla gönderir. Test yardımcıları: `_dogrulanmis_kullanici(paket)` (doğrulanmış öğrenci oluşturur, `Kullanici` entity'si ile — `tests/test_ekran_sohbet.py:29-38` deseni), `_giris_yap(istemci)` (giriş formundaki gizli tokenla tam giriş akışı, yanıt döndürür).

- [ ] **Step 1: Başarısız testleri yaz** — `tests/test_csrf.py`'ye ekle:

```python
def _dogrulanmis_kullanici(paket):
    from uniasist.entity import Kullanici
    from uniasist.enumlar import Rol
    from uniasist.guvenlik import sifre_hashle

    ogrenci = Kullanici(
        ad_soyad="Ali Veli",
        eposta="ali@universite.edu.tr",
        sifre_hash=sifre_hashle("Gizli1234"),
        rol=Rol.OGRENCI,
        universite="Üniversite",
        bolum="Bilgisayar Mühendisliği",
        eposta_dogrulandi=True,
    )
    paket.kimlik.kullanici_deposu.kaydet(ogrenci)


def _giris_yap(istemci):
    metin = istemci.get("/giris").get_data(as_text=True)
    eslesme = re.search(r'name="csrf_token" value="([^"]+)"', metin)
    assert eslesme, "giris formunda gizli csrf_token yok"
    yanit = istemci.post(
        "/giris",
        data={
            "eposta": "ali@universite.edu.tr",
            "sifre": "Gizli1234",
            "csrf_token": eslesme.group(1),
        },
    )
    assert yanit.status_code == 302
    assert yanit.headers["Location"].endswith("/sohbet")
    return yanit


def test_giris_formunda_gizli_token(istemci, paket):
    _dogrulanmis_kullanici(paket)
    yanit = _giris_yap(istemci)
    assert yanit.headers["Location"].endswith("/sohbet")


def test_yanit_rotasi_baslik_tokeni_ile_calisir(istemci, paket):
    _dogrulanmis_kullanici(paket)
    _giris_yap(istemci)
    token = _token_al(istemci, "/sohbet")
    yanit = istemci.post(
        "/sohbet/yanit",
        data={"soru": "Burs başvurusu ne zaman yapılır?"},
        headers={"X-CSRFToken": token},
    )
    assert yanit.status_code == 200


def test_geri_bildirim_json_rotasi_korumali(istemci, paket):
    _dogrulanmis_kullanici(paket)
    _giris_yap(istemci)
    token = _token_al(istemci, "/sohbet")
    yanit = istemci.post(
        "/geri-bildirim", json={"mesaj_id": 999999, "tur": "YARARLI"}
    )
    assert yanit.status_code == 400
    assert yanit.get_json(silent=True) is None  # CSRF 400'ü — view çalışmadı
    yanit = istemci.post(
        "/geri-bildirim",
        json={"mesaj_id": 999999, "tur": "YARARLI"},
        headers={"X-CSRFToken": token},
    )
    veri = yanit.get_json(silent=True)
    assert veri is not None and veri["ok"] is False  # view çalıştı, mesaj yok
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

Run: `.venv\Scripts\python -m pytest tests/test_csrf.py -q`
Expected: FAIL — 3 yeni test `_giris_yap` içinde "giris formunda gizli csrf_token yok" assert hatasıyla düşer (form henüz gizli alan taşımıyor).

- [ ] **Step 3: 25 POST formuna gizli alan ekle** — Files bölümündeki satır numaralarıyla listelenen tüm formlara, form açılış etiketinden hemen sonra:

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

- [ ] **Step 4: `statik/sohbet.js`'ye başlık ekle**

- Satır 10'dan sonra: meta etiketten token oku:
  `var csrfMeta = document.querySelector('meta[name="csrf-token"]');`
  `var csrfToken = csrfMeta ? csrfMeta.content : null;`
- Satır 92 `fetch("/sohbet/yanit", ...)`: seçeneklere `headers: { "X-CSRFToken": csrfToken }` ekle.
- Satır 200 `fetch("/sohbet/" + sohbetId + "/ad", ...)`: aynı başlığı ekle.
- Satır 232-235 `fetch("/geri-bildirim", ...)`: mevcut `headers` nesnesine `"X-CSRFToken": csrfToken` ekle.

- [ ] **Step 5: Testleri doğrula**

Run: `.venv\Scripts\python -m pytest tests/test_csrf.py -q`
Expected: 9 PASS.
Run: `.venv\Scripts\python -m pytest -q`
Expected: 243 pass.

- [ ] **Step 6: Manuel smoke test (JS'in gerçek tarayıcıda çalıştığını doğrula)**

Run: `.venv\Scripts\python app.py` → http://127.0.0.1:5000, `ali@universite.edu.tr / Ogrenci1234` ile giriş:
- Sohbete soru sor → yanıt akmalı (fetch + token).
- Sohbet adlandır (Kenar çubuğu) → sayfa yenilenmeli.
- Bir yanıta "Yararsız" + açıklama gönder → teşekkür mesajı.
- Belgelerim'den dosya yükle → başarı (multipart + token).
Beklenen: hepsi çalışır, sunucu konsolunda CSRF 400 kaydı yok.

- [ ] **Step 7: Commit**

```bash
git add sablonlar/ders.html sablonlar/bildirimler.html sablonlar/belgelerim.html sablonlar/dersler.html sablonlar/dogrulama_bekliyor.html sablonlar/giris.html sablonlar/kayit.html sablonlar/kullanicilar.html sablonlar/plan.html sablonlar/profil.html sablonlar/sohbet.html sablonlar/temel.html sablonlar/yanitlanamayan.html statik/sohbet.js tests/test_csrf.py
git commit -m "feat: formlara ve fetch isteklerine csrf token baglantisi"
```

---

### Task 3: /cikis GET'ten POST'a

**Files:**
- Modify: `uniasist/ekran/giris.py:88-94`
- Modify: `sablonlar/temel.html:29`
- Modify: `tests/test_ekran_giris.py:80`, `tests/test_ekran_profil.py:104`, `tests/test_ekran_sohbet.py:306` (her biri `istemci.get("/cikis")` → `istemci.post("/cikis")`)
- Test: `tests/test_csrf.py` (genişlet)

**Interfaces:**
- Consumes: Task 1-2'nin `istemci` fixture'ı, `_dogrulanmis_kullanici`, `_giris_yap`, `_token_al`.
- Produces: `/cikis` yalnız POST (GET → 405); çıkış formu token taşır.

- [ ] **Step 1: Başarısız testleri yaz** — `tests/test_csrf.py`'ye ekle:

```python
def test_cikis_post_ile_yapilir(istemci, paket):
    _dogrulanmis_kullanici(paket)
    _giris_yap(istemci)
    token = _token_al(istemci, "/sohbet")
    yanit = istemci.post("/cikis", headers={"X-CSRFToken": token})
    assert yanit.status_code == 302
    assert yanit.headers["Location"].endswith("/giris")


def test_cikis_get_405_doner(istemci):
    assert istemci.get("/cikis").status_code == 405
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

Run: `.venv\Scripts\python -m pytest tests/test_csrf.py -q`
Expected: FAIL — `test_cikis_post_ile_yapilir` 405 alır (rota henüz POST kabul etmiyor), `test_cikis_get_405_doner` 302 alır.

- [ ] **Step 3: Rota ve şablonu değiştir**

- `uniasist/ekran/giris.py:88`: `@giris_bp.route("/cikis")` → `@giris_bp.route("/cikis", methods=["POST"])` (gövde değişmez).
- `sablonlar/temel.html:29`: `<a href="/cikis">Çıkış</a>` → `temel.html:41`'deki desenle uyumlu satır içi form: `method="post" action="/cikis"`, `class="satir-ici"`, gizli `csrf_token` alanı (Task 2 deseni), `type="submit"` düğmesi "Çıkış" etiketiyle. Görünüm mevcut menü bağlantılarıyla uyumlu kalmalı (gerekiyorsa `stil.css`'e küçük düğme stili eklenebilir).

- [ ] **Step 4: Mevcut 3 test çağrısını güncelle**

Files bölümündeki 3 dosyada `istemci.get("/cikis")` → `istemci.post("/cikis")` (bu fixture'larda CSRF kapalı, token gerekmez).

- [ ] **Step 5: Testleri doğrula**

Run: `.venv\Scripts\python -m pytest tests/test_csrf.py tests/test_ekran_giris.py tests/test_ekran_profil.py tests/test_ekran_sohbet.py -q`
Expected: PASS.
Run: `.venv\Scripts\python -m pytest -q`
Expected: 245 pass (243 + 2).

- [ ] **Step 6: Commit**

```bash
git add uniasist/ekran/giris.py sablonlar/temel.html tests/test_csrf.py tests/test_ekran_giris.py tests/test_ekran_profil.py tests/test_ekran_sohbet.py
git commit -m "feat: cikis rotasi post ile csrf korumali"
```

---

### Task 4: SameSite=Lax çerezler

**Files:**
- Modify: `uniasist/uygulama.py` (~satır 36, `secret_key` ataması sonrası)
- Modify: `uniasist/ekran/giris.py:81`
- Test: `tests/test_csrf.py` (genişlet)

**Interfaces:**
- Consumes: Task 1-2'nin `istemci` fixture'ı, `_dogrulanmis_kullanici`.
- Produces: `uniasist_oturum` ve Flask `session` çerezleri `SameSite=Lax` özniteliğiyle set edilir.

- [ ] **Step 1: Başarısız testleri yaz** — `tests/test_csrf.py`'ye ekle:

```python
def test_oturum_cerezi_samesite_lax(istemci, paket):
    _dogrulanmis_kullanici(paket)
    yanit = _giris_yap(istemci)  # giriş yanıtını döndürür
    set_cerez = yanit.headers.get("Set-Cookie", "")
    assert "uniasist_oturum" in set_cerez
    assert "SameSite=Lax" in set_cerez


def test_session_cerezi_samesite_lax(istemci):
    yanit = istemci.get("/giris")
    set_cerez = yanit.headers.get("Set-Cookie", "")
    assert "session" in set_cerez
    assert "SameSite=Lax" in set_cerez
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

Run: `.venv\Scripts\python -m pytest tests/test_csrf.py -q`
Expected: FAIL — iki yeni test "SameSite=Lax" bulamaz (öznitelik set edilmiyor).

- [ ] **Step 3: Çerez özniteliklerini ekle**

- `uniasist/ekran/giris.py:81`: `yanit.set_cookie("uniasist_oturum", oturum.oturum_id, httponly=True)` → sonuna `samesite="Lax"` ekle.
- `uniasist/uygulama.py`: `uygulama.secret_key = ...` sonrası `uygulama.config["SESSION_COOKIE_SAMESITE"] = "Lax"` ekle.

- [ ] **Step 4: Testleri doğrula**

Run: `.venv\Scripts\python -m pytest tests/test_csrf.py -q`
Expected: 11 PASS.
Run: `.venv\Scripts\python -m pytest -q`
Expected: 247 pass (245 + 2).

- [ ] **Step 5: Commit**

```bash
git add uniasist/uygulama.py uniasist/ekran/giris.py tests/test_csrf.py
git commit -m "feat: cerezlere samesite lax ekle"
```

---

### Task 5: Dokümantasyon güncelleme

**Files:**
- Modify: `README.md` ("Kurulum" bölümünden sonra yeni "## Güvenlik" bölümü)
- Modify: `SONRAKI_ADIMLAR.md`

**Interfaces:**
- Consumes: Task 1-4'ün tamamlanmış durumu (test sayıları, davranış).
- Produces: güncel devir belgesi.

- [ ] **Step 1: README'ye Güvenlik bölümü ekle**

"## Kurulum" bölümünden sonra kısa bölüm: CSRF koruması tüm POST'larda açık (flask-wtf, `X-CSRFToken` başlığı / form alanı), çerezlerde `SameSite=Lax`, token geçerlilik süresi 1 saat (`WTF_CSRF_TIME_LIMIT`), HTTPS + `Secure` çerez bayrağı canlıya çıkışta eklenecek (bilinçli ertelenmiş).

- [ ] **Step 2: SONRAKI_ADIMLAR.md'yi güncelle**

CSRF maddesi tamamlandı olarak işaretlenir (tarih, test sayısı 247/247, `flask-wtf` bağımlılığı notu); sıradaki adımlar: HTTPS/Secure çerez → GitHub varsayılan dal. "Kabul edilen kararlar" bölümünden "CSRF koruması YOK" satırı kaldırılıp yeni durum yazılır.

- [ ] **Step 3: Tam suite son kontrol**

Run: `.venv\Scripts\python -m pytest -q`
Expected: 247 pass.

- [ ] **Step 4: Commit**

```bash
git add README.md SONRAKI_ADIMLAR.md
git commit -m "docs: csrf korumasi tamamlandi belgeleri guncelle"
```
