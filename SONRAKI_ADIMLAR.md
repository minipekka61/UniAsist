# UniAsist — Sonraki Adımlar (2026-11-11 oturum sonu durumu)

> Bu dosya oturumlar arası devir teslim belgesidir. Opencode'u açınca bu dosyayı
> göstererek kaldığın yerden devam etmesini iste.

## ⏸ Kaldığın yer (2026-11-11, oturum devam ediyor)

- `feat/csrf-korumasi` dalı implementation planının 5/5 task'ı tamamlandı,
  247/247 test yeşil (234 eski + 13 yeni CSRF testi).
- **SIRADAKİ İŞ:** Dal için bağımsız kod incelemesi (review) → bulgular
  değerlendirilir → yerel `master`'a merge + `git push origin master`.
- Sonrasında öncelik sırasıyla: HTTPS/Secure çerez → GitHub varsayılan dal.

## Mevcut durum

- **2026-10-31 oturumu:** UniAsist v2 (SaaS dönüşümü) 15/15 görevle tamamlandı,
  229/229 test yeşildi, `feat/uniasist-v2-saas` GitHub'a pushlandı.
- **2026-11-08 oturumu:** Ertelenen 6 minor iyileştirme `fix/sonraki-adimlar`
  dalında yapıldı; dal `master`'a merge edildi, pushlandı (95034df), dal silindi.
- **2026-11-11 oturumu:** CSRF koruması `feat/csrf-korumasi` dalında yapıldı
  (5 task, `0998d4d..HEAD`): flask-wtf `CSRFProtect` tüm POST'larda etkin,
  25 forma gizli token, `sohbet.js` fetch'lere `X-CSRFToken` başlığı,
  `/cikis` POST'a çevrildi, çerezlere `SameSite=Lax` eklendi. 247/247 yeşil.
  Tasarım: `docs/superpowers/specs/2026-11-11-csrf-korumasi-design.md`,
  plan: `docs/superpowers/plans/2026-11-11-csrf-korumasi.md`.

## Sonraki adımlar (öncelik sırasıyla)

1. **`feat/csrf-korumasi` inceleme + merge** — bağımsız inceleme sonrası yerel
   `master`'a merge et ve `git push origin master` yap. (Merge öncesi suite:
   `.venv\Scripts\python -m pytest -q` → 247/247.)
2. **HTTPS + `Secure` çerez bayrağı** — canlıya çıkarken (`uniasist_tema`
   çerezi dahil; `uniasist_oturum` ve `session`'a da `Secure` eklenmeli).
3. **GitHub varsayılan dalı** — uzak `main` ayrı/eski bir geçmişte ("Initial
   commit"); GitHub ayarlarından varsayılan dal `master` yapılmalı ya da `main`
   silinmeli (tarayıcıdan yapılır, CLI yok).

## Kabul edilen kararlar (bilinçli, değiştirilmedi)

- CSRF koruması flask-wtf ile (el yapımı token değil) — ürün sahibi kararı,
  2026-11-11. Davranış testleri `WTF_CSRF_ENABLED = False` ile çalışır; CSRF'in
  kendisi `tests/test_csrf.py`'de odaklı test edilir.
- CSRF token'ı Flask'ın imzalı `session` çerezinde taşınır (SECRET_KEY mevcut).
- `/cikis` POST oldu; GET 405 döner. Menüdeki çıkış düğmesi formdur.
- Tema çerezi `Secure` bayraksız (dev HTTP aşaması; HTTPS'e geçince eklenecek).
- Pro→Ücretsiz düşen kullanıcının mevcut PAYLASILAN belgesini başka derse
  taşıması engellenmiyor (spec yalnız yeni paylaşımı engelliyor).
- `kullanici_ders` tablosunda FK/cascade yok (kod tabanı stiliyle uyumlu).
- Var olmayan sohbet_id 403 döner (404 değil — kaynak varlığını ifşa etmemek için;
  kardeş rotalarla tutarlı).
- Servis hatasında sohbet geçmişine iz bırakılmıyor (soru kaydı da yok —
  2026-11-08 ödün notu).

## İncelemeden ertelenen minorlar (bilinçli, istenirse yapılır)

- `test_sohbet.py` kapsam testine "kendi belgesi başka takip edilen derse etiketli"
  senaryosu eklenebilir (kod doğru, test niyeti belgelemez).
- `ucretsize_don` hata yolu test edilmiyor (yalnız `/plan/pro` testli; buton
  yöneticiye render edilmediği için erişim zayıf).
- `ekran/plan.py` iki rota aynı hata yapısını paylaşıyor; ortak yardımcı çıkar.

## Çalıştırma hatırlatıcıları

```
.venv\Scripts\python app.py          # http://127.0.0.1:5000
.venv\Scripts\python -m pytest -q    # testler (247/247)
.venv\Scripts\python degerlendir.py  # 50 soru, hedef >=%80 (sonuç: %86)
```

Demo hesaplar: `admin@universite.edu.tr / Yonetici1234`,
`ali@universite.edu.tr / Ogrenci1234` (Pro), `ayse@universite.edu.tr / Ogrenci1234` (Ücretsiz).
