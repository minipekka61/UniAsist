import logging

import pytest

from uniasist.eposta import KonsolEpostaServisi, SmtpEpostaServisi


def test_konsol_eposta_servisi_loglar(caplog):
    with caplog.at_level(logging.INFO, logger="uniasist.eposta"):
        KonsolEpostaServisi().dogrulamaEpostasiGonder(
            "ali@universite.edu.tr",
            "Ali Veli",
            "http://localhost:5000/dogrula/abc123",
        )
    assert "ali@universite.edu.tr" in caplog.text
    assert "http://localhost:5000/dogrula/abc123" in caplog.text


def test_smtp_eposta_servisi_yapilir(monkeypatch):
    gonderilen = {}

    class SahteSMTP:
        def __init__(self, sunucu, port):
            gonderilen["sunucu"] = sunucu
            gonderilen["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            gonderilen["starttls"] = True

        def login(self, kullanici, sifre):
            gonderilen["login"] = kullanici

        def send_message(self, mesaj):
            gonderilen["mesaj"] = mesaj

    monkeypatch.setattr("uniasist.eposta.smtplib.SMTP", SahteSMTP)
    SmtpEpostaServisi().dogrulamaEpostasiGonder(
        "ali@universite.edu.tr", "Ali Veli", "http://localhost:5000/dogrula/t1"
    )
    mesaj = gonderilen["mesaj"]
    assert mesaj["To"] == "ali@universite.edu.tr"
    assert "http://localhost:5000/dogrula/t1" in mesaj.get_content()
    assert "doğrula" in str(mesaj["Subject"]).lower()
