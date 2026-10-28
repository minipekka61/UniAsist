import config
from uniasist.depo.bilgi_kaynagi_deposu import BilgiKaynagiDeposu
from uniasist.depo.geri_bildirim_deposu import GeriBildirimDeposu
from uniasist.depo.kullanici_deposu import KullaniciDeposu
from uniasist.depo.soru_kaydi_deposu import SoruKaydiDeposu
from uniasist.depo.sohbet_deposu import SohbetDeposu
from uniasist.depo.universite_deposu import UniversiteDeposu
from uniasist.depo.veritabani import baglan
from uniasist.depo.yanitlanamayan_soru_deposu import YanitlanamayanSoruDeposu
from uniasist.eposta import KonsolEpostaServisi, SmtpEpostaServisi
from uniasist.servis.arama_dizini import AramaDizini
from uniasist.servis.belge_isleme_servisi import BelgeIslemeServisi
from uniasist.servis.bilgi_tabani_servisi import BilgiTabaniServisi
from uniasist.servis.geri_bildirim_servisi import GeriBildirimServisi
from uniasist.servis.kimlik_dogrulama_servisi import KimlikDogrulamaServisi
from uniasist.servis.kullanici_yonetim_servisi import KullaniciYonetimServisi
from uniasist.servis.rapor_servisi import RaporServisi
from uniasist.servis.sohbet_servisi import SohbetServisi
from uniasist.servis.yanit_uretme_servisi import YanitUretmeServisi
from uniasist.servis.yanitlanamayan_soru_servisi import YanitlanamayanSoruServisi
from uniasist.veri.bolumler import BOLUMLER
from uniasist.veri.universiteler import UNIVERSITELER
from uniasist.yapayzeka.hazir_llm_servisi import HazirLLMServisi
from uniasist.yapayzeka.yerel_arama_servisi import YerelAramaServisi


class KurulumPaketi:
    def __init__(self, db, yapay_zeka, arama_dizini, kimlik, kullanici_yonetimi,
                 bilgi_tabani, sohbet, yanitlanamayan, geri_bildirim, rapor,
                 universite_deposu, eposta_servisi):
        self.db = db
        self.yapay_zeka = yapay_zeka
        self.arama_dizini = arama_dizini
        self.kimlik = kimlik
        self.kullanici_yonetimi = kullanici_yonetimi
        self.bilgi_tabani = bilgi_tabani
        self.sohbet = sohbet
        self.yanitlanamayan = yanitlanamayan
        self.geri_bildirim = geri_bildirim
        self.rapor = rapor
        self.universite_deposu = universite_deposu
        self.eposta_servisi = eposta_servisi
        self.kullanici_deposu = kimlik.kullanici_deposu


def temel_verileri_ekle(db):
    universite_deposu = UniversiteDeposu(db)
    if not universite_deposu.hepsiniListele():
        from uniasist.entity import Universite

        for ad, alan_adi in UNIVERSITELER:
            universite_deposu.kaydet(Universite(ad=ad, eposta_alan_adi=alan_adi))
    if not universite_deposu.bolumleriListele():
        for bolum in BOLUMLER:
            universite_deposu.bolumEkle(bolum)
    return universite_deposu


def eposta_servisi_olustur():
    if config.MAILGONDER and config.SMTP_KULLANICI:
        return SmtpEpostaServisi()
    return KonsolEpostaServisi()


def kur(db=None, db_yolu=None, yapay_zeka=None, seed_yap=False):
    if yapay_zeka is None:
        if config.API_ANAHTARI:
            yapay_zeka = HazirLLMServisi()
        else:
            yapay_zeka = YerelAramaServisi()
    if db is None:
        db = baglan(db_yolu)

    universite_deposu = temel_verileri_ekle(db)
    eposta_servisi = eposta_servisi_olustur()

    kullanici_deposu = KullaniciDeposu(db)
    sohbet_deposu = SohbetDeposu(db)
    bilgi_kaynagi_deposu = BilgiKaynagiDeposu(db)
    yanitlanamayan_soru_deposu = YanitlanamayanSoruDeposu(db)
    soru_kaydi_deposu = SoruKaydiDeposu(db)
    geri_bildirim_deposu = GeriBildirimDeposu(db)

    arama_dizini = AramaDizini(db)
    if not arama_dizini.saglayiciUyumlu(yapay_zeka.saglayici_etiketi):
        arama_dizini.yenidenGomme(yapay_zeka)

    kimlik = KimlikDogrulamaServisi(kullanici_deposu, universite_deposu, eposta_servisi)
    kullanici_yonetimi = KullaniciYonetimServisi(kullanici_deposu, kimlik)
    belge_isleme = BelgeIslemeServisi(arama_dizini, yapay_zeka)
    bilgi_tabani = BilgiTabaniServisi(bilgi_kaynagi_deposu, belge_isleme, arama_dizini)
    yanit_uretme = YanitUretmeServisi(arama_dizini, yapay_zeka)
    yanitlanamayan = YanitlanamayanSoruServisi(yanitlanamayan_soru_deposu)
    sohbet = SohbetServisi(sohbet_deposu, soru_kaydi_deposu, yanit_uretme, yanitlanamayan, bilgi_kaynagi_deposu, kullanici_deposu)
    geri_bildirim = GeriBildirimServisi(sohbet_deposu, geri_bildirim_deposu)
    rapor = RaporServisi(soru_kaydi_deposu, geri_bildirim_deposu)

    paket = KurulumPaketi(
        db=db,
        yapay_zeka=yapay_zeka,
        arama_dizini=arama_dizini,
        kimlik=kimlik,
        kullanici_yonetimi=kullanici_yonetimi,
        bilgi_tabani=bilgi_tabani,
        sohbet=sohbet,
        yanitlanamayan=yanitlanamayan,
        geri_bildirim=geri_bildirim,
        rapor=rapor,
        universite_deposu=universite_deposu,
        eposta_servisi=eposta_servisi,
    )
    if seed_yap:
        from uniasist import seed

        seed.kos(paket)
    return paket
