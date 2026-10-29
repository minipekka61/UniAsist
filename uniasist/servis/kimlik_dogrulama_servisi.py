import re
import uuid
from datetime import datetime, timedelta

import config
from uniasist.depo.veritabani import (
    oturum_bul,
    oturum_kaydet,
    oturum_sil,
    oturumlari_sonlandir,
)
from uniasist.entity import Kullanici, Oturum
from uniasist.enumlar import Rol
from uniasist.guvenlik import sifre_hashle
from uniasist.hatalar import IsKuraliIhlaliException


class KimlikDogrulamaServisi:
    def __init__(self, kullanici_deposu, eposta_servisi):
        self.kullanici_deposu = kullanici_deposu
        self.eposta_servisi = eposta_servisi

    def _epostaGecerliMi(self, eposta):
        return bool(
            isinstance(eposta, str)
            and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", eposta)
        )

    def _akademikMi(self, eposta):
        alan = eposta.strip().rsplit("@", 1)[-1].lower()
        return any(alan.endswith(sonek) for sonek in config.AKADEMIK_ALAN_ADLARI)

    def _dogrulamaBaglantisi(self, token):
        return f"{config.TEMEL_URL.rstrip('/')}/dogrula/{token}"

    def _dogrulamaDuzenle(self, kullanici):
        token = uuid.uuid4().hex
        bitis = datetime.now() + timedelta(hours=config.DOGRULAMA_SURESI_SAAT)
        kullanici.dogrulamaTokenAta(token, bitis)
        self.kullanici_deposu.kaydet(kullanici)
        self.eposta_servisi.dogrulamaEpostasiGonder(
            kullanici.eposta, kullanici.ad_soyad, self._dogrulamaBaglantisi(token)
        )
        return kullanici

    def _sifreKuralinaUygunMu(self, sifre):
        return (
            isinstance(sifre, str)
            and len(sifre) >= 8
            and any(k.isalpha() for k in sifre)
            and any(k.isdigit() for k in sifre)
        )

    def kayitOl(self, adSoyad, eposta, sifre, sifreTekrar, universite="", bolum=""):
        if not adSoyad or not adSoyad.strip():
            raise IsKuraliIhlaliException("IK-01", "Ad soyad zorunludur.")
        if not self._epostaGecerliMi(eposta):
            raise IsKuraliIhlaliException(
                "IK-01",
                "Geçerli bir e-posta adresi girmelisiniz.",
            )
        eposta = eposta.strip()
        if not self._akademikMi(eposta):
            raise IsKuraliIhlaliException(
                "IK-01",
                "Kayıt yalnızca öğrenci e-posta adresleriyle yapılabilir "
                "(örn. .edu.tr uzantılı adresiniz).",
            )
        if self.kullanici_deposu.epostaVarMi(eposta):
            raise IsKuraliIhlaliException(
                "IK-02", "Bu e-posta adresi ile zaten bir hesap var. Giriş yapmayı deneyin."
            )
        if not self._sifreKuralinaUygunMu(sifre):
            raise IsKuraliIhlaliException(
                "IK-03",
                "Şifre en az 8 karakter olmalı, en az bir harf ve bir rakam içermelidir.",
            )
        if sifre != sifreTekrar:
            raise IsKuraliIhlaliException("IK-03", "Şifre tekrarı ile eşleşmiyor.")
        kullanici = Kullanici(
            ad_soyad=adSoyad.strip(),
            eposta=eposta,
            sifre_hash=sifre_hashle(sifre),
            rol=Rol.OGRENCI,
            universite=(universite or "").strip(),
            bolum=(bolum or "").strip(),
        )
        self.kullanici_deposu.kaydet(kullanici)
        return self._dogrulamaDuzenle(kullanici)

    def dogrulamaGonder(self, eposta):
        kullanici = self.kullanici_deposu.epostaIleBul(eposta) if eposta else None
        if kullanici is None or kullanici.dogrulanmisMi():
            return None
        return self._dogrulamaDuzenle(kullanici)

    def dogrula(self, token):
        kullanici = self.kullanici_deposu.tokenIleBul(token)
        if (
            kullanici is None
            or kullanici.dogrulanmisMi()
            or kullanici.dogrulama_bitis is None
            or kullanici.dogrulama_bitis <= datetime.now()
        ):
            raise IsKuraliIhlaliException(
                "IK-29",
                "Doğrulama bağlantısı geçersiz veya süresi dolmuş. "
                "Yeni bir bağlantı isteyin.",
            )
        kullanici.epostaDogrula()
        self.kullanici_deposu.kaydet(kullanici)
        return kullanici

    def girisYap(self, eposta, sifre):
        kullanici = self.kullanici_deposu.epostaIleBul(eposta) if eposta else None
        if kullanici is None:
            raise IsKuraliIhlaliException("IK-04", config.HATA_EPOSTA_SIFRE)
        if kullanici.kilitliMi():
            raise IsKuraliIhlaliException("IK-04", config.HATA_KILIT)
        if not kullanici.sifreDogrula(sifre):
            kullanici.basarisizDenemeKaydet()
            self.kullanici_deposu.kaydet(kullanici)
            raise IsKuraliIhlaliException("IK-04", config.HATA_EPOSTA_SIFRE)
        if not kullanici.aktifMi():
            raise IsKuraliIhlaliException("IK-05", config.HATA_DEVRE_DISI)
        kullanici.denemeleriSifirla()
        self.kullanici_deposu.kaydet(kullanici)
        simdi = datetime.now()
        oturum = Oturum(
            oturum_id=uuid.uuid4().hex,
            kullanici_id=kullanici.kullanici_id,
            olusturma_zamani=simdi,
            son_etkinlik_zamani=simdi,
        )
        oturum_kaydet(self.kullanici_deposu.db, oturum)
        return oturum

    def cikisYap(self, oturum_id):
        if oturum_id:
            oturum_sil(self.kullanici_deposu.db, oturum_id)

    def oturumDogrula(self, oturum_id):
        if not oturum_id:
            return None
        oturum = oturum_bul(self.kullanici_deposu.db, oturum_id)
        if oturum is None or not oturum.aktif:
            return None
        if oturum.sureDoldu():
            oturum_sil(self.kullanici_deposu.db, oturum_id)
            return None
        oturum.etkinlikGuncelle()
        oturum_kaydet(self.kullanici_deposu.db, oturum)
        kullanici = self.kullanici_deposu.idIleBul(oturum.kullanici_id)
        if kullanici is None or not kullanici.aktifMi():
            return None
        return kullanici

    def sifreDegistir(self, kullanici_id, mevcutSifre, yeniSifre, yeniSifreTekrar):
        kullanici = self.kullanici_deposu.idIleBul(kullanici_id)
        if kullanici is None:
            raise IsKuraliIhlaliException("IK-07", "Kullanıcı bulunamadı.")
        if not kullanici.sifreDogrula(mevcutSifre):
            raise IsKuraliIhlaliException("IK-07", "Mevcut şifre hatalı.")
        if not self._sifreKuralinaUygunMu(yeniSifre):
            raise IsKuraliIhlaliException(
                "IK-03",
                "Yeni şifre en az 8 karakter olmalı, en az bir harf ve bir rakam içermelidir.",
            )
        if yeniSifre != yeniSifreTekrar:
            raise IsKuraliIhlaliException("IK-03", "Yeni şifre tekrarı ile eşleşmiyor.")
        if kullanici.sifreDogrula(yeniSifre):
            raise IsKuraliIhlaliException(
                "IK-07", "Yeni şifre mevcut şifreden farklı olmalıdır."
            )
        kullanici.sifreGuncelle(sifre_hashle(yeniSifre))
        self.kullanici_deposu.kaydet(kullanici)

    def kullaniciOturumlariniSonlandir(self, kullanici_id):
        oturumlari_sonlandir(self.kullanici_deposu.db, kullanici_id)
