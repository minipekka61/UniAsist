import config

from uniasist.dto import YanitSonucu
from uniasist.entity import KaynakReferansi as KaynakRef
from uniasist.enumlar import SonucDurumu
from uniasist.hatalar import IsKuraliIhlaliException
from uniasist.yapayzeka.yerel_arama_servisi import YerelAramaServisi

_BILGI_YOK = "BILGI_YOK"


class YanitUretmeServisi:
    def __init__(self, arama_dizini, yapay_zeka_servisi, benzerlik_esigi=None,
                 en_fazla_parca=None):
        self.arama_dizini = arama_dizini
        self.yapay_zeka_servisi = yapay_zeka_servisi
        if benzerlik_esigi is None:
            if isinstance(yapay_zeka_servisi, YerelAramaServisi):
                benzerlik_esigi = config.YEREL_ESIK
            else:
                benzerlik_esigi = config.BENZERLIK_ESIGI
        self.benzerlik_esigi = benzerlik_esigi
        self.en_fazla_parca = en_fazla_parca or config.EN_FAZLA_PARCA

    def _kaynakReferanslariOlustur(self, sonuclar):
        return [
            KaynakRef(
                bolum_bilgisi=s.parca.bolumBilgisiGetir(),
                kaynak_adi=s.parca.kaynak_adi,
                benzerlik_skoru=s.skor,
                kategori=s.parca.kategori,
                kaynak_id=s.parca.kaynak_id,
            )
            for s in sonuclar
            if s.parca.kaynak_adi
        ]

    def yanitUret(self, soru_metni, baglam, kapsam=None):
        sonuc = None
        for olay in self.yanitUretAkis(soru_metni, baglam, kapsam=kapsam):
            if olay["tur"] == "sonuc":
                sonuc = olay["sonuc"]
        return sonuc

    def yanitUretAkis(self, soru_metni, baglam, kapsam=None):
        try:
            sorgu_gommesi = self.yapay_zeka_servisi.gommeUret(soru_metni)
            sonuclar = self.arama_dizini.enYakinParcalar(
                sorgu_gommesi, self.en_fazla_parca, kapsam=kapsam
            )
        except IsKuraliIhlaliException:
            yield self._sonuc_olayi(
                YanitSonucu(SonucDurumu.SERVIS_HATASI, config.SERVIS_HATA_METNI, [])
            )
            return

        if not sonuclar or sonuclar[0].skor < self.benzerlik_esigi:
            yield self._sonuc_olayi(
                YanitSonucu(SonucDurumu.ICERIK_BULUNAMADI, config.BILGI_YOK_METNI, [])
            )
            return

        kaynaklar = self._kaynakReferanslariOlustur(sonuclar)
        if not kaynaklar:
            yield self._sonuc_olayi(
                YanitSonucu(SonucDurumu.ICERIK_BULUNAMADI, config.BILGI_YOK_METNI, [])
            )
            return

        parcalar = [s.parca for s in sonuclar]
        yayilan = []
        askida = ""
        elendi = False
        try:
            for parca_metni in self.yapay_zeka_servisi.yanitUretAkis(
                soru_metni, parcalar, baglam
            ):
                if elendi:
                    yayilan.append(parca_metni)
                    yield {"tur": "parca", "metin": parca_metni}
                    continue
                askida += parca_metni
                sekil = askida.strip()
                if sekil == _BILGI_YOK:
                    continue
                if len(sekil) < len(_BILGI_YOK) and _BILGI_YOK.startswith(sekil):
                    continue
                elendi = True
                yayilan.append(askida)
                yield {"tur": "parca", "metin": askida}
                askida = ""
        except IsKuraliIhlaliException:
            yield self._sonuc_olayi(
                YanitSonucu(SonucDurumu.SERVIS_HATASI, config.SERVIS_HATA_METNI, [])
            )
            return

        tam_metin = "".join(yayilan) + askida
        if tam_metin.strip() == _BILGI_YOK or not tam_metin.strip():
            yield self._sonuc_olayi(
                YanitSonucu(SonucDurumu.ICERIK_BULUNAMADI, config.BILGI_YOK_METNI, [])
            )
            return
        yield self._sonuc_olayi(
            YanitSonucu(SonucDurumu.YANIT, tam_metin, kaynaklar)
        )

    def _sonuc_olayi(self, sonuc):
        return {"tur": "sonuc", "sonuc": sonuc}
