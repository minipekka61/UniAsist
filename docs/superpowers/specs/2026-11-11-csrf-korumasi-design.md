# CSRF Koruması — Tasarım (2026-11-11)

## Amaç ve neden

Halka açık deployment'tan önce CSRF koruması eklemek (`SONRAKI_ADIMLAR.md`'de
bilinçli ertelenmiş 1. öncelik). Kimlik doğrulama `uniasist_oturum` çereziyle
yapılıyor; tarayıcı bu çerezi siteler-arası isteklerde de otomatik gönderiyor.
Kötü bir site, kullanıcı UniAsist'e girişliyken onun adına belge silebilir,
plan değiştirebilir, yönetici eylemleri tetikleyebilir.

## Hedefler

1. Tüm durum değiştiren POST istekleri geçerli CSRF token'ı gerektirir
   (24 rota, 13 şablonda ~26 form, `sohbet.js`'de 3 `fetch()` ucu).
2. JS `fetch()` uçları token'ı `<meta>` etiketinden okuyup `X-CSRFToken`
   başlığıyla gönderir.
3. `uniasist_oturum` çerezine ve Flask `session` çerezine `SameSite=Lax`
   eklenir (savunma derinliği).
4. Mevcut 234 test yeşil kalır; CSRF için odaklı yeni testler eklenir.

## Hedef olmayanlar

- HTTPS + `Secure` çerez bayrağı (ayrı adım, canlıya çıkışta).
- Content-Security-Policy gibi diğer güvenlik başlıkları.

## Anti-hedefler

- Mevcut UX'in bozulması (formlar görünürde değişmemeli).
- Davranış testlerinin CSRF token'ı derdiyle uğraşması (CSRF testi ayrı dosyada).

## Kısıtlar

- Projenin minimal bağımlılık stiline bilinçli istisna: `flask-wtf` eklenecek
  (ürün sahibi kararı, 2026-11-11).
- Kod tabanı Türkçe isimlendirme ve el yapımı stilinde; şablonlar sabit
  `action` yolları kullanıyor (değişmiyor).

## Yaklaşımlar

1. **Flask-WTF `CSRFProtect` (SEÇİLEN)** — Sektör standardı, denenmiş.
   Tüm POST'lar varsayılan olarak korunur: yeni bir rota eklendiğinde
   unutulma riski yok. Jinja'da `csrf_token()`, AJAX için `X-CSRFToken`
   başlık desteği hazır. Token Flask'ın imzalı `session` çerezinde taşınır
   (`SECRET_KEY` zaten ayarlı). Takas: yeni bağımlılık.
2. **El yapımı token** — Bağımlılık yok, kod tabanı stiline uygun; ama
   güvenlik-kritik kodu (üretim, doğrulama, rotasyon, zaman-güvenli
   karşılaştırma) sıfırdan kendimiz yazıp test etmiş oluruz. Reddedildi:
   denetlenmiş kütüphane, el yazma koddan daha güvenli.
3. **Sadece `SameSite` çerez** — Tek başına tam koruma değil (eski
   tarayıcılar, üst düzey gezinmeler). Reddedildi ana yaklaşım olarak;
   1'in yanında savunma derinliği olarak ekleniyor.

## Nasıl (karara bağlananlar)

- `requirements.txt`'ye `flask-wtf` eklenir, kurulur.
- `uniasist/uygulama.py`: `CSRFProtect(uygulama)` başlatılır;
  `SESSION_COOKIE_SAMESITE = "Lax"`.
- `uniasist/ekran/giris.py`: `set_cookie("uniasist_oturum", ...,
  samesite="Lax")`.
- `sablonlar/temel.html`: `<head>`'e `<meta name="csrf-token"
  content="{{ csrf_token() }}">`.
- `method="post"` olan tüm formlara gizli giriş:
  `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`
  (ders, bildirimler, belgelerim, dersler, dogrulama_bekliyor, giris, kayit,
  kullanicilar, plan, profil, sohbet, temel, yanitlanamayan şablonları).
  GET formları almaz.
- `statik/sohbet.js`: 3 `fetch()` çağrısına meta etiketten okunan
  `X-CSRFToken` başlığı eklenir (FormData ve JSON gövdeleri fark etmez).
- `/cikis` GET'ten POST'a çevrilir (`temel.html`'de satır içi form +
  düğme) — çıkış CSRF'ini de kapatar. *Öneri olarak eklendi, onaya tabi.*
- Testler: mevcut 9 ekran testi dosyasının fixture'larına
  `uygulama.config["WTF_CSRF_ENABLED"] = False` eklenir (TESTING satırının
  yanına). Yeni `tests/test_csrf.py` CSRF'i açık uygulamayla test eder:
  token'sız POST → 400; form token'ıyla POST → başarılı; `X-CSRFToken`
  başlığıyla POST (fetch simülasyonu) → başarılı; GET etkilenmez.

## Builder'a kalan

- Form gizli alanlarının şablon şablon eklenmesi, JS başlık eklemesi,
  fixture satırları ve yeni test dosyasının yazımı; tam test suitinin
  ve `degerlendir.py`'nin yeşil doğrulanması.
