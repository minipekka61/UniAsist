# UniAsist — Sonraki Adımlar (2026-11-08 oturum sonu durumu)

> Bu dosya oturumlar arası devir teslim belgesidir. Opencode'u açınca bu dosyayı
> göstererek kaldığın yerden devam etmesini iste.

## ⏸ Kaldığın yer (2026-11-08, oturum durduruldu)

- `fix/sonraki-adimlar` dalı **hazır**: 6 düzeltme tamamlandı, 234/234 test yeşil,
  bağımsız inceleme "Ready to merge: Yes" verdi (Critical/Important bulgu yok).
- **YARIN İLK İŞ:** dalı yerel `master`'a merge et ve `git push origin master` yap.
  (Merge öncesi suite'i bir kez daha çalıştır: `.venv\Scripts\python -m pytest -q`)
- Sonrasında öncelik sırasıyla: CSRF → HTTPS/Secure çerez → GitHub varsayılan dal.
- İncelemeden ertelenen 3 minor iyileştirme aşağıda "İncelemeden ertelenen
  minorlar" bölümünde listeli.

## Mevcut durum

- **2026-10-31 oturumu:** UniAsist v2 (SaaS dönüşümü) 15/15 görevle tamamlandı,
  229/229 test yeşildi, `feat/uniasist-v2-saas` GitHub'a pushlandı.
- **GitHub entegrasyonu tamamlandı:** uzak `master`, v2 içeren `8c145f7`'ye
  güncellendi (PR yerine direkt push — `gh` CLI kurulu değil).
- **2026-11-08 oturumu:** Ertelenen 6 minor iyileştirmenin tamamı `fix/sonraki-adimlar`
  dalında yapıldı (6 commit, `9d7a6c5..638dd10`), bağımsız kod incelemesi
  "Ready to merge: Yes" verdi (Critical/Important yok), 234/234 test yeşil.

## 2026-11-08'de yapılanlar

1. ✅ **Plan geçişlerinde sessiz hata yutma** — `ekran/plan.py` artık IK-10 hata
   mesajını sayfada gösteriyor (yönetici "Pro'ya Geç"e basınca mesaj görüyor).
2. ✅ **"Ders / Kategori" etiketi** — `belgelerim.html`'de üç yer "Kategori" oldu.
3. ✅ **SERVIS_HATASI kotası** — düzeltme gerekmedi: mevcut kod servis hatasında
   SoruKaydi hiç yazmıyor, kota zaten tüketilmiyor (`test_ik19...` bilinçli koruyor).
   Uçtan uca regresyon testi eklendi (`test_ik33_servis_hatasi_kotayi_tuketmez`).
   *Bilinen ödün:* servis hataları yönetici kullanım raporlarında görünmez
   (`toplam_soru` kesinti sırasında eksik sayar). Görünürlük istenirse
   "kaydet + saymadan çıkar" yaklaşımı için SoruKaydi'ya durum alanı gerekir.
4. ✅ **Ders filtresi artık kendi belgelerine de uygulanıyor** (ürün sahibi kararı,
   2026-11-08): sohbette bir ders seçiliyken yalnız o derse etiketli kendi
   belgeleri + o dersin paylaşılanları kapsamda. "Tüm derslerim" seçiminde davranış
   değişmedi. Spec'e işlendi.
5. ✅ **Yabancı sohbet_id ile /sohbet/yanit** — artık 500 yerine 403 dönüyor.
6. ✅ **README yazım hatası** — "muaftır" düzeltildi.

## Sonraki adımlar (öncelik sırasıyla)

1. **CSRF koruması** — halka açık deployment'tan ÖNCE eklenmeli (öncelikli,
   bilinçli ertelenmiş karar).
2. **HTTPS + `Secure` çerez bayrağı** — canlıya çıkarken (`uniasist_tema` çerezi
   dahil).
3. **GitHub varsayılan dalı** — uzak `main` ayrı/eski bir geçmişte ("Initial
   commit"); GitHub ayarlarından varsayılan dal `master` yapılmalı ya da `main`
   silinmeli (tarayıcıdan yapılır, CLI yok).

## İncelemeden ertelenen minorlar (bilinçli, istenirse yapılır)

- `test_sohbet.py` kapsam testine "kendi belgesi başka takip edilen derse etiketli"
  senaryosu eklenebilir (kod doğru, test niyeti belgelemez).
- `ucretsize_don` hata yolu test edilmiyor (yalnız `/plan/pro` testli; buton
  yöneticiye render edilmediği için erişim zayıf).
- `ekran/plan.py` iki rota aynı hata yapısını paylaşıyor; ortak yardımcı çıkar.

## Kabul edilen kararlar (bilinçli, değiştirilmedi)

- CSRF koruması YOK — halka açık deployment öncesi eklenecek (öncelikli).
- Tema çerezi `Secure` bayraksız (dev HTTP aşaması; HTTPS'e geçince eklenecek).
- Pro→Ücretsiz düşen kullanıcının mevcut PAYLASILAN belgesini başka derse
  taşıması engellenmiyor (spec yalnız yeni paylaşımı engelliyor).
- `kullanici_ders` tablosunda FK/cascade yok (kod tabanı stiliyle uyumlu).
- Var olmayan sohbet_id 403 döner (404 değil — kaynak varlığını ifşa etmemek için;
  kardeş rotalarla tutarlı).
- Servis hatasında sohbet geçmişine iz bırakılmıyor (soru kaydı da yok — yukarıdaki
  ödün notu).

## Çalıştırma hatırlatıcıları

```
.venv\Scripts\python app.py          # http://127.0.0.1:5000
.venv\Scripts\python -m pytest -q    # testler (234/234)
.venv\Scripts\python degerlendir.py  # 50 soru, hedef >=%80 (sonuç: %86)
```

Demo hesaplar: `admin@universite.edu.tr / Yonetici1234`,
`ali@universite.edu.tr / Ogrenci1234` (Pro), `ayse@universite.edu.tr / Ogrenci1234` (Ücretsiz).
