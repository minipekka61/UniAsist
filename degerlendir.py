SORULAR = [
    ("Üniversitede lisans programlarının normal eğitim süresi kaç yıldır?", ["dört", "4 yıl"]),
    ("Lisans öğrencileri en fazla kaç yıl içinde mezun olmak zorundadır?", ["yedi", "7"]),
    ("Bir yarıyılın normal ders yükü kaç AKTS kredisidir?", ["30"]),
    ("Danışman onayı ile ders yükü en fazla kaç AKTS'ye kadar artırılabilir?", ["40"]),
    ("Güz yarıyılı dersleri ne zaman başlar?", ["28 Eylül"]),
    ("Bahar yarıyılı dersleri ne zaman başlar?", ["15 Şubat"]),
    ("Yaz okulu hangi tarihler arasında düzenlenir?", ["5 Temmuz"]),
    ("Güz yarıyılı yarıyıl sonu sınavları hangi tarihler arasında yapılır?", ["25 Ocak", "Ocak"]),
    ("Ders ekleme ve bırakma işlemleri hangi süre içinde yapılır?", ["iki hafta", "2 hafta"]),
    ("Ders eklemede bir yarıyılda en fazla kaç AKTS olacak şekilde ders eklenebilir?", ["40"]),
    ("Yarıyıl ders yükü kaç AKTS'nin altına düşemez?", ["15"]),
    ("Burs başvuruları ne zaman yapılır?", ["eylül"]),
    ("Başarı bursu için genel not ortalaması en az kaç olmalıdır?", ["3,00", "3.00"]),
    ("Başarı bursu eğitim ücretinden yüzde kaç indirim sağlar?", ["%50", "50"]),
    ("Başarı bursunun kitap-kırtasiye desteği aylık ne kadardır?", ["1.000", "1000"]),
    ("Yurt başvuruları ne zaman ve hangi sistem üzerinden yapılır?", ["temmuz", "KYK"]),
    ("Üniversite yurtlarında kontenjanın yüzde kaçı birinci sınıf öğrencilerine ayrılır?", ["%20", "20"]),
    ("Üç kişilik odalarda aylık yurt ücreti ne kadardır?", ["3.500", "3500"]),
    ("Staj başvurusu için en az kaç gün süreyle çalışma gerekir?", ["60"]),
    ("Staj iki ayrı işyerinde toplam kaç gün olarak tamamlanabilir?", ["60"]),
    ("Staj yapılacak işyeri staj başlangıcından ne kadar önce onaya sunulur?", ["on beş", "15"]),
    ("Mezuniyet için toplam kaç AKTS kredisi tamamlanmalıdır?", ["240"]),
    ("Mezuniyet için genel not ortalaması en az kaç olmalıdır?", ["2,00", "2.00"]),
    ("Mezuniyet töreni ne zaman yapılır?", ["haziran"]),
    ("Yüksek onur öğrencisi olmak için mezuniyet ortalaması en az kaç olmalıdır?", ["3,50", "3.50"]),
    ("Çift anadal programına başvuru hangi yarıyılın sonunda yapılır?", ["dördüncü", "4"]),
    ("Çift anadal başvurusu için genel not ortalaması en az kaç olmalıdır?", ["3,00", "3.00"]),
    ("Çift anadal programında her yarıyıl en fazla kaç AKTS ders alınabilir?", ["12"]),
    ("Yatay geçiş için genel not ortalaması en az kaç olmalıdır?", ["2,50", "2.50"]),
    ("Yatay geçiş başvuruları hangi aylarda alınır?", ["temmuz", "ocak"]),
    ("Yatay geçiş kontenjanı birinci sınıf mevcudunun yüzde kaçını geçemez?", ["%15", "15"]),
    ("Kayıt yenileme süresi ne kadardır?", ["iki hafta", "2 hafta"]),
    ("Katkı payı kaç taksitte ödenir?", ["iki taksit", "2 taksit"]),
    ("Gecikmeli kayıt için en fazla kaç gün ek süre tanınabilir?", ["on beş", "15"]),
    ("Yaz okulunda en fazla kaç ders alınabilir?", ["iki ders", "2 ders"]),
    ("Başka bir üniversiteden yaz okulunda en fazla kaç AKTS ders alınabilir?", ["9"]),
    ("Yaz okulu hangi tarihler arasında yürütülür?", ["5 Temmuz"]),
    ("Diplomalar tahkik tarihinden itibaren kaç gün içinde hazırlanır?", ["otuz", "30"]),
    ("Geçici mezuniyet belgesi en fazla ne kadar süre kullanılabilir?", ["altı ay", "6 ay"]),
    ("Diploma kaybı hâlinde ne yapılması gerekir?", ["ilan", "geçici mezuniyet"]),
    ("Psikolojik danışmanlık hizmeti ücretli mi?", ["ücretsiz"]),
    ("Genel not ortalaması kaçın altına düşen öğrencilere akademik uyarı yapılır?", ["2,00", "2.00"]),
    ("Yurtdışı eğitim programları başvuru duyuruları hangi aylarda yapılır?", ["ekim", "şubat"]),
    ("Engelli öğrencilere sınavlarda yüzde kaça kadar ek süre tanınabilir?", ["%50", "50"]),
    ("Engelli öğrenci bildirim formu başvurusunda hangi belge sunulur?", ["rapor"]),
    ("Görme engelli öğrencilerin ders materyalleri hangi biçimlere dönüştürülür?", ["sesli kitap", "rak"]),
    ("Burs başvurusu nereye yapılır?", ["Öğrenci İşleri"]),
    ("Yurt başvurusu hangi kurumun sistemi üzerinden yapılır?", ["KYK"]),
    ("Tek ders sınavında verilebilecek en yüksek not nedir?", ["CC"]),
    ("İhtiyaç bursundan aylık ne kadar destek verilir?", ["2.500", "2500"]),
]

HEDEF_ORAN = 80


def main():
    from uniasist.kurulum import kur

    paket = kur(seed_yap=True)
    saglayici = type(paket.yapay_zeka).__name__
    sohbet = paket.sohbet.yeniSohbetBaslat(ziyaretci_oturum_id="degerlendir")

    dogru = 0
    basarisiz = []
    for soru, anahtarlar in SORULAR:
        sonuc = None
        for olay in paket.sohbet.soruSorAkis(sohbet, soru):
            if olay.get("tur") == "sonuc":
                sonuc = olay
        if (
            sonuc is not None
            and sonuc["durum"] == "YANIT"
            and sonuc["kaynaklar"]
            and any(anahtar in sonuc["metin"] for anahtar in anahtarlar)
        ):
            dogru += 1
        else:
            basarisiz.append(soru)

    toplam = len(SORULAR)
    oran = dogru * 100 / toplam
    print(f"Sağlayıcı: {saglayici}")
    print(f"Toplam soru: {toplam}")
    print(f"Doğru yanıt: {dogru}")
    print(f"Başarı oranı: %{oran:.0f} (hedef: %{HEDEF_ORAN})")
    if oran >= HEDEF_ORAN:
        print("Sonuç: hedefe ulaşıldı.")
    else:
        print("Sonuç: hedefe ulaşılamadı.")
    if basarisiz:
        print("Yanıtlanamayan ya da hatalı yanıtlanan sorular:")
        for soru in basarisiz:
            print(f"  - {soru}")


if __name__ == "__main__":
    main()
