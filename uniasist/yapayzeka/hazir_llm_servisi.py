import json

import requests

import config
from uniasist.hatalar import IsKuraliIhlaliException
from uniasist.yapayzeka.i_yapay_zeka_servisi import IYapayZekaServisi

SISTEM_TALIMATI = (
    "Sen UniAsist adlı üniversite öğrenci destek asistanısın. Yalnızca "
    "'BELGE İÇERİĞİ' bölümünde verilen metinlere dayanarak, Türkçe ve anlaşılır "
    "biçimde yanıt ver. Belge içeriğinde yanıt bulunmuyorsa tahmin yürütmeye "
    "çalışma ve yalnızca 'BILGI_YOK' yaz. Yanıtında öğrenci numarası, T.C. kimlik "
    "numarası gibi kişisel veri isteme."
)


class HazirLLMServisi(IYapayZekaServisi):
    def __init__(self, api_anahtari=None, api_base=None, model=None,
                 embedding_model=None, zaman_asimi=None):
        self.api_anahtari = api_anahtari or config.API_ANAHTARI
        self.api_base = (api_base or config.API_BASE).rstrip("/")
        self.model = model or config.MODEL
        self.embedding_model = embedding_model or config.EMBEDDING_MODEL
        self.zaman_asimi = zaman_asimi or config.LLM_ZAMAN_ASIMI_SANIYE

    @property
    def saglayici_etiketi(self):
        return f"api:{self.embedding_model}"

    def _basliklar(self):
        return {"Authorization": f"Bearer {self.api_anahtari}"}

    def _hata(self):
        return IsKuraliIhlaliException("IK-19", config.SERVIS_HATA_METNI)

    def gommeUret(self, metin):
        try:
            yanit = requests.post(
                f"{self.api_base}/embeddings",
                headers=self._basliklar(),
                json={"model": self.embedding_model, "input": [metin]},
                timeout=self.zaman_asimi,
            )
            yanit.raise_for_status()
            return yanit.json()["data"][0]["embedding"]
        except (requests.RequestException, KeyError, IndexError, ValueError):
            raise self._hata()

    def _istemler(self, soru_metni, parcalar, baglam):
        satirlar = []
        if baglam:
            satirlar.append("ÖNCEKİ KONUŞMA:")
            for mesaj in baglam:
                kim = "Kullanıcı" if mesaj.gonderen and mesaj.gonderen.name == "KULLANICI" else "Asistan"
                satirlar.append(f"{kim}: {mesaj.metin}")
            satirlar.append("")
        satirlar.append("BELGE İÇERİĞİ:")
        for i, parca in enumerate(parcalar, start=1):
            satirlar.append(f"[{i}] ({parca.kaynak_adi} — {parca.bolumBilgisiGetir()}) {parca.metin}")
        satirlar.append("")
        satirlar.append(f"SORU: {soru_metni}")
        return [
            {"role": "system", "content": SISTEM_TALIMATI},
            {"role": "user", "content": "\n".join(satirlar)},
        ]

    def yanitUretAkis(self, soru_metni, parcalar, baglam):
        try:
            yanit = requests.post(
                f"{self.api_base}/chat/completions",
                headers=self._basliklar(),
                json={
                    "model": self.model,
                    "temperature": 0.2,
                    "stream": True,
                    "messages": self._istemler(soru_metni, parcalar, baglam),
                },
                timeout=self.zaman_asimi,
            )
            yanit.raise_for_status()
            for satir in yanit.iter_lines():
                if not satir:
                    continue
                metin = satir.decode("utf-8")
                if not metin.startswith("data:"):
                    continue
                yuk = metin[len("data:"):].strip()
                if yuk == "[DONE]":
                    break
                try:
                    parca = json.loads(yuk)["choices"][0]["delta"].get("content")
                except (KeyError, IndexError, ValueError):
                    continue
                if parca:
                    yield parca
        except requests.RequestException:
            raise self._hata()

    def yanitUret(self, soru_metni, parcalar, baglam):
        return "".join(self.yanitUretAkis(soru_metni, parcalar, baglam))
