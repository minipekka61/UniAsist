import logging
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage

import config

LOG = logging.getLogger("uniasist.eposta")


class IEpostaServisi(ABC):
    @abstractmethod
    def dogrulamaEpostasiGonder(self, eposta, ad_soyad, baglanti):
        ...


class KonsolEpostaServisi(IEpostaServisi):
    def dogrulamaEpostasiGonder(self, eposta, ad_soyad, baglanti):
        LOG.info(
            "Doğrulama e-postası: %s <%s> — bağlantı: %s",
            ad_soyad,
            eposta,
            baglanti,
        )


class SmtpEpostaServisi(IEpostaServisi):
    def dogrulamaEpostasiGonder(self, eposta, ad_soyad, baglanti):
        mesaj = EmailMessage()
        mesaj["From"] = config.SMTP_GONDEREN
        mesaj["To"] = eposta
        mesaj["Subject"] = "UniAsist — e-posta adresinizi doğrulayın"
        mesaj.set_content(
            f"Merhaba {ad_soyad},\n\n"
            f"UniAsist hesabınızı doğrulamak için şu bağlantıyı açın:\n"
            f"{baglanti}\n\n"
            f"Bağlantı 24 saat geçerlidir. Bu kaydı siz yapmadıysanız bu e-postayı yok sayabilirsiniz."
        )
        with smtplib.SMTP(config.SMTP_SUNUCU, config.SMTP_PORT) as sunucu:
            sunucu.starttls()
            sunucu.login(config.SMTP_KULLANICI, config.SMTP_SIFRE)
            sunucu.send_message(mesaj)
