from datetime import datetime, timedelta

import config
from uniasist.entity import (
    Belge,
    GeriBildirim,
    IcerikParcasi,
    Kullanici,
    Mesaj,
    Oturum,
    SSSGirdisi,
    Sohbet,
    YanitlanamayanSoru,
)
from uniasist.enumlar import (
    GonderenTuru,
    HesapDurumu,
    KayitDurumu,
    KaynakDurumu,
    Rol,
)
from uniasist.guvenlik import sifre_hashle


def kullanici(**kw):
    varsayilan = dict(
        ad_soyad="Ali Veli",
        eposta="ali@universite.edu.tr",
        sifre_hash="x",
        rol=Rol.OGRENCI,
    )
    varsayilan.update(kw)
    return Kullanici(**varsayilan)


def test_ik04_bes_denemede_kilitlenme():
    k = kullanici()
    for _ in range(config.AZAMI_HATALI_DENEME):
        k.basarisizDenemeKaydet()
    assert k.kilitliMi()
    assert k.basarisiz_deneme_sayisi == config.AZAMI_HATALI_DENEME
    assert k.kilit_bitis_zamani is not None
    kalan = k.kilit_bitis_zamani - datetime.now()
    assert timedelta(0) < kalan <= timedelta(minutes=config.KILIT_SURESI_DK)


def test_ik04_dort_denemede_kilitlenmez():
    k = kullanici()
    for _ in range(config.AZAMI_HATALI_DENEME - 1):
        k.basarisizDenemeKaydet()
    assert not k.kilitliMi()


def test_kullanici_sifre_dogrulama():
    k = kullanici(sifre_hash=sifre_hashle("Gizli1234"))
    assert k.sifreDogrula("Gizli1234")
    assert not k.sifreDogrula("Yanlis1234")


def test_kullanici_durum_gecisleri():
    k = kullanici()
    assert k.aktifMi()
    k.devreDisiBirak()
    assert k.durum == HesapDurumu.DEVRE_DISI
    assert not k.aktifMi()
    k.rolDegistir(Rol.PERSONEL)
    assert k.rol == Rol.PERSONEL
    k.denemeleriSifirla()
    assert k.basarisiz_deneme_sayisi == 0 and not k.kilitliMi()


def test_kullanici_sifre_guncelle():
    k = kullanici(sifre_hash=sifre_hashle("Eski1234"))
    k.sifreGuncelle(sifre_hashle("Yeni1234"))
    assert k.sifreDogrula("Yeni1234")


def test_oturum_sure_doldu_ve_etkinlik():
    simdi = datetime.now()
    o = Oturum(oturum_id="t1", kullanici_id=1, olusturma_zamani=simdi, son_etkinlik_zamani=simdi)
    assert not o.sureDoldu()
    o.son_etkinlik_zamani = simdi - timedelta(minutes=config.OTURUM_SURESI_DK + 1)
    assert o.sureDoldu()
    o.etkinlikGuncelle()
    assert not o.sureDoldu()
    o.sonlandir()
    assert not o.aktif


def test_sohbet_son_mesajlari_getir_10():
    s = Sohbet(baslik="b", olusturma_zamani=datetime.now())
    for i in range(12):
        s.mesajEkle(Mesaj(gonderen=GonderenTuru.KULLANICI, metin=f"m{i}", zaman=datetime.now()))
    son = s.sonMesajlariGetir(10)
    assert len(son) == 10
    assert [m.metin for m in son] == [f"m{i}" for i in range(2, 12)]
    assert s.bosMu() is False


def test_sohbet_bos_ve_kalici():
    s = Sohbet(baslik="b", olusturma_zamani=datetime.now())
    assert s.bosMu()
    assert not s.kaliciMi()
    o = Sohbet(kullanici_id=7, baslik="b", olusturma_zamani=datetime.now())
    assert o.kaliciMi()


def test_mesaj_kaynak_ekle():
    m = Mesaj(gonderen=GonderenTuru.SISTEM, metin="yanıt", zaman=datetime.now())
    r = lambda: None
    m.kaynakEkle(r)
    assert m.kaynaklariGetir() == [r]


def test_icerik_parcasi_benzerlik_hesapla():
    p = IcerikParcasi(kaynak_id=1, sira=1, metin="a", gomme=[1.0, 0.0])
    assert abs(p.benzerlikHesapla([1.0, 0.0]) - 1.0) < 1e-9
    assert abs(p.benzerlikHesapla([0.0, 1.0]) - 0.0) < 1e-9
    bos = IcerikParcasi(kaynak_id=1, sira=1, metin="a")
    assert bos.benzerlikHesapla([1.0, 0.0]) == 0.0
    assert bos.benzerlikHesapla([]) == 0.0


def test_belge_dosya_gecerli_mi():
    def belge(**kw):
        varsayilan = dict(
            baslik="Yönetmelik",
            kategori="Kayıt",
            dosya_adi="yonetmelik.txt",
            dosya_turu="txt",
            boyut_byte=1000,
            dosya_yolu="x.txt",
        )
        varsayilan.update(kw)
        return Belge(**varsayilan)

    assert belge().dosyaGecerliMi()
    assert belge(dosya_turu="pdf").dosyaGecerliMi()
    assert not belge(dosya_turu="docx").dosyaGecerliMi()
    assert not belge(boyut_byte=config.AZAMI_BELGE_BOYUTU + 1).dosyaGecerliMi()
    assert not belge(baslik="").dosyaGecerliMi()
    assert not belge(kategori="").dosyaGecerliMi()


def test_bilgi_kaynagi_durum_gecisleri():
    b = Belge(baslik="b", kategori="k", dosya_adi="a.txt", dosya_turu="txt", boyut_byte=1, dosya_yolu="p")
    assert b.durum == KaynakDurumu.PASIF
    assert not b.aktifMi()
    b.aktifYap()
    assert b.aktifMi()
    b.pasifYap()
    assert not b.aktifMi()


def test_sssgirdisi_alanlar_gecerli_mi():
    g = SSSGirdisi(baslik="SSS", kategori="Burs", soru="Soru?", cevap="Cevap.")
    assert g.alanlarGecerliMi()
    assert g.kaynakAdiGetir() == "SSS"
    assert "Soru?" in g.icerikMetniGetir() and "Cevap." in g.icerikMetniGetir()
    assert not SSSGirdisi(baslik="SSS", kategori="Burs", soru="", cevap="Cevap.").alanlarGecerliMi()
    assert not SSSGirdisi(baslik="SSS", kategori="Burs", soru="S?", cevap="").alanlarGecerliMi()


def test_geri_bildirim_aciklama_gecerli_mi():
    g = GeriBildirim(mesaj_id=1, kullanici_id=1, tur=None, aciklama="a" * 300, zaman=datetime.now())
    assert g.aciklamaGecerliMi()
    g2 = GeriBildirim(mesaj_id=1, kullanici_id=1, tur=None, aciklama="a" * 301, zaman=datetime.now())
    assert not g2.aciklamaGecerliMi()


def test_yanitlanamayan_soru_tekrar_artir_ve_coz():
    y = YanitlanamayanSoru(soru_metni="Soru?", ilk_tarih=datetime.now())
    assert y.durum == KayitDurumu.ACIK and y.tekrar_sayisi == 1
    y.tekrarArtir()
    assert y.tekrar_sayisi == 2
    y.coz()
    assert y.durum == KayitDurumu.COZULDU


def test_belge_yeni_surum_ata():
    b = Belge(baslik="b", kategori="k", dosya_adi="a.txt", dosya_turu="txt", boyut_byte=1, dosya_yolu="p")
    b.yeniSurumAta("yeni.pdf", "y.pdf", 200)
    assert b.surum_no == 2
    assert b.dosya_adi == "yeni.pdf" and b.dosya_yolu == "y.pdf" and b.boyut_byte == 200


def test_belge_icerik_metni_getir_txt(tmp_path):
    dosya = tmp_path / "belge.txt"
    dosya.write_text("Staj başvurusu için en az 60 gün çalışma şartıdır.", encoding="utf-8")
    b = Belge(baslik="b", kategori="k", dosya_adi="belge.txt", dosya_turu="txt", boyut_byte=1, dosya_yolu=str(dosya))
    assert "60 gün" in b.icerikMetniGetir()
    assert b.kaynakAdiGetir() == "belge.txt"
